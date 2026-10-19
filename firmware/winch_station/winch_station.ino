/*
 * RoomCleaner winch station -- Seeed XIAO ESP32-C3 + red A4988 carrier +
 * AS5600 on the spool + NC bead switch (Rev C electrical package,
 * docs/electrical/station_revC_20261016).
 *
 * This sketch is only hardware glue. All protocol and motion logic lives in
 * station_core.h, which is conformance-tested against the Python reference
 * (roomcleaner/cdpr/station_core.py, tests/firmware). Behaviour summary:
 *   - boots OFF (EN high via the 10k pull-up: no holding torque) until the host
 *     sends cfg + arm; a fault NEVER disables the driver; only a confirmed
 *     disarm ("claw_supported") does
 *   - motion = Hermite segments in this station's clock; steps generated here
 *   - lease: no valid host message for lease_us -> coordinated self-hold,
 *     broadcast to the other stations
 *   - a reboot starts a new boot id/epoch: the host must re-reference L0
 *
 * Pins (Rev C): STEP GPIO3, DIR GPIO4, EN GPIO5 (active low, 10k pull-up),
 * HOME GPIO10 (NC switch to GND, internal pull-up), AS5600 SDA GPIO6 / SCL GPIO7.
 * The A4988 has no fault output (unlike the DRV8825 bench code's GPIO20).
 *
 * Board: "XIAO_ESP32C3", USB CDC On Boot enabled, arduino-esp32 core 3.x.
 * Copy secrets.example.h -> secrets.h and set STATION_ID, Wi-Fi, static IP.
 *
 * STATUS: written against the core API; not yet compiled for the ESP32 in this
 * workspace (no Arduino toolchain here). First physical run = commissioning
 * steps 2-4 with tools/commission_station.py on an UNLOADED spool.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include "esp_random.h"
#include "esp_timer.h"
#include "secrets.h"        // STATION_ID, WIFI_SSID, WIFI_PASS, STATION_IP, GATEWAY, SUBNET
#include "station_core.h"
#include "as5600.h"
#include "stepgen.h"

using namespace roomcleaner::winch;

constexpr int STEP_PIN = 3, DIR_PIN = 4, EN_PIN = 5, HOME_PIN = 10, SDA_PIN = 6, SCL_PIN = 7;
constexpr uint16_t UDP_PORT = 8771;          // stations listen here
constexpr uint16_t HOST_PORT = 8770;         // host transport binds here
constexpr int64_t PERIOD_US = 1000;          // control period (1 kHz)

WiFiUDP udp;
AS5600 encoder;
StationCore* core = nullptr;
IPAddress hostIp;
bool haveHost = false;
int32_t encCounts = 0;
int64_t nextTick = 0;
char rx[json::kMaxDatagram + 1];

static int64_t nowUs() { return esp_timer_get_time(); }

void sendOut(const OutMsg& m) {
  if (m.broadcast) {                          // peers and host: subnet broadcast
    udp.beginPacket(IPAddress(255, 255, 255, 255), UDP_PORT);
    udp.write(reinterpret_cast<const uint8_t*>(m.data), m.len);
    udp.endPacket();
  }
  if (haveHost) {
    udp.beginPacket(hostIp, HOST_PORT);
    udp.write(reinterpret_cast<const uint8_t*>(m.data), m.len);
    udp.endPacket();
  }
}

void receive(int64_t now) {
  int n;
  while ((n = udp.parsePacket()) > 0) {
    IPAddress from = udp.remoteIP();
    uint16_t fromPort = udp.remotePort();
    int len = udp.read(rx, sizeof(rx) - 1);
    if (len <= 0 || from == WiFi.localIP()) continue;     // own broadcast echo
    rx[len] = 0;
    // The host is whoever talks from HOST_PORT; peers broadcast from UDP_PORT.
    bool fromHost = fromPort == HOST_PORT;
    if (fromHost) {
      hostIp = from;
      haveHost = true;
    }
    core->handleDatagram(rx, len, now, fromHost);
  }
}

void setup() {
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, HIGH);                 // disabled until armed
  pinMode(HOME_PIN, INPUT_PULLUP);
  stepgen::begin(STEP_PIN, DIR_PIN);
  Wire.begin(SDA_PIN, SCL_PIN, 400000);
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);                       // latency matters more than power here
  WiFi.config(STATION_IP, GATEWAY, SUBNET);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(100);
  udp.begin(UDP_PORT);
  core = new StationCore(esp_random(), PERIOD_US);   // one allocation at boot, none afterwards
  Serial.printf("station %s %s boot\n", STATION_ID, WiFi.localIP().toString().c_str());
  nextTick = nowUs();
}

void loop() {
  int64_t now = nowUs();
  if (now < nextTick) return;
  nextTick += PERIOD_US;
  if (now - nextTick > 5 * PERIOD_US) nextTick = now + PERIOD_US;   // the core flags TIMING itself

  receive(now);
  bool encValid = encoder.sample(encCounts);
  const StationCore::Params* p = core->params();
  bool level = digitalRead(HOME_PIN) == HIGH;                    // HIGH = contacts open
  bool nc = p ? p->sw_nc != 0 : true;
  bool swActive = nc ? level : !level;                           // NC: open = actuated or broken wire
  int steps = core->update(now, encCounts, encValid, swActive);

  digitalWrite(EN_PIN, core->armed() ? LOW : HIGH);              // OFF is the only disabled state
  if (steps != 0 && core->armed()) {
    int sign = p ? (p->step_sign < 0 ? -1 : 1) : 1;
    stepgen::load(steps, PERIOD_US, sign);
  }
  OutMsg m;
  while (core->drain(m)) sendOut(m);
  if (WiFi.status() != WL_CONNECTED) WiFi.reconnect();          // lease handles the outage
}
