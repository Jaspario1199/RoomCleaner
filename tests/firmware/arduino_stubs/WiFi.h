#pragma once
#include "Arduino.h"
#define WIFI_STA 1
#define WL_CONNECTED 3
struct WiFiT { void mode(int){} void setSleep(bool){} void config(IPAddress,IPAddress,IPAddress){} void begin(const char*,const char*){}
  int status(){return 3;} void reconnect(){} IPAddress localIP(){return {};} };
static WiFiT WiFi;
