/*
 * RoomCleaner claw node -- Seeed XIAO ESP32-S3 Sense (camera board attached).
 *
 * Role: the claw's eyes and hand. It does NOT decide anything about motion.
 * The host (roomcleaner/cdpr/claw_link.py) pulls frames and status and sends
 * grip commands over HTTP on the home 2.4 GHz network.
 *
 *   GET  /status          JSON: online, uptime/clock (us), battery_v, battery_low, grip
 *                         state, servo_us, camera_ok, camera mode string, frame counter.
 *                         There is NO attitude in it: the claw carries no IMU (decision
 *                         D27). Roll/pitch come from vision and the cable model on the host.
 *   GET  /frame           one JPEG; headers X-Capture-Us (esp_timer at capture),
 *                         X-Frame-Id, X-Camera-Mode. Fixed sensor mode: the
 *                         intrinsic calibration is only valid for this mode.
 *   POST /grip?close=1    close (0 = open). The claw obeys: the HOST decides whether a
 *                         grip is approved (it waits for the claw to settle and checks
 *                         the tilt). A request without close=0|1 is rejected (400).
 *   POST /setup           park the servo at the OPEN position for horn/drum assembly
 *
 * Safety behaviour
 *   - Losing WiFi or the host NEVER opens the claw: an item held stays held.
 *   - The servo is only driven inside [SERVO_MIN_US, SERVO_MAX_US].
 *   - Brown-out (battery below BATT_CUTOFF_V): the servo holds its last command
 *     and /status reports low battery; the host refuses to lift.
 *
 * Wiring (verify against your build before powering):
 *   Servo signal   GPIO1  (D0)     servo power from the 6.0 V buck, common ground
 *   Battery sense  GPIO3  (D2)     2S LiPo through 200k/100k divider (ratio 3.0)
 *   Camera         Sense board (pins below)
 *
 * Board: "XIAO_ESP32S3", PSRAM: "OPI PSRAM". No extra libraries: the servo pulses come straight from the LEDC
 * hardware on timer 1 / channel 1 (the camera clock owns timer 0 / channel 0; ESP32Servo could collide with it and
 * leave the servo without pulses, seen on the bench 10/26).
 * Copy secrets.example.h to secrets.h and fill in the network credentials (and, optionally, a fixed IP).
 * The orange user LED blinks once a second while the sketch runs (the board has no power LED).
 */
#include <WiFi.h>
#include <WebServer.h>
#include "driver/ledc.h"
#include "esp_camera.h"
#include "esp_timer.h"
#include "secrets.h"       // WIFI_SSID, WIFI_PASS

// ---------------------------------------------------------------- settings
static const char* HOSTNAME = "roomcleaner-claw";
static const int   SERVO_PIN = 1;
static const int   SERVO_MIN_US = 600, SERVO_MAX_US = 2400;
static const int   SERVO_OPEN_US = 900;      // measure on the assembled claw (D8)
static const int   SERVO_CLOSED_US = 2000;   // measure: fingers curled, no stall
static const int   BATT_PIN = 3;
static const float BATT_RATIO = 3.0f;        // divider; calibrate against a meter
static const float BATT_CUTOFF_V = 6.8f;
static const char* CAMERA_MODE = "SVGA-800x600-q10";
static const int   LED_PIN = 21;             // orange user LED, ON when LOW

// XIAO ESP32-S3 Sense camera pins
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  10
#define SIOD_GPIO_NUM  40
#define SIOC_GPIO_NUM  39
#define Y9_GPIO_NUM    48
#define Y8_GPIO_NUM    11
#define Y7_GPIO_NUM    12
#define Y6_GPIO_NUM    14
#define Y5_GPIO_NUM    16
#define Y4_GPIO_NUM    18
#define Y3_GPIO_NUM    17
#define Y2_GPIO_NUM    15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM  47
#define PCLK_GPIO_NUM  13

WebServer server(80);
int servoUs = SERVO_OPEN_US;
bool gripClosed = false;
bool cameraOk = false;
uint32_t frameId = 0;

// ---------------------------------------------------------------- servo
// 50 Hz, 14-bit, on LEDC timer 1 / channel 1
static const ledc_mode_t SERVO_MODE = LEDC_LOW_SPEED_MODE;
static const ledc_timer_t SERVO_TIMER = LEDC_TIMER_1;
static const ledc_channel_t SERVO_CH = LEDC_CHANNEL_1;
static const uint32_t SERVO_PERIOD_US = 20000, SERVO_DUTY_MAX = (1u << 14) - 1;

bool servoStart() {
  ledc_timer_config_t t = {};
  t.speed_mode = SERVO_MODE;
  t.duty_resolution = LEDC_TIMER_14_BIT;
  t.timer_num = SERVO_TIMER;
  t.freq_hz = 50;
  t.clk_cfg = LEDC_AUTO_CLK;
  if (ledc_timer_config(&t) != ESP_OK) return false;
  ledc_channel_config_t c = {};
  c.gpio_num = SERVO_PIN;
  c.speed_mode = SERVO_MODE;
  c.channel = SERVO_CH;
  c.timer_sel = SERVO_TIMER;
  c.duty = 0;
  c.hpoint = 0;
  return ledc_channel_config(&c) == ESP_OK;
}

void setServo(int us) {
  servoUs = constrain(us, SERVO_MIN_US, SERVO_MAX_US);
  ledc_set_duty(SERVO_MODE, SERVO_CH, (uint32_t)servoUs * SERVO_DUTY_MAX / SERVO_PERIOD_US);
  ledc_update_duty(SERVO_MODE, SERVO_CH);
}

float batteryV() {
  uint32_t mv = analogReadMilliVolts(BATT_PIN);
  return mv / 1000.0f * BATT_RATIO;
}

// ---------------------------------------------------------------- camera
bool cameraInit() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM; c.pin_vsync = VSYNC_GPIO_NUM;
  c.pin_href = HREF_GPIO_NUM; c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM; c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_SVGA;             // 800x600: must match the calibration
  c.jpeg_quality = 10;
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;          // never serve a stale queued frame
  if (esp_camera_init(&c) != ESP_OK) return false;
  sensor_t* s = esp_camera_sensor_get();
  s->set_lenc(s, 1);                         // fixed processing so intrinsics stay valid
  return true;
}

// ---------------------------------------------------------------- HTTP
void sendJson(int code, const String& body) {
  server.sendHeader("Cache-Control", "no-store");
  server.send(code, "application/json", body);
}

void handleStatus() {
  char buf[300];
  float v = batteryV();                      // one ADC read: the voltage and the flag must agree
  snprintf(buf, sizeof(buf),
           "{\"online\":true,\"t_us\":%llu,\"battery_v\":%.2f,\"battery_low\":%s,\"grip_closed\":%s,"
           "\"servo_us\":%d,\"camera_ok\":%s,\"camera_mode\":\"%s\",\"frame_id\":%lu}",
           (unsigned long long)esp_timer_get_time(), v, v < BATT_CUTOFF_V ? "true" : "false",
           gripClosed ? "true" : "false", servoUs, cameraOk ? "true" : "false", CAMERA_MODE,
           (unsigned long)frameId);
  sendJson(200, buf);
}

void handleFrame() {
  if (!cameraOk) { sendJson(503, "{\"error\":\"camera not initialised\"}"); return; }
  camera_fb_t* fb = esp_camera_fb_get();
  uint64_t t = esp_timer_get_time();
  if (!fb) { sendJson(503, "{\"error\":\"capture failed\"}"); return; }
  frameId++;
  server.sendHeader("X-Capture-Us", String((unsigned long long)t));
  server.sendHeader("X-Frame-Id", String(frameId));
  server.sendHeader("X-Camera-Mode", CAMERA_MODE);
  server.sendHeader("Cache-Control", "no-store");
  server.setContentLength(fb->len);
  server.send(200, "image/jpeg", "");
  server.client().write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void handleGrip() {
  // Bad parameters never move the servo: close must be exactly 0 or 1.
  if (!server.hasArg("close") || (server.arg("close") != "0" && server.arg("close") != "1")) {
    sendJson(400, "{\"ok\":false,\"why\":\"close must be 0 or 1\"}");
    return;
  }
  bool close = server.arg("close") == "1";
  setServo(close ? SERVO_CLOSED_US : SERVO_OPEN_US);
  gripClosed = close;
  sendJson(200, String("{\"ok\":true,\"grip_closed\":") + (close ? "true" : "false") + "}");
}

void handleSetup() {
  setServo(SERVO_OPEN_US);
  gripClosed = false;
  sendJson(200, "{\"ok\":true,\"note\":\"servo parked open: attach horn/drum now\"}");
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);               // LED off until loop() blinks it
  if (!servoStart()) Serial.println("servo: LEDC setup FAILED");
  setServo(SERVO_OPEN_US);                   // power-up: open (nothing can be held yet)
  analogReadResolution(12);
  cameraOk = cameraInit();
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(HOSTNAME);
  WiFi.setSleep(false);                      // latency over power
#if defined(CLAW_IP)
  WiFi.config(CLAW_IP, GATEWAY, SUBNET);     // fixed address: config claw.address = "<CLAW_IP>"
#endif
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.printf("\nclaw %s camera=%d\n", WiFi.localIP().toString().c_str(), cameraOk);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/frame", HTTP_GET, handleFrame);
  server.on("/grip", HTTP_POST, handleGrip);
  server.on("/setup", HTTP_POST, handleSetup);
  server.begin();
}

void loop() {
  digitalWrite(LED_PIN, (millis() % 1000) < 80 ? LOW : HIGH);   // heartbeat: short blink once a second
  server.handleClient();
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();                        // grip state is deliberately untouched
    delay(200);
  }
}
