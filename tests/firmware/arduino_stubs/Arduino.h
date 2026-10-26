#pragma once
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cmath>
#include <cstring>
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define IRAM_ATTR
inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline int digitalRead(int) { return 0; }
inline void delay(int) {}
struct hw_timer_t {};
inline hw_timer_t* timerBegin(uint32_t) { static hw_timer_t t; return &t; }
inline void timerAttachInterrupt(hw_timer_t*, void (*)()) {}
inline void timerAlarm(hw_timer_t*, uint64_t, bool, uint64_t) {}
typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(x) (void)(x)
#define portEXIT_CRITICAL(x) (void)(x)
struct SerialT { void begin(int) {} void println(const char*) {} template <class... A> void printf(const char*, A...) {} };
static SerialT Serial;
struct IPAddress { IPAddress(int=0,int=0,int=0,int=0) {} bool operator==(const IPAddress&) const { return false; }
  struct S { const char* c_str() const { return ""; } }; S toString() const { return {}; } };
