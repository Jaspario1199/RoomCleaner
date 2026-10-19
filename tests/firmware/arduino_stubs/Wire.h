#pragma once
#include "Arduino.h"
struct TwoWire { void begin(int,int,uint32_t){} void beginTransmission(int){} void write(uint8_t){} int endTransmission(bool=true){return 0;}
  int requestFrom(int,int n){return n;} int available(){return 0;} int read(){return 0;} };
static TwoWire Wire;
