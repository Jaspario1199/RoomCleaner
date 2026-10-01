/*
 * RoomCleaner firmware -- Arduino Uno + CNC Shield V3 + 4x stepper drivers (A4988/DRV8825) + 1 servo.
 *
 * Drives the four winch steppers and the gripper servo, homes on limit switches,
 * and takes simple newline commands over USB serial from the Python host:
 *
 *   H DETACHED  -> home detached winches to switches, replies "HOMED"
 *   M a b c d    -> move winches to absolute step counts a b c d, replies "DONE"
 *   G <deg>      -> set gripper servo angle, replies "OK"
 *   ?            -> replies "POS a b c d"
 *   S            -> replies "SW x y z a" (1 = switch pressed / wire fault)
 *
 * Needs the AccelStepper library (Library Manager -> "AccelStepper").
 *
 * Pin map = standard CNC Shield V3 (GRBL layout) with the 4th axis on D12/D13.
 * Because D12/D13 are the A-axis, the 4th endstop and the servo live on the
 * analog pins (used as digital). Verify against your board silkscreen.
 */

#include <AccelStepper.h>

#include <Servo.h>
#include "encoder_guard.h"

// ---- Pins (CNC Shield V3) -------------------------------------------------
const int EN_PIN = 8;               // driver enable (active LOW)
// step, dir per axis:  X, Y, Z, A
const int STEP_PINS[4] = {2, 3, 4, 12};
const int DIR_PINS[4]  = {5, 6, 7, 13};
// limit switches (NC to GND): X=D9, Y=D10, Z=D11, A=A3(17). INPUT_PULLUP.
const int LIMIT_PINS[4] = {9, 10, 11, 17};
const int SERVO_PIN = 18;           // A4

// ---- Motion tuning --------------------------------------------------------
const float MAX_SPEED = 500.0;     // steps/sec (cap for moves)
const float ACCEL = 600.0;          // steps/sec^2
const float HOME_SPEED = 300.0;     // steps/sec while seeking the switch
const long  HOME_BACKOFF = 200;     // steps to back off after the switch trips
// Homing reels the cable IN toward the switch. Set the sign so that direction
// matches your wiring (+1 or -1 per axis).
const int   HOME_DIR[4] = {-1, -1, -1, -1};

AccelStepper steppers[4];

Servo gripper;

void setup() {
  Serial.begin(115200);
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, LOW);        // enable drivers
  for (int i = 0; i < 4; i++) {
    steppers[i] = AccelStepper(AccelStepper::DRIVER, STEP_PINS[i], DIR_PINS[i]);
    steppers[i].setMaxSpeed(MAX_SPEED);
    steppers[i].setAcceleration(ACCEL);

    pinMode(LIMIT_PINS[i], INPUT_PULLUP);
  }
  for(int i=0;i<4;i++) { pinMode(STEP_PINS[i],OUTPUT); pinMode(DIR_PINS[i],OUTPUT); }
  gripper.attach(SERVO_PIN);
  Serial.println(F("READY"));
}

// Switches are wired Common + NC to GND with INPUT_PULLUP (fail-safe):
// at rest the NC contact holds the pin LOW; pressing the lever OPENS the
// circuit and the pullup takes the pin HIGH. A broken/unplugged wire also
// reads HIGH, i.e. "pressed" -- the axis refuses to move instead of
// grinding past a dead switch.
bool pressed(int i) { return digitalRead(LIMIT_PINS[i]) == HIGH; }

// These are bench defaults, NOT commissioned travel bounds.
const unsigned long HOME_TIMEOUT_MS = 120000UL;
const long HOME_MAX_STEPS = 100000L;
const long LATCH_MAX_STEPS = 2000L;
float moveSpeed = MAX_SPEED;
bool homed = false;
String interruptLine;

long encoderTicks[4],encoderBase[4],stepBase[4];
unsigned long encoderReceived=0,errorStarted[4]={0,0,0,0};
bool encoderSeen=false,encoderFault=false;
void syncEncoder(int axis){encoderBase[axis]=encoderTicks[axis];stepBase[axis]=steppers[axis].currentPosition();errorStarted[axis]=0;}
bool acceptEncoder(const String &line){
 long t[4];if(sscanf(line.c_str(),"E %ld %ld %ld %ld",&t[0],&t[1],&t[2],&t[3])!=4)return false;
 for(int i=0;i<4;i++)if(t[i]>1000000000L || t[i]<-1000000000L)return false;
 for(int i=0;i<4;i++)encoderTicks[i]=t[i];
 if(!encoderSeen)for(int i=0;i<4;i++)syncEncoder(i);
 encoderSeen=true;encoderReceived=millis();return true;
}
bool feedbackGood(){
 if(encoderFault || !encoderSeen || millis()-encoderReceived>250){homed=false;return false;}
 for(int i=0;i<4;i++){
  bool bad=encoderOutsideTolerance(encoderErrorNumerator(encoderTicks[i],encoderBase[i],steppers[i].currentPosition(),stepBase[i]));
  if(!bad)errorStarted[i]=0;
  else if(!errorStarted[i])errorStarted[i]=millis();
  else if(millis()-errorStarted[i]>100){encoderFault=true;homed=false;return false;}
 }
 return true;
}

bool interrupted() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      interruptLine.trim();
      if(interruptLine.startsWith("E ")){acceptEncoder(interruptLine);interruptLine="";continue;}
      bool stop = interruptLine == "X";
      if (!stop && interruptLine.length()) Serial.println(F("ERR busy"));
      interruptLine = "";
      if (stop) { homed = false; Serial.println(F("ERR stopped; rehome required")); return true; }
    } else if (interruptLine.length() < 64) interruptLine += c;
  }
  return false;
}

bool fail(const __FlashStringHelper *msg) {
  homed = false;
  // Leave drivers enabled to retain holding torque. Software STOP is not a brake.
  Serial.print(F("ERR ")); Serial.println(msg); return false;
}

bool boundedAxis(int axis, long target, float speed) {
  unsigned long started = millis();
  steppers[axis].moveTo(target);
  steppers[axis].setSpeed(speed * (target >= steppers[axis].currentPosition() ? 1 : -1));
  while (steppers[axis].distanceToGo()) {
    if (interrupted()) return false;
    if(!feedbackGood())return fail(F("encoder fault/stale; inspect and rehome"));
    if (millis()-started > HOME_TIMEOUT_MS) return fail(F("homing backoff timeout"));
    steppers[axis].runSpeedToPosition();
  }
  return true;
}

bool seekSwitch(int axis, float speed, long maxTravel) {
  unsigned long started = millis();
  long origin = steppers[axis].currentPosition();
  steppers[axis].setSpeed(speed*HOME_DIR[axis]);
  while (true) {
    if (interrupted()) return false;
    if(!feedbackGood())return fail(F("encoder fault/stale; inspect and rehome"));
    if (millis()-started > HOME_TIMEOUT_MS || labs(steppers[axis].currentPosition()-origin)>maxTravel)
      return fail(F("homing seek timeout/travel limit"));
    if (pressed(axis)) { delay(5); if (pressed(axis)) return true; }
    steppers[axis].runSpeed();
  }
}

void homeAll() {
  homed = false;
  if(!encoderSeen || millis()-encoderReceived>250){fail(F("healthy encoder stream required"));return;}
  encoderFault=false;
  for(int i=0;i<4;i++)syncEncoder(i);
  // Sequential homing is ONLY for a detached claw setup.
  // It is not a valid automatic homing path for a freely suspended four-cable claw.
  for (int i=0; i<4; i++) {
    if (pressed(i)) {
      if (!boundedAxis(i, steppers[i].currentPosition()-HOME_DIR[i]*HOME_BACKOFF, HOME_SPEED)) return;
      if (pressed(i)) { fail(F("switch stuck/open wire on initial backoff")); return; }
    }
    if (!seekSwitch(i, HOME_SPEED, HOME_MAX_STEPS)) return;
    if (!boundedAxis(i, steppers[i].currentPosition()-HOME_DIR[i]*HOME_BACKOFF, HOME_SPEED)) return;
    if (pressed(i)) { fail(F("switch failed to release/open wire")); return; }
    if (!seekSwitch(i, HOME_SPEED/3.0, LATCH_MAX_STEPS)) return;
    steppers[i].setCurrentPosition(0); syncEncoder(i); // preserve encoder baseline across step-datum reset
    if (!boundedAxis(i, -HOME_DIR[i]*HOME_BACKOFF, HOME_SPEED/3.0)) return;
    if (pressed(i)) { fail(F("switch failed final release")); return; }
    // Retain backoff step count so measured trigger lengths remain the datum.
  }
  unsigned long settling=millis();
  while(millis()-settling<150){if(interrupted())return;if(!feedbackGood()){fail(F("homing encoder final verification failed"));return;}}
  for(int i=0;i<4;i++)if(encoderOutsideTolerance(encoderErrorNumerator(encoderTicks[i],encoderBase[i],steppers[i].currentPosition(),stepBase[i]))){fail(F("homing encoder target mismatch"));return;}
  homed = true;
  Serial.println(F("HOMED"));
}

long coordinatedSpan, coordinatedDelta[4], pulseError[4];
int coordinatedDir[4];
void coordinatedTick() {
  bool pulse[4];
  for(int i=0;i<4;i++) {
    pulseError[i] += coordinatedDelta[i];
    pulse[i] = pulseError[i] >= coordinatedSpan;
    if(pulse[i]) {
      pulseError[i] -= coordinatedSpan;
      digitalWrite(STEP_PINS[i],HIGH);
    }
  }
  delayMicroseconds(3); // meets typical step-driver pulse width requirements
  for(int i=0;i<4;i++) if(pulse[i]) {
    digitalWrite(STEP_PINS[i],LOW);
    steppers[i].setCurrentPosition(steppers[i].currentPosition()+coordinatedDir[i]);
  }
}
// One accelerated scalar stepper clocks a Bresenham pulse distributor. This
// preserves four-axis progress ratios instead of giving each motor its own ramp.
AccelStepper coordinator(coordinatedTick, coordinatedTick);

void moveTo4(long a, long b, long c, long d) {
  if (!homed) { fail(F("home required")); return; }
  if(!feedbackGood()){fail(F("encoder stream required"));return;}
  for(int i=0;i<4;i++)if(encoderOutsideTolerance(encoderErrorNumerator(encoderTicks[i],encoderBase[i],steppers[i].currentPosition(),stepBase[i]))){fail(F("encoder preflight mismatch"));return;}
  long targets[4] = {a,b,c,d};
  coordinatedSpan=0;
  for(int i=0;i<4;i++) {
    long delta=targets[i]-steppers[i].currentPosition();
    coordinatedDelta[i]=labs(delta);
    coordinatedDir[i]=delta>=0 ? 1 : -1;
    coordinatedSpan=max(coordinatedSpan,coordinatedDelta[i]);
    digitalWrite(DIR_PINS[i],delta>=0 ? HIGH : LOW);
  }
  if (coordinatedSpan > 500000L) { fail(F("move exceeds provisional travel bound")); return; }
  for(int i=0;i<4;i++) pulseError[i]=coordinatedSpan/2;
  coordinator.setCurrentPosition(0);
  coordinator.setMaxSpeed(moveSpeed);
  coordinator.setAcceleration(ACCEL);
  coordinator.moveTo(coordinatedSpan);
  unsigned long started=millis();
  unsigned long deadline=(unsigned long)(1000.0*(coordinatedSpan/moveSpeed + 2.0*moveSpeed/ACCEL + 10.0));
  while(coordinator.distanceToGo()) {
    if(interrupted()) return;
    if(!feedbackGood()){fail(F("encoder following error/stale; inspect and rehome"));return;}
    if(millis()-started > deadline) { fail(F("move timeout")); return; }
    for(int i=0;i<4;i++) if(pressed(i)) { fail(F("limit switch/open wire during move")); return; }
    coordinator.run();
  }
  // Allow last sensor samples to catch up; DONE means rotation is within tolerance.
  unsigned long settling=millis();
  while(millis()-settling<150){
    if(interrupted())return;
    if(!feedbackGood()){fail(F("encoder final verification failed"));return;}
  }
  for(int i=0;i<4;i++)if(encoderOutsideTolerance(encoderErrorNumerator(encoderTicks[i],encoderBase[i],steppers[i].currentPosition(),stepBase[i]))){fail(F("encoder target not reached"));return;}
  Serial.println(F("DONE"));
}

void loop() {
  if(homed && !feedbackGood())fail(F("idle encoder fault/stale; inspect and rehome"));
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;
  char cmd = line.charAt(0);

  if(cmd=='E'){acceptEncoder(line);if(homed && !feedbackGood())fail(F("idle encoder fault; inspect and rehome"));}
  else if(cmd=='B'){
    int axis;long delta;
    if(sscanf(line.c_str(),"B DETACHED %d %ld",&axis,&delta)!=2 || axis<0 || axis>3 || labs(delta)>160 || delta==0){Serial.println(F("ERR bad detached bench jog"));return;}
    homed=false;long target=steppers[axis].currentPosition()+delta;
    steppers[axis].moveTo(target);steppers[axis].setSpeed(delta>0?100:-100);
    while(steppers[axis].distanceToGo()){
      if(interrupted())return;
      if(delta*HOME_DIR[axis]>0 && pressed(axis)){fail(F("bench jog hit limit"));return;}
      steppers[axis].runSpeedToPosition();
    }
    Serial.println(F("BENCH_DONE")); // explicit bounded commissioning exception; no suspension
  }
  else if (cmd == 'H') {
    if (line != "H DETACHED") Serial.println(F("ERR detached claw acknowledgement required"));
    else homeAll();
  } else if (cmd == 'M') {
    long a, b, c, d;
    if (sscanf(line.c_str(), "M %ld %ld %ld %ld", &a, &b, &c, &d) == 4) {
      moveTo4(a, b, c, d);
    } else {
      Serial.println(F("ERR bad M"));
    }
  } else if (cmd == 'X') {
    homed=false; Serial.println(F("STOPPED"));
  } else if (cmd == 'V') {
    float speed=line.substring(1).toFloat();
    if(speed>0 && speed<=MAX_SPEED) { moveSpeed=speed; Serial.println(F("OK")); }
    else Serial.println(F("ERR speed outside range"));
  } else if (cmd == 'G') {
    int deg;
    if (sscanf(line.c_str(), "G %d", &deg) == 1) {
      gripper.write(constrain(deg, 0, 180));
      Serial.println(F("OK"));
    } else {
      Serial.println(F("ERR bad G"));
    }
  } else if (cmd == 'S') {
    // Switch states for bench testing: 1 = pressed (or wire fault), 0 = at rest.
    Serial.print(F("SW "));
    for (int i = 0; i < 4; i++) {
      Serial.print(pressed(i) ? 1 : 0);
      Serial.print(i < 3 ? ' ' : '\n');
    }
  } else if (cmd == '?') {
    Serial.print(F("POS "));
    for (int i = 0; i < 4; i++) {
      Serial.print(steppers[i].currentPosition());
      Serial.print(i < 3 ? ' ' : '\n');
    }
  } else {
    Serial.println(F("ERR unknown"));
  }
}
