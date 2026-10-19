// Step pulse generator for the A4988: the control loop hands over a signed
// step count for the next control period; a hardware timer spreads the
// pulses evenly across that period (DDA). The network never times pulses.
//
// Timing: 40 kHz tick (25 us). A pulse is one tick high, at least one tick
// low (A4988 needs >= 1 us each). DIR is written when a period is loaded,
// >= 25 us before the first STEP edge (A4988 setup 200 ns).
#pragma once
#include <Arduino.h>

namespace stepgen {

constexpr uint32_t TICK_HZ = 40000;
static int stepPin = -1, dirPin = -1;
static hw_timer_t* timer = nullptr;
static volatile int32_t remaining = 0;       // pulses left this period (>= 0)
static volatile uint32_t interval = 1;       // ticks between pulses
static volatile uint32_t phase = 0;
static volatile bool high = false;
static volatile int32_t emitted = 0;         // signed total since boot (diagnostics)
static volatile int dirSign = 1;
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

static void IRAM_ATTR onTick() {
  if (high) {
    digitalWrite(stepPin, LOW);
    high = false;
    return;
  }
  if (remaining <= 0) return;
  if (++phase >= interval) {
    phase = 0;
    digitalWrite(stepPin, HIGH);
    high = true;
    remaining = remaining - 1;
    emitted = emitted + dirSign;
  }
}

inline void begin(int step, int dir) {
  stepPin = step;
  dirPin = dir;
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  digitalWrite(stepPin, LOW);
  timer = timerBegin(TICK_HZ);                  // arduino-esp32 v3 API
  timerAttachInterrupt(timer, &onTick);
  timerAlarm(timer, 1, true, 0);
}

// steps: signed count for the next period; stepSign maps + (payout) to DIR.
// Returns false if the previous period had not finished (TIMING problem).
inline bool load(int32_t steps, uint32_t periodUs, int stepSign) {
  bool clean;
  portENTER_CRITICAL(&mux);
  clean = remaining == 0;
  int s = steps * stepSign;
  dirSign = steps >= 0 ? 1 : -1;
  digitalWrite(dirPin, s >= 0 ? HIGH : LOW);
  int32_t n = steps >= 0 ? steps : -steps;
  uint32_t ticks = periodUs * TICK_HZ / 1000000UL;
  interval = n > 0 ? (ticks / (uint32_t)n > 2 ? ticks / (uint32_t)n : 2) : 1;
  phase = 0;
  remaining = n;
  portEXIT_CRITICAL(&mux);
  return clean;
}

inline int32_t total() { return emitted; }

}  // namespace stepgen
