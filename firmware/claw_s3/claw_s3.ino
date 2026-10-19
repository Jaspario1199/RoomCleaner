/*
 * RoomCleaner claw node -- Seeed XIAO ESP32-S3 Sense (camera board attached).
 *
 * Role: the claw's eyes and hand. It does NOT decide anything about motion.
 * The host (roomcleaner/cdpr/claw_link.py) pulls frames and status and sends
 * grip commands over HTTP on the home 2.4 GHz network.
 *
 *   GET  /status          JSON: online, uptime/clock (us), battery_v, roll/pitch (rad,
 *                         MPU6050 accelerometer, low-pass), tilt_rad, grip state,
 *                         servo_us, camera mode string, imu_ok, frame counter
 *   GET  /frame           one JPEG; headers X-Capture-Us (esp_timer at capture),
 *                         X-Frame-Id, X-Camera-Mode. Fixed sensor mode: the
 *                         intrinsic calibration is only valid for this mode.
 *   POST /grip?close=1    close (0 = open). Refused (409) while the claw is tilted
 *                         beyond GRIP_TILT_MAX_RAD unless &force=1. Replies JSON.
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
 *   MPU6050 SDA    GPIO5  (D4)     3.3 V, address 0x68
 *   MPU6050 SCL    GPIO6  (D5)
 *   Battery sense  GPIO3  (D2)     2S LiPo through 200k/100k divider (ratio 3.0)
 *   Camera         Sense board (pins below)
 *
 * Board: "XIAO_ESP32S3", PSRAM: "OPI PSRAM". Libraries: ESP32Servo.
 * Copy secrets.example.h to secrets.h and fill in the network credentials.
 */
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <ESP32Servo.h>
#include "esp_camera.h"
#include "esp_timer.h"
#include "secrets.h"       // WIFI_SSID, WIFI_PASS

// ---------------------------------------------------------------- settings
static const char* HOSTNAME = "roomcleaner-claw";
static const int   SERVO_PIN = 1;
static const int   SERVO_MIN_US = 600, SERVO_MAX_US = 2400;
static const int   SERVO_OPEN_US = 900;      // measure on the assembled claw (D8)
static const int   SERVO_CLOSED_US = 2000;   // measure: fingers curled, no stall
static const int   I2C_SDA = 5, I2C_SCL = 6;
static const int   BATT_PIN = 3;
static const float BATT_RATIO = 3.0f;        // divider; calibrate against a meter
static const float BATT_CUTOFF_V = 6.8f;
static const float GRIP_TILT_MAX_RAD = 0.0873f;   // 5 deg (config claw.grip_tilt_max_rad)
static const char* CAMERA_MODE = "SVGA-800x600-q10";

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
Servo servo;
int servoUs = SERVO_OPEN_US;
bool gripClosed = false;
bool cameraOk = false, imuOk = false;
uint32_t frameId = 0;
float rollF = 0, pitchF = 0;          // low-passed accelerometer attitude (rad)
uint64_t lastImuUs = 0;

// ---------------------------------------------------------------- servo
void setServo(int us) {
  servoUs = constrain(us, SERVO_MIN_US, SERVO_MAX_US);
  servo.writeMicroseconds(servoUs);
}

// ---------------------------------------------------------------- IMU
bool mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(0x68);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

bool mpuInit() {
  if (!mpuWrite(0x6B, 0x00)) return false;   // wake
  mpuWrite(0x1C, 0x00);                      // accel +-2 g
  mpuWrite(0x1A, 0x04);                      // DLPF ~20 Hz
  return true;
}

void imuUpdate() {
  Wire.beginTransmission(0x68);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) { imuOk = false; return; }
  if (Wire.requestFrom(0x68, 6) != 6) { imuOk = false; return; }
  int16_t ax = (Wire.read() << 8) | Wire.read();
  int16_t ay = (Wire.read() << 8) | Wire.read();
  int16_t az = (Wire.read() << 8) | Wire.read();
  // Mount the IMU with +Z along the claw's body +Z (up when hanging).
  float roll = atan2f((float)ay, (float)az);
  float pitch = atan2f(-(float)ax, sqrtf((float)ay * ay + (float)az * az));
  const float a = 0.2f;                      // ~10 Hz sampling, ~0.5 s time constant
  rollF += a * (roll - rollF);
  pitchF += a * (pitch - pitchF);
  imuOk = true;
}

float tiltRad() { return sqrtf(rollF * rollF + pitchF * pitchF); }

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
  char buf[400];
  snprintf(buf, sizeof(buf),
           "{\"online\":true,\"t_us\":%llu,\"battery_v\":%.2f,\"battery_low\":%s,\"roll\":%.5f,"
           "\"pitch\":%.5f,\"tilt_rad\":%.5f,\"imu_ok\":%s,\"grip_closed\":%s,\"servo_us\":%d,"
           "\"camera_ok\":%s,\"camera_mode\":\"%s\",\"frame_id\":%lu}",
           (unsigned long long)esp_timer_get_time(), batteryV(), batteryV() < BATT_CUTOFF_V ? "true" : "false",
           rollF, pitchF, tiltRad(), imuOk ? "true" : "false", gripClosed ? "true" : "false", servoUs,
           cameraOk ? "true" : "false", CAMERA_MODE, (unsigned long)frameId);
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
  bool close = server.hasArg("close") && server.arg("close") == "1";
  bool force = server.hasArg("force") && server.arg("force") == "1";
  if (close && !force && (!imuOk || tiltRad() > GRIP_TILT_MAX_RAD)) {
    sendJson(409, "{\"ok\":false,\"why\":\"claw not upright\"}");
    return;
  }
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
  servo.setPeriodHertz(50);
  servo.attach(SERVO_PIN, SERVO_MIN_US, SERVO_MAX_US);
  setServo(SERVO_OPEN_US);                   // power-up: open (nothing can be held yet)
  Wire.begin(I2C_SDA, I2C_SCL, 400000);
  imuOk = mpuInit();
  analogReadResolution(12);
  cameraOk = cameraInit();
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(HOSTNAME);
  WiFi.setSleep(false);                      // latency over power
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.printf("\nclaw %s camera=%d imu=%d\n", WiFi.localIP().toString().c_str(), cameraOk, imuOk);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/frame", HTTP_GET, handleFrame);
  server.on("/grip", HTTP_POST, handleGrip);
  server.on("/setup", HTTP_POST, handleSetup);
  server.begin();
}

void loop() {
  server.handleClient();
  uint64_t now = esp_timer_get_time();
  if (now - lastImuUs >= 100000) {           // 10 Hz attitude
    lastImuUs = now;
    imuUpdate();
  }
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();                        // grip state is deliberately untouched
    delay(200);
  }
}
