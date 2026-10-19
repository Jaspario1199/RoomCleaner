// AS5600 magnetic angle sensor on the spool: 12-bit absolute angle within ONE
// turn. Multi-turn counts are accumulated here by unwrapping successive
// readings; they restart at power-up (a new boot epoch -- the host must
// re-reference L0). Sampling must be fast enough that the spool turns less
// than half a revolution between reads (1 kHz vs <= 1.25 rev/s here).
#pragma once
#include <Arduino.h>
#include <Wire.h>

class AS5600 {
 public:
  static constexpr uint8_t ADDR = 0x36;
  static constexpr uint8_t REG_STATUS = 0x0B;     // MD bit5 magnet detected, ML bit4 too weak, MH bit3 too strong
  static constexpr uint8_t REG_RAW_ANGLE = 0x0C;  // 12-bit, 0x0C high nibble, 0x0D low byte

  // Returns true and updates counts when the reading is valid (magnet present,
  // field strength in range, bus OK). Invalid readings leave counts unchanged.
  bool sample(int32_t& counts) {
    int status = read(REG_STATUS, 1);
    int raw = read(REG_RAW_ANGLE, 2);
    bool ok = status >= 0 && raw >= 0 && (status & 0x20) && !(status & 0x18);
    if (!ok) {
      lastStatus = status;
      return false;
    }
    raw &= 0x0FFF;
    if (have) counts_ += unwrap(raw, prev);
    prev = raw;
    have = true;
    lastStatus = status;
    counts = counts_;
    return true;
  }
  int status() const { return lastStatus; }

  static int unwrap(int raw, int previous) { return (raw - previous + 6144) % 4096 - 2048; }

 private:
  int read(uint8_t reg, int n) {
    Wire.beginTransmission(ADDR);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return -1;
    if (Wire.requestFrom((int)ADDR, n) != n) return -1;
    int v = 0;
    while (Wire.available()) v = (v << 8) | Wire.read();
    return v;
  }
  int32_t counts_ = 0;
  int prev = 0;
  bool have = false;
  int lastStatus = -1;
};
