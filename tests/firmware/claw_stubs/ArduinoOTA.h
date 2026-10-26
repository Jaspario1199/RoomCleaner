#pragma once
// ArduinoOTA stand-in for the host build (test only): counts handle() calls so a test can see when updates are listened for.
inline int g_ota_handles = 0;
struct ArduinoOTAClass {
  void setHostname(const char*) {}
  void setPassword(const char*) {}
  template <class F> void onStart(F) {}
  void begin() {}
  void handle() { g_ota_handles++; }
};
static ArduinoOTAClass ArduinoOTA;
