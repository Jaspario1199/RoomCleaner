// RoomCleaner station driver bench test, Rev D pins (2026-10-21).
// Board: Seeed XIAO ESP32-C3, "USB CDC On Boot: Enabled", Serial Monitor 115200.
// UNLOADED BENCH ONLY: motor free (nothing on the spool), JP1 open, USB powers logic.
// Pins match firmware/winch_station: STEP GPIO3 (D1), DIR GPIO4 (D2),
// ENABLE GPIO5 (D3, active LOW), HOME GPIO10 (D10, NC switch to GND).
//
// Commands (type the letter, press Enter):
//   f  = 200 steps forward  (one revolution in full step)
//   r  = 200 steps reverse
//   h  = hold: enable the driver and keep it energised (feel the shaft resist)
//   o  = off: disable the driver (shaft turns freely)
//   s  = print the switch state

constexpr int STEP_PIN = 3, DIR_PIN = 4, EN_PIN = 5, HOME_PIN = 10;
constexpr int STEPS = 200;           // one rev at full step (MS1-3 to GND)
constexpr int STEP_DELAY_US = 2500;  // 200 steps/s: slow and quiet for a first test

void move(bool forward) {
  digitalWrite(DIR_PIN, forward ? HIGH : LOW);
  digitalWrite(EN_PIN, LOW);                    // enable
  delay(5);
  for (int i = 0; i < STEPS; i++) {
    if (digitalRead(HOME_PIN) == HIGH) {        // NC opened = switch pressed or wire open
      Serial.println("STOP: switch open/pressed");
      break;
    }
    digitalWrite(STEP_PIN, HIGH); delayMicroseconds(5);
    digitalWrite(STEP_PIN, LOW);  delayMicroseconds(STEP_DELAY_US);
  }
  Serial.println(forward ? "done forward (driver still holding; 'o' to release)"
                         : "done reverse (driver still holding; 'o' to release)");
}

void setup() {
  pinMode(EN_PIN, OUTPUT);  digitalWrite(EN_PIN, HIGH);   // disabled at boot
  pinMode(STEP_PIN, OUTPUT); digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT);  digitalWrite(DIR_PIN, LOW);
  pinMode(HOME_PIN, INPUT_PULLUP);
  Serial.begin(115200);
  delay(1500);
  Serial.println("driver bench test: f / r / h / o / s");
}

void loop() {
  if (!Serial.available()) return;
  char c = Serial.read();
  if (c == 'f') move(true);
  else if (c == 'r') move(false);
  else if (c == 'h') { digitalWrite(EN_PIN, LOW);  Serial.println("holding"); }
  else if (c == 'o') { digitalWrite(EN_PIN, HIGH); Serial.println("off"); }
  else if (c == 's') Serial.println(digitalRead(HOME_PIN) == HIGH ? "switch OPEN (pressed / unplugged)"
                                                                    : "switch CLOSED (released)");
}
