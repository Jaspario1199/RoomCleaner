// RoomCleaner winch station bench test, Rev D layout (2026-10-25).
// Checks each part of the breadboard one at a time from the Serial Monitor: driver held off at boot, homing switch,
// AS5600 encoder on I2C, then slow motor jogs compared against the encoder.
//
// Board: "ESP32 Dev Module" (ELEGOO ESP32 DevKit, docs/electrical/station_revD_20261021/BREADBOARD_LAYOUT_ESP32.md)
//    or "XIAO_ESP32C3" (docs/electrical/station_revD_20261021/BREADBOARD_LAYOUT.md). Serial Monitor 115200, "Newline".
// Power: USB with JP1 OUT for every test. The 12 V supply is needed only for the motor tests (menu e / f / b / t).
// Not the station firmware: no Wi-Fi, no host. Flash winch_station.ino again when the bench test passes.

#include <Wire.h>

#if CONFIG_IDF_TARGET_ESP32C3        // Seeed XIAO ESP32-C3
constexpr int STEP_PIN = 3, DIR_PIN = 4, EN_PIN = 5, HOME_PIN = 10, SDA_PIN = 6, SCL_PIN = 7;
const char* BOARD = "XIAO ESP32-C3";
#elif CONFIG_IDF_TARGET_ESP32        // ELEGOO ESP32 DevKit (ESP-WROOM-32)
constexpr int STEP_PIN = 25, DIR_PIN = 26, EN_PIN = 27, HOME_PIN = 32, SDA_PIN = 21, SCL_PIN = 22;
const char* BOARD = "ELEGOO ESP32 DevKit";
#else
#error "station_bench_test: build for XIAO_ESP32C3 or ESP32 Dev Module"
#endif

constexpr uint8_t AS5600_ADDR = 0x36;
constexpr uint8_t REG_STATUS = 0x0B, REG_RAW_ANGLE = 0x0C, REG_AGC = 0x1A;
constexpr int COUNTS_PER_REV = 4096;
constexpr int MOTOR_STEPS_PER_REV = 200;     // full steps (MS1-3 low on the board)
int gearRatio = 1;                           // 1 = spool on the motor shaft; 3 = the 3:1 spur stage (menu g)
constexpr int STEP_RATE_HZ = 200;            // slow on purpose: about 1 motor rev/s
bool driverOn = false;

// ---------- driver ----------
void driverEnable(bool on) {                 // A4988 EN is active LOW; R1 holds it HIGH (off) at boot
  digitalWrite(EN_PIN, on ? LOW : HIGH);
  driverOn = on;
  Serial.printf("driver %s (EN pin %s)\n", on ? "ENABLED: motor holds torque" : "disabled: motor free", on ? "LOW" : "HIGH");
}

void stepPulses(long n, bool forward) {
  digitalWrite(DIR_PIN, forward ? HIGH : LOW);
  delayMicroseconds(5);                      // DIR setup time before the first STEP edge
  const uint32_t period_us = 1000000UL / STEP_RATE_HZ;
  for (long i = 0; i < n; i++) {
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(5);                    // A4988 needs at least 1 us high
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(period_us - 5);
    if ((i & 63) == 0) yield();
  }
}

// ---------- encoder ----------
int readReg(uint8_t reg, uint8_t len) {      // -1 when the encoder does not answer
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(AS5600_ADDR, len) != len) return -1;
  int v = 0;
  for (uint8_t i = 0; i < len; i++) v = (v << 8) | Wire.read();
  return v;
}

int rawAngle() {
  int v = readReg(REG_RAW_ANGLE, 2);
  return v < 0 ? -1 : (v & 0x0FFF);
}

void magnetReport() {
  int st = readReg(REG_STATUS, 1), agc = readReg(REG_AGC, 1), a = rawAngle();
  if (st < 0) { Serial.println("encoder: NO ANSWER at 0x36 (check SDA/SCL rows 9/10, VCC on 3V3, GND)"); return; }
  bool md = st & 0x20, ml = st & 0x10, mh = st & 0x08;
  Serial.printf("encoder: angle %4d / 4096 (%6.1f deg)  magnet %s%s%s  AGC %d\n", a, a * 360.0 / COUNTS_PER_REV,
                md ? "DETECTED" : "NOT detected", ml ? ", too WEAK (move closer)" : "", mh ? ", too STRONG (move away)" : "", agc);
}

void i2cScan() {
  Serial.println("I2C scan:");
  int found = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  device at 0x%02X%s\n", a, a == AS5600_ADDR ? "  <- AS5600 encoder" : "");
      found++;
    }
  }
  if (!found) Serial.println("  nothing found: SDA/SCL swapped, wrong rows, or the encoder has no power");
}

// ---------- homing switch ----------
void homeReport() {
  int v = digitalRead(HOME_PIN);
  Serial.printf("home switch: %s  (pin %s)\n", v == LOW ? "at REST (NC closed)" : "PRESSED or wire open", v == LOW ? "LOW" : "HIGH");
}

// ---------- tests ----------
void jog(bool forward) {
  if (!driverOn) { Serial.println("driver is disabled: press e first (12 V must be on)"); return; }
  long n = MOTOR_STEPS_PER_REV / 4;          // a quarter motor turn
  int a0 = rawAngle();
  stepPulses(n, forward);
  delay(100);
  int a1 = rawAngle();
  if (a0 < 0 || a1 < 0) { Serial.printf("jogged %ld steps %s (encoder not answering)\n", n, forward ? "forward" : "back"); return; }
  int d = a1 - a0;
  if (d > COUNTS_PER_REV / 2) d -= COUNTS_PER_REV;
  if (d < -COUNTS_PER_REV / 2) d += COUNTS_PER_REV;
  float expect = (float)n * COUNTS_PER_REV / (MOTOR_STEPS_PER_REV * gearRatio);
  Serial.printf("jogged %ld steps %s: encoder moved %+d counts, expected about %.0f (either sign)\n", n, forward ? "forward" : "back",
                d, expect);
}

void turnTest() {
  if (!driverOn) { Serial.println("driver is disabled: press e first (12 V must be on)"); return; }
  long n = (long)MOTOR_STEPS_PER_REV * gearRatio;   // one spool revolution
  Serial.printf("one spool turn = %ld steps at %d Hz, forward then back...\n", n, STEP_RATE_HZ);
  int a0 = rawAngle();
  long seen = 0;
  int prev = a0;
  digitalWrite(DIR_PIN, HIGH);
  delayMicroseconds(5);
  for (long i = 0; i < n; i++) {
    stepPulses(1, true);
    if (i % 10 == 0 && a0 >= 0) {            // unwrap the encoder as it turns
      int a = rawAngle();
      int d = a - prev;
      if (d > COUNTS_PER_REV / 2) d -= COUNTS_PER_REV;
      if (d < -COUNTS_PER_REV / 2) d += COUNTS_PER_REV;
      seen += d; prev = a;
    }
  }
  delay(100);
  if (a0 >= 0) {
    int a = rawAngle(), d = a - prev;
    if (d > COUNTS_PER_REV / 2) d -= COUNTS_PER_REV;
    if (d < -COUNTS_PER_REV / 2) d += COUNTS_PER_REV;
    seen += d;
    long err = labs(seen) - COUNTS_PER_REV;
    Serial.printf("  forward: encoder %+ld counts (expected 4096 either sign), error %+ld counts -> %s\n", seen, err,
                  labs(err) <= 60 ? "PASS" : "CHECK (skipped steps, loose magnet, or wrong gear ratio, menu g)");
    Serial.printf("  encoder sign for this DIR-high direction: %s\n", seen > 0 ? "+" : "-");
  }
  stepPulses(n, false);
  Serial.println("  back to the start");
}

void help() {
  Serial.printf("\nRoomCleaner station bench test (%s)\n", BOARD);
  Serial.printf("pins: STEP %d  DIR %d  EN %d  HOME %d  SDA %d  SCL %d   gear ratio %d:1\n", STEP_PIN, DIR_PIN, EN_PIN, HOME_PIN, SDA_PIN, SCL_PIN, gearRatio);
  Serial.println("  s  status: home switch + encoder");
  Serial.println("  i  I2C scan (the encoder should be at 0x36)");
  Serial.println("  w  watch home switch + encoder 5x/s (any key stops)");
  Serial.println("  e  enable driver (12 V on)      d  disable driver");
  Serial.println("  f  jog forward 1/4 motor turn    b  jog back 1/4 motor turn");
  Serial.println("  t  one spool turn, checked against the encoder");
  Serial.println("  g  toggle gear ratio 1:1 / 3:1");
  Serial.println("  h  this menu");
}

void setup() {
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, HIGH);                // driver OFF before anything else
  pinMode(STEP_PIN, OUTPUT); digitalWrite(STEP_PIN, LOW);
  pinMode(DIR_PIN, OUTPUT);  digitalWrite(DIR_PIN, LOW);
  pinMode(HOME_PIN, INPUT);                  // R4 10k is the pull-up
  Serial.begin(115200);
  delay(500);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);
  help();
  Serial.println("\nboot check:");
  Serial.println("  driver held disabled (EN HIGH): the motor must NOT move or hold.");
  homeReport();
  i2cScan();
  magnetReport();
}

void loop() {
  if (!Serial.available()) { delay(10); return; }
  char c = Serial.read();
  switch (c) {
    case 's': homeReport(); magnetReport(); break;
    case 'i': i2cScan(); break;
    case 'w':
      while (Serial.available()) Serial.read();
      Serial.println("watching (any key stops)...");
      while (!Serial.available()) {
        int a = rawAngle();
        Serial.printf("home %s   angle %s%d\n", digitalRead(HOME_PIN) == LOW ? "rest   " : "PRESSED", a < 0 ? "no answer " : "", a);
        delay(200);
      }
      while (Serial.available()) Serial.read();
      break;
    case 'e': driverEnable(true); break;
    case 'd': driverEnable(false); break;
    case 'f': jog(true); break;
    case 'b': jog(false); break;
    case 't': turnTest(); break;
    case 'g': gearRatio = gearRatio == 1 ? 3 : 1; Serial.printf("gear ratio %d:1\n", gearRatio); break;
    case 'h': help(); break;
    case '\n': case '\r': break;
    default: Serial.printf("unknown '%c' (h for help)\n", c);
  }
}
