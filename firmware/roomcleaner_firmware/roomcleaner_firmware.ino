/*
 * RoomCleaner firmware -- Arduino Uno + CNC Shield V3 + 4x DRV8825 + 1 servo.
 *
 * Drives the four winch steppers and the gripper servo, homes on limit switches,
 * and takes simple newline commands over USB serial from the Python host:
 *
 *   H            -> home all winches to their switches, replies "HOMED"
 *   M a b c d    -> move winches to absolute step counts a b c d, replies "DONE"
 *   G <deg>      -> set gripper servo angle, replies "OK"
 *   ?            -> replies "POS a b c d"
 *
 * Needs the AccelStepper library (Library Manager -> "AccelStepper").
 *
 * Pin map = standard CNC Shield V3 (GRBL layout) with the 4th axis on D12/D13.
 * Because D12/D13 are the A-axis, the 4th endstop and the servo live on the
 * analog pins (used as digital). Verify against your board silkscreen.
 */

#include <AccelStepper.h>
#include <MultiStepper.h>
#include <Servo.h>

// ---- Pins (CNC Shield V3) -------------------------------------------------
const int EN_PIN = 8;               // driver enable (active LOW)
// step, dir per axis:  X, Y, Z, A
const int STEP_PINS[4] = {2, 3, 4, 12};
const int DIR_PINS[4]  = {5, 6, 7, 13};
// limit switches (NC to GND): X=D9, Y=D10, Z=D11, A=A3(17). INPUT_PULLUP.
const int LIMIT_PINS[4] = {9, 10, 11, 17};
const int SERVO_PIN = 18;           // A4

// ---- Motion tuning --------------------------------------------------------
const float MAX_SPEED = 1200.0;     // steps/sec (cap for moves)
const float ACCEL = 600.0;          // steps/sec^2
const float HOME_SPEED = 300.0;     // steps/sec while seeking the switch
const long  HOME_BACKOFF = 200;     // steps to back off after the switch trips
// Homing reels the cable IN toward the switch. Set the sign so that direction
// matches your wiring (+1 or -1 per axis).
const int   HOME_DIR[4] = {-1, -1, -1, -1};

AccelStepper steppers[4];
MultiStepper group;
Servo gripper;

void setup() {
  Serial.begin(115200);
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, LOW);        // enable drivers
  for (int i = 0; i < 4; i++) {
    steppers[i] = AccelStepper(AccelStepper::DRIVER, STEP_PINS[i], DIR_PINS[i]);
    steppers[i].setMaxSpeed(MAX_SPEED);
    steppers[i].setAcceleration(ACCEL);
    group.addStepper(steppers[i]);
    pinMode(LIMIT_PINS[i], INPUT_PULLUP);
  }
  gripper.attach(SERVO_PIN);
  Serial.println("READY");
}

// A switch reads LOW when pressed (NC to GND + INPUT_PULLUP).
bool pressed(int i) { return digitalRead(LIMIT_PINS[i]) == LOW; }

void homeAll() {
  // Home one axis at a time -- safer for cables (avoids tangling).
  for (int i = 0; i < 4; i++) {
    steppers[i].setSpeed(HOME_SPEED * HOME_DIR[i]);
    while (!pressed(i)) {
      steppers[i].runSpeed();
    }
    steppers[i].setCurrentPosition(0);
    // Back off the switch a touch so it isn't held.
    steppers[i].moveTo(-HOME_DIR[i] * HOME_BACKOFF);
    while (steppers[i].distanceToGo() != 0) steppers[i].run();
    steppers[i].setCurrentPosition(0);
  }
  Serial.println("HOMED");
}

void moveTo4(long a, long b, long c, long d) {
  long targets[4] = {a, b, c, d};
  group.moveTo(targets);
  group.runSpeedToPosition();       // blocks until all four arrive
  Serial.println("DONE");
}

void loop() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;
  char cmd = line.charAt(0);

  if (cmd == 'H') {
    homeAll();
  } else if (cmd == 'M') {
    long a, b, c, d;
    if (sscanf(line.c_str(), "M %ld %ld %ld %ld", &a, &b, &c, &d) == 4) {
      moveTo4(a, b, c, d);
    } else {
      Serial.println("ERR bad M");
    }
  } else if (cmd == 'G') {
    int deg;
    if (sscanf(line.c_str(), "G %d", &deg) == 1) {
      gripper.write(constrain(deg, 0, 180));
      Serial.println("OK");
    } else {
      Serial.println("ERR bad G");
    }
  } else if (cmd == '?') {
    Serial.print("POS ");
    for (int i = 0; i < 4; i++) {
      Serial.print(steppers[i].currentPosition());
      Serial.print(i < 3 ? ' ' : '\n');
    }
  } else {
    Serial.println("ERR unknown");
  }
}
