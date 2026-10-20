#pragma once
#include "Arduino.h"
#define WIFI_STA 1
#define WL_CONNECTED 3
struct WiFiT {
  void mode(int) {}
  void setHostname(const char*) {}
  void setSleep(bool) {}
  void begin(const char*, const char*) {}
  int status() { return WL_CONNECTED; }
  void reconnect() {}
  IPAddress localIP() { return {}; }
};
static WiFiT WiFi;
