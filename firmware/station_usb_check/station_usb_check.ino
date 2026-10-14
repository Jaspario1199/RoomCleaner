// RoomCleaner station bring-up, USB-only check, Rev A (2026-10-14).
// Board: Seeed XIAO ESP32-C3. Enable USB CDC On Boot.
// Disconnect ALL external wiring, driver, motor supply and battery.
// This tests upload/serial only. It does not configure or test motor control.

void setup() {
  Serial.begin(115200);
}

void loop() {
  Serial.println("RoomCleaner station: USB OK");
  delay(1000);
}
