/*
 * RoomCleaner wireless effector -- ESP32 on the claw.
 *
 * The gripper servo lives here, not on the central Arduino. The ESP32 joins your
 * WiFi and runs a tiny HTTP server; the host computer sends grip/release:
 *
 *     GET /grip?angle=120     -> curl the tentacles, replies "OK 120"
 *     GET /release?angle=20   -> open the tentacles, replies "OK 20"
 *     GET /status             -> replies "READY <angle>"
 *
 * Only the 4 Dyneema cables touch the effector -- no wire crosses the room.
 * Grip/release aren't time-critical, so WiFi latency here is harmless.
 *
 * Power: a small LiPo on the effector (through a 5-6 V buck/boost to the servo).
 * Optionally add charging contacts at the rest/dock position.
 *
 * Board: any ESP32 dev board. Set the servo pin to a free GPIO.
 * Library: ESP32Servo (Library Manager -> "ESP32Servo").
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <ESPmDNS.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* HOSTNAME  = "roomcleaner-claw";   // -> http://roomcleaner-claw.local

const int SERVO_PIN = 13;
const int DEFAULT_RELEASE = 20;

WebServer server(80);
Servo gripper;
int currentAngle = DEFAULT_RELEASE;

void setAngle(int a) {
  currentAngle = constrain(a, 0, 180);
  gripper.write(currentAngle);
}

void handleGrip() {
  int a = server.hasArg("angle") ? server.arg("angle").toInt() : 120;
  setAngle(a);
  server.send(200, "text/plain", "OK " + String(currentAngle));
}

void handleRelease() {
  int a = server.hasArg("angle") ? server.arg("angle").toInt() : DEFAULT_RELEASE;
  setAngle(a);
  server.send(200, "text/plain", "OK " + String(currentAngle));
}

void handleStatus() {
  server.send(200, "text/plain", "READY " + String(currentAngle));
}

void setup() {
  Serial.begin(115200);
  gripper.attach(SERVO_PIN);
  setAngle(DEFAULT_RELEASE);          // start open

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.println("\nWiFi: " + WiFi.localIP().toString());

  if (MDNS.begin(HOSTNAME)) Serial.println("mDNS: http://" + String(HOSTNAME) + ".local");

  server.on("/grip", handleGrip);
  server.on("/release", handleRelease);
  server.on("/status", handleStatus);
  server.begin();
}

void loop() {
  server.handleClient();
}
