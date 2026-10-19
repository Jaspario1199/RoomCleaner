#pragma once
#include "Arduino.h"
struct WiFiUDP { void begin(uint16_t){} int parsePacket(){return 0;} IPAddress remoteIP(){return {};} uint16_t remotePort(){return 0;}
  int read(char*,size_t){return 0;} void beginPacket(IPAddress,uint16_t){} size_t write(const uint8_t*,size_t n){return n;} int endPacket(){return 1;} };
