// RoomCleaner claw bench test, Rev B breadboard (2026-10-25).
// Checks the claw circuit one part at a time from the Serial Monitor, and shows the live camera in a browser.
//   - orange LED heartbeat (1 blink/s = the program is running, also on battery only)
//   - battery voltage through the R1/R2 divider on D2
//   - servo on D0: OFF at boot (no signal = no jump); center, small steps, open/close test positions
//   - camera: live video at http://<ip>/ , one photo at http://<ip>/jpg , numbers at http://<ip>/status
//
// Board: "XIAO_ESP32S3", Tools > PSRAM: "OPI PSRAM" (the camera needs it). Library: ESP32Servo.
// Wi-Fi: copy secrets.example.h to secrets.h (git-ignored) and fill in your 2.4 GHz network. Without Wi-Fi the
// serial menu still works; only the camera page needs it.
// Wiring: docs/electrical/claw_revB_20261021/breadboard_layout_claw.png and offboard_wiring_claw.png.
// Not the claw firmware: flash firmware/claw_s3/claw_s3.ino again when the bench test passes.

#include <Arduino.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#if __has_include("secrets.h")
#include "secrets.h"                         // WIFI_SSID, WIFI_PASS
#define HAVE_SECRETS 1
#else
#define HAVE_SECRETS 0                       // no secrets.h yet: everything except the camera page still works
#define WIFI_SSID ""
#define WIFI_PASS ""
#endif

#if !defined(CONFIG_IDF_TARGET_ESP32S3)
#error "claw_bench_test: select Tools > Board > esp32 > XIAO_ESP32S3 (and PSRAM: OPI PSRAM)"
#endif

// ---------------------------------------------------------------- pins and limits (same as claw_s3.ino)
constexpr int SERVO_PIN = 1;                 // D0
constexpr int BATT_PIN = 3;                  // D2
constexpr int LED_PIN = 21;                  // orange user LED, ON when LOW
constexpr int SERVO_MIN_US = 600, SERVO_MAX_US = 2400;
constexpr int SERVO_CENTER_US = 1500;
constexpr int SERVO_OPEN_US = 900, SERVO_CLOSED_US = 2000;   // claw_s3 defaults, not yet measured on the claw
constexpr int STEP_US = 50;
constexpr float BATT_RATIO = 3.0f;           // R1 200k / R2 100k
constexpr float BATT_CUTOFF_V = 6.8f;

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

Servo servo;
bool servoOn = false;
int servoUs = SERVO_CENTER_US;
bool cameraOk = false;
httpd_handle_t httpd = nullptr;

// ---------------------------------------------------------------- battery
float battMilliVoltsAtPin() {
  uint32_t sum = 0;
  for (int i = 0; i < 16; i++) sum += analogReadMilliVolts(BATT_PIN);
  return sum / 16.0f;
}

float batteryV() { return battMilliVoltsAtPin() / 1000.0f * BATT_RATIO; }

void batteryReport() {
  float pin = battMilliVoltsAtPin(), v = pin / 1000.0f * BATT_RATIO;
  Serial.printf("battery: %.2f V (D2 pin %.0f mV x %.1f)", v, pin, BATT_RATIO);
  if (pin < 200) Serial.println("  -> about 0: battery off, or on USB only, or R1 / jumper c5->g14 missing");
  else if (v < BATT_CUTOFF_V) Serial.println("  -> LOW (below 6.8 V): charge the pack");
  else if (v > 8.6f) Serial.println("  -> TOO HIGH for a 2S pack: check R1 200k / R2 100k values");
  else Serial.println("  -> OK (full 8.4 V, empty 6.8 V). Compare with a meter on the pack");
}

// ---------------------------------------------------------------- servo
void servoWrite(int us) {
  servoUs = constrain(us, SERVO_MIN_US, SERVO_MAX_US);
  if (!servoOn) {
    servo.setPeriodHertz(50);
    servo.attach(SERVO_PIN, SERVO_MIN_US, SERVO_MAX_US);
    servoOn = true;
  }
  servo.writeMicroseconds(servoUs);
  Serial.printf("servo: %d us%s\n", servoUs, servoUs == SERVO_MIN_US || servoUs == SERVO_MAX_US ? " (limit)" : "");
}

void servoOff() {
  if (servoOn) servo.detach();
  servoOn = false;
  digitalWrite(SERVO_PIN, LOW);
  Serial.println("servo: signal OFF (the servo goes limp)");
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
  c.frame_size = FRAMESIZE_VGA;              // 640x480: smooth live view (claw_s3 uses SVGA for calibration)
  c.jpeg_quality = 12;
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("camera: init FAILED (0x%x). Check PSRAM = OPI PSRAM, the Sense board pressed fully onto its connector,\n"
                  "        and the ribbon cable seated.\n", err);
    return false;
  }
  sensor_t* s = esp_camera_sensor_get();
  Serial.printf("camera: OK, sensor PID 0x%02X (0x26 = OV2640, 0x36 = OV3660)\n", s->id.PID);
  return true;
}

void cameraTest() {
  if (!cameraOk) { Serial.println("camera: not running (see the boot message)"); return; }
  uint32_t t0 = millis();
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) { Serial.println("camera: capture FAILED"); return; }
  Serial.printf("camera: captured %ux%u JPEG, %u bytes in %lu ms\n", fb->width, fb->height, fb->len, millis() - t0);
  esp_camera_fb_return(fb);
}

// ---------------------------------------------------------------- web page (runs in its own task)
static const char INDEX_HTML[] =
    "<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>Claw camera</title><style>body{font-family:sans-serif;background:#111;color:#eee;margin:16px}"
    "img{width:100%;max-width:800px;border:1px solid #444}</style></head><body>"
    "<h3>RoomCleaner claw camera (bench test)</h3><img src='/stream'>"
    "<p id=s>...</p><script>setInterval(()=>fetch('/status').then(r=>r.json()).then(j=>{"
    "document.getElementById('s').textContent='battery '+j.battery_v.toFixed(2)+' V, servo '+(j.servo_on?j.servo_us+' us':'off')"
    "}).catch(()=>{}),2000)</script></body></html>";

esp_err_t indexHandler(httpd_req_t* req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, INDEX_HTML, HTTPD_RESP_USE_STRLEN);
}

esp_err_t jpgHandler(httpd_req_t* req) {
  camera_fb_t* fb = cameraOk ? esp_camera_fb_get() : nullptr;
  if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
  httpd_resp_set_type(req, "image/jpeg");
  esp_err_t r = httpd_resp_send(req, (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return r;
}

esp_err_t streamHandler(httpd_req_t* req) {
  if (!cameraOk) { httpd_resp_send_500(req); return ESP_FAIL; }
  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
  char head[64];
  while (true) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) return ESP_FAIL;
    int n = snprintf(head, sizeof(head), "\r\n--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
    esp_err_t r = httpd_resp_send_chunk(req, head, n);
    if (r == ESP_OK) r = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (r != ESP_OK) return r;               // the browser closed the page
  }
}

esp_err_t statusHandler(httpd_req_t* req) {
  char buf[160];
  snprintf(buf, sizeof(buf), "{\"battery_v\":%.2f,\"servo_on\":%s,\"servo_us\":%d,\"camera_ok\":%s,\"uptime_s\":%lu}",
           batteryV(), servoOn ? "true" : "false", servoUs, cameraOk ? "true" : "false", millis() / 1000);
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_send(req, buf, HTTPD_RESP_USE_STRLEN);
}

void webStart() {
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  if (httpd_start(&httpd, &cfg) != ESP_OK) { Serial.println("web: server did not start"); return; }
  httpd_uri_t pages[] = {{"/", HTTP_GET, indexHandler, nullptr}, {"/jpg", HTTP_GET, jpgHandler, nullptr},
                         {"/stream", HTTP_GET, streamHandler, nullptr}, {"/status", HTTP_GET, statusHandler, nullptr}};
  for (auto& p : pages) httpd_register_uri_handler(httpd, &p);
}

void wifiStart() {
  if (!HAVE_SECRETS) {
    Serial.println("wifi: no secrets.h in the sketch folder, so no Wi-Fi and no camera page. Add a tab named secrets.h\n"
                   "      (see secrets.example.h) and upload again. All serial tests work without it.");
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("roomcleaner-claw-test");
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("wifi: connecting");
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) { delay(300); Serial.print("."); }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nwifi: connected. Open  http://%s/  in a browser on the same network\n", WiFi.localIP().toString().c_str());
    webStart();
  } else {
    Serial.println("\nwifi: NOT connected after 15 s (2.4 GHz only; check secrets.h). The serial tests still work; 'n' retries.");
  }
}

void wifiReport() {
  if (WiFi.status() == WL_CONNECTED)
    Serial.printf("wifi: connected, IP %s, signal %d dBm -> http://%s/\n", WiFi.localIP().toString().c_str(), WiFi.RSSI(),
                  WiFi.localIP().toString().c_str());
  else
    Serial.println("wifi: not connected ('n' to retry)");
}

// ---------------------------------------------------------------- menu
void help() {
  Serial.println("\nRoomCleaner claw bench test (XIAO ESP32-S3 Sense)");
  Serial.println("  s  status: battery, camera, wifi");
  Serial.println("  b  battery voltage");
  Serial.println("  k  camera: take one test picture");
  Serial.println("  n  wifi: reconnect / show the camera page address");
  Serial.println("  m  servo to CENTER (1500 us)     x  servo signal OFF");
  Serial.println("  +  servo +50 us                  -  servo -50 us");
  Serial.println("  o  servo to OPEN test position (900 us)   c  CLOSE test position (2000 us)");
  Serial.println("     (o / c only after checking with + / - that the claw can travel that far)");
  Serial.println("  h  this menu");
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);               // LED off
  pinMode(SERVO_PIN, OUTPUT);
  digitalWrite(SERVO_PIN, LOW);              // no servo pulses until you ask for them
  ESP32PWM::allocateTimer(1);                // leave LEDC timer 0 to the camera clock
  Serial.begin(115200);
  delay(1500);                               // time for the USB serial port to appear
  analogReadResolution(12);
  help();
  Serial.println("\nboot check:");
  batteryReport();
  cameraOk = cameraInit();
  wifiStart();
  Serial.println("servo: OFF at boot. Type m to center it.");
}

void loop() {
  static uint32_t lastBlink = 0;
  uint32_t now = millis();
  digitalWrite(LED_PIN, (now - lastBlink) < 80 ? LOW : HIGH);   // short blink once a second
  if (now - lastBlink >= 1000) lastBlink = now;

  if (!Serial.available()) { delay(5); return; }
  char ch = Serial.read();
  switch (ch) {
    case 's': batteryReport(); Serial.printf("camera: %s\n", cameraOk ? "running" : "NOT running"); wifiReport();
              Serial.printf("servo: %s\n", servoOn ? String(servoUs).c_str() : "off"); break;
    case 'b': batteryReport(); break;
    case 'k': cameraTest(); break;
    case 'n': if (WiFi.status() != WL_CONNECTED) wifiStart(); else wifiReport(); break;
    case 'm': servoWrite(SERVO_CENTER_US); break;
    case '+': servoWrite(servoUs + STEP_US); break;
    case '-': servoWrite(servoUs - STEP_US); break;
    case 'o': servoWrite(SERVO_OPEN_US); break;
    case 'c': servoWrite(SERVO_CLOSED_US); break;
    case 'x': servoOff(); break;
    case 'h': help(); break;
    case '\n': case '\r': break;
    default: Serial.printf("unknown '%c' (h for help)\n", ch);
  }
}
