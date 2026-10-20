#pragma once
#include "Arduino.h"
inline int g_servo_us = -1;      // last pulse written (what a real servo would see)
class Servo {
 public:
  void setPeriodHertz(int) {}
  void attach(int, int, int) {}
  void writeMicroseconds(int us) { g_servo_us = us; }
};
