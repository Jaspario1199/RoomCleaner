#pragma once
// Minimal Arduino-ESP32 stand-ins for a HOST build of firmware/claw_s3 (test only; not an ESP32 build).
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <algorithm>

class String {
 public:
  String() {}
  String(const char* s) : s_(s) {}
  String(const std::string& s) : s_(s) {}
  String(unsigned long long v) : s_(std::to_string(v)) {}
  String(unsigned long v) : s_(std::to_string(v)) {}
  String(unsigned int v) : s_(std::to_string(v)) {}
  String(int v) : s_(std::to_string(v)) {}
  const char* c_str() const { return s_.c_str(); }
  bool operator==(const char* o) const { return s_ == o; }
  bool operator!=(const char* o) const { return s_ != o; }
  String operator+(const char* o) const { return String(s_ + o); }
  String operator+(const String& o) const { return String(s_ + o.s_); }
 private:
  std::string s_;
};

template <class T, class L, class H>
inline T constrain(T x, L lo, H hi) { return x < (T)lo ? (T)lo : (x > (T)hi ? (T)hi : x); }
inline void delay(int) {}
inline uint32_t analogReadMilliVolts(int) { return 2600; }   // x 3.0 divider = 7.8 V
inline void analogReadResolution(int) {}
struct SerialT {
  void begin(int) {}
  void print(const char*) {}
  template <class... A> void printf(const char*, A...) {}
};
static SerialT Serial;
#define LEDC_CHANNEL_0 0
#define LEDC_TIMER_0 0
struct IPAddress { String toString() const { return String("0.0.0.0"); } };
