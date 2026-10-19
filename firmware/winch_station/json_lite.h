// json_lite.h - minimal, allocation-free JSON for the winch-station protocol.
//
// Decoder: parses ONE datagram (<= 512 bytes) into a flat Doc of at most
// kMaxEntries key/value pairs. Nested objects are flattened with dotted keys
// ("p.sid", "cap.ts"); the object itself is also stored as a Val::Obj entry so
// callers can test "is this a dict". Arrays are not supported (decode fails).
// Duplicate keys: the last one wins (find() scans backwards), like Python.
//
// Encoder: Writer streams into a caller-supplied fixed buffer, tracks commas
// itself and flags overflow instead of writing past the end.
//
// No exceptions, no RTTI, no heap. Portable C++17 (native g++ and ESP32 Arduino).
#pragma once
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace roomcleaner {
namespace winch {
namespace json {

constexpr size_t kMaxDatagram = 512;   // mirrors protocol.MAX_DATAGRAM
constexpr int kMaxEntries = 32;
constexpr int kKeyMax = 24;            // including NUL
constexpr int kStrMax = 24;            // including NUL
constexpr int kMaxDepth = 3;

// ---------------------------------------------------------------- value
struct Val {
  enum Type : uint8_t { Null, Bool, Int, Num, Str, Obj };
  Type type = Null;
  bool b = false;
  bool trunc = false;     // string did not fit; never compares equal to anything
  int64_t i = 0;
  double d = 0.0;
  char s[kStrMax] = {0};

  static Val ofInt(int64_t v) { Val x; x.type = Int; x.i = v; return x; }

  // Python truthiness (bool(x)).
  bool truthy() const {
    switch (type) {
      case Null: return false;
      case Bool: return b;
      case Int: return i != 0;
      case Num: return d != 0.0;
      case Str: return s[0] != 0 || trunc;
      case Obj: return true;
    }
    return false;
  }
  // int(x) for JSON numbers/bools: floats truncate toward zero. Strings are not
  // converted (Python would parse numeric strings); NaN/inf/out-of-range fail.
  bool toInt(int64_t& out) const {
    switch (type) {
      case Bool: out = b ? 1 : 0; return true;
      case Int: out = i; return true;
      case Num:
        if (!(d > -9.2e18 && d < 9.2e18)) return false;  // also rejects NaN
        out = static_cast<int64_t>(d);
        return true;
      default: return false;
    }
  }
  // float(x) for JSON numbers/bools.
  bool toDouble(double& out) const {
    switch (type) {
      case Bool: out = b ? 1.0 : 0.0; return true;
      case Int: out = static_cast<double>(i); return true;
      case Num: out = d; return true;
      default: return false;
    }
  }
  bool strEq(const char* lit) const { return type == Str && !trunc && strcmp(s, lit) == 0; }
  // Python "value == integer id" for ids that may arrive as int/float/bool.
  bool idEq(int64_t x) const {
    switch (type) {
      case Bool: return (b ? 1 : 0) == x;
      case Int: return i == x;
      case Num: return d == static_cast<double>(x);
      default: return false;
    }
  }
};

struct Doc {
  struct Entry {
    char key[kKeyMax];
    Val v;
  };
  Entry e[kMaxEntries];
  int n = 0;
  Val nullv;   // returned for absent keys (Python None)
  Val sink;    // scratch for entries whose key was too long to store

  const Val* find(const char* key) const {
    for (int k = n - 1; k >= 0; --k)
      if (strcmp(e[k].key, key) == 0) return &e[k].v;
    return nullptr;
  }
  const Val& get(const char* key) const {
    const Val* p = find(key);
    return p ? *p : nullv;
  }
};

// -------------------------------------------------------------- decoder
class Parser {
 public:
  Parser(const char* data, size_t len, Doc& doc) : p_(data), end_(data + len), doc_(doc) {}

  bool run() {
    doc_.n = 0;
    ws();
    char path[kKeyMax];
    path[0] = 0;
    if (p_ >= end_ || *p_ != '{') return false;
    if (!object(path, 0, true)) return false;
    ws();
    return p_ == end_;
  }

 private:
  const char* p_;
  const char* end_;
  Doc& doc_;

  void ws() {
    while (p_ < end_ && (*p_ == ' ' || *p_ == '\t' || *p_ == '\n' || *p_ == '\r')) ++p_;
  }

  static int hexv(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
  }

  // Parses a quoted string into buf (capacity cap, NUL terminated). Sets
  // *trunc when it did not fit. Rejects control and non-ASCII bytes.
  bool string(char* buf, int cap, bool* trunc) {
    if (p_ >= end_ || *p_ != '"') return false;
    ++p_;
    int n = 0;
    *trunc = false;
    auto put = [&](char c) {
      if (n < cap - 1) buf[n++] = c; else *trunc = true;
    };
    while (true) {
      if (p_ >= end_) return false;
      unsigned char c = static_cast<unsigned char>(*p_++);
      if (c == '"') break;
      if (c < 0x20 || c >= 0x80) return false;
      if (c != '\\') { put(static_cast<char>(c)); continue; }
      if (p_ >= end_) return false;
      char x = *p_++;
      switch (x) {
        case '"': put('"'); break;
        case '\\': put('\\'); break;
        case '/': put('/'); break;
        case 'b': put('\b'); break;
        case 'f': put('\f'); break;
        case 'n': put('\n'); break;
        case 'r': put('\r'); break;
        case 't': put('\t'); break;
        case 'u': {
          if (end_ - p_ < 4) return false;
          int cp = 0;
          for (int k = 0; k < 4; ++k) {
            int h = hexv(*p_++);
            if (h < 0) return false;
            cp = cp * 16 + h;
          }
          put(cp < 0x80 && cp != 0 ? static_cast<char>(cp) : '?');
          break;
        }
        default: return false;
      }
    }
    buf[n] = 0;
    return true;
  }

  bool number(Val& v) {
    const char* s = p_;
    const char* q = p_;
    bool isFloat = false;
    if (q < end_ && *q == '-') ++q;
    if (q >= end_) return false;
    if (*q == '0') ++q;
    else if (*q >= '1' && *q <= '9') { while (q < end_ && *q >= '0' && *q <= '9') ++q; }
    else return false;
    if (q < end_ && *q == '.') {
      isFloat = true; ++q;
      if (q >= end_ || *q < '0' || *q > '9') return false;
      while (q < end_ && *q >= '0' && *q <= '9') ++q;
    }
    if (q < end_ && (*q == 'e' || *q == 'E')) {
      isFloat = true; ++q;
      if (q < end_ && (*q == '+' || *q == '-')) ++q;
      if (q >= end_ || *q < '0' || *q > '9') return false;
      while (q < end_ && *q >= '0' && *q <= '9') ++q;
    }
    size_t len = static_cast<size_t>(q - s);
    if (len >= 40) return false;
    char tmp[40];
    memcpy(tmp, s, len);
    tmp[len] = 0;
    p_ = q;
    if (!isFloat) {
      // exact integer accumulate with overflow detection; fall back to double
      bool neg = tmp[0] == '-';
      const char* d = tmp + (neg ? 1 : 0);
      uint64_t acc = 0;
      bool over = false;
      for (; *d; ++d) {
        uint64_t digit = static_cast<uint64_t>(*d - '0');
        if (acc > (UINT64_MAX - digit) / 10) { over = true; break; }
        acc = acc * 10 + digit;
      }
      if (!over && acc <= (neg ? static_cast<uint64_t>(INT64_MAX) + 1 : static_cast<uint64_t>(INT64_MAX))) {
        v.type = Val::Int;
        v.i = neg ? static_cast<int64_t>(0 - acc) : static_cast<int64_t>(acc);
        return true;
      }
    }
    v.type = Val::Num;
    v.d = strtod(tmp, nullptr);
    return true;
  }

  bool literal(const char* lit) {
    size_t n = strlen(lit);
    if (static_cast<size_t>(end_ - p_) < n || memcmp(p_, lit, n) != 0) return false;
    p_ += n;
    return true;
  }

  // Parses an object whose '{' is at p_. `path` is the dotted prefix of its
  // keys (empty for the top level).
  bool object(const char* path, int depth, bool pathOk) {
    if (depth >= kMaxDepth) return false;
    ++p_;  // '{'
    size_t plen = strlen(path);
    ws();
    if (p_ < end_ && *p_ == '}') { ++p_; return true; }
    while (true) {
      ws();
      char key[kKeyMax];
      bool ktrunc = false;
      if (!string(key, kKeyMax, &ktrunc)) return false;
      ws();
      if (p_ >= end_ || *p_ != ':') return false;
      ++p_;
      ws();
      char full[kKeyMax];
      bool fullOk = pathOk && !ktrunc;
      if (fullOk) {
        size_t klen = strlen(key);
        size_t need = plen + (plen ? 1 : 0) + klen + 1;
        if (need > static_cast<size_t>(kKeyMax)) {
          fullOk = false;
        } else {
          size_t o = 0;
          if (plen) { memcpy(full, path, plen); o = plen; full[o++] = '.'; }
          memcpy(full + o, key, klen + 1);
        }
      }
      if (!fullOk) full[0] = 0;
      Val* slot;
      if (fullOk) {
        if (doc_.n >= kMaxEntries) return false;   // too many fields
        Doc::Entry& en = doc_.e[doc_.n++];
        memcpy(en.key, full, strlen(full) + 1);
        en.v = Val();
        slot = &en.v;
      } else {
        doc_.sink = Val();
        slot = &doc_.sink;
      }
      if (p_ >= end_) return false;
      char c = *p_;
      if (c == '{') {
        slot->type = Val::Obj;
        if (!object(full, depth + 1, fullOk)) return false;
      } else if (c == '"') {
        slot->type = Val::Str;
        if (!string(slot->s, kStrMax, &slot->trunc)) return false;
      } else if (c == 't') {
        if (!literal("true")) return false;
        slot->type = Val::Bool; slot->b = true;
      } else if (c == 'f') {
        if (!literal("false")) return false;
        slot->type = Val::Bool; slot->b = false;
      } else if (c == 'n') {
        if (!literal("null")) return false;
        slot->type = Val::Null;
      } else if (c == '-' || (c >= '0' && c <= '9')) {
        if (!number(*slot)) return false;
      } else {
        return false;   // arrays and anything else unsupported
      }
      ws();
      if (p_ >= end_) return false;
      if (*p_ == ',') { ++p_; continue; }
      if (*p_ == '}') { ++p_; return true; }
      return false;
    }
  }
};

// Parse one datagram. Returns false for anything malformed or unsupported.
inline bool decode(const char* data, size_t len, Doc& out) {
  if (len > kMaxDatagram) return false;
  Parser p(data, len, out);
  return p.run();
}

// -------------------------------------------------------------- encoder
class Writer {
 public:
  Writer(char* buf, size_t cap) : b_(buf), cap_(cap) { if (cap_) b_[0] = 0; }

  bool ok() const { return ok_; }
  size_t size() const { return n_; }

  void objBegin() { raw('{'); ++depth_; comma_[depth_ < kDepth ? depth_ : kDepth - 1] = false; }
  void objEnd() { raw('}'); if (depth_ > 0) --depth_; valueDone(); }

  void key(const char* k) {
    if (comma_[dIdx()]) raw(',');
    raw('"');
    text(k);
    raw('"');
    raw(':');
    comma_[dIdx()] = false;
  }
  void kvObjBegin(const char* k) { key(k); objBegin(); }
  void kvStr(const char* k, const char* v) { key(k); str(v); }
  void kvInt(const char* k, int64_t v) { key(k); integer(v); }
  void kvBool(const char* k, bool v) { key(k); text(v ? "true" : "false"); valueDone(); }
  void kvNull(const char* k) { key(k); text("null"); valueDone(); }
  void kvFixed(const char* k, double v, int decimals) { key(k); fixed(v, decimals); }
  void kvVal(const char* k, const Val& v) { key(k); val(v); }

  void str(const char* s) {
    raw('"');
    for (; *s; ++s) {
      char c = *s;
      if (c == '"' || c == '\\') { raw('\\'); raw(c); }
      else if (static_cast<unsigned char>(c) < 0x20 || static_cast<unsigned char>(c) >= 0x7f) {
        static const char hex[] = "0123456789abcdef";
        text("\\u00");
        raw(hex[(static_cast<unsigned char>(c) >> 4) & 15]);
        raw(hex[static_cast<unsigned char>(c) & 15]);
      } else raw(c);
    }
    raw('"');
    valueDone();
  }
  void integer(int64_t v) {
    char tmp[24];
    int k = 0;
    uint64_t u = v < 0 ? 0 - static_cast<uint64_t>(v) : static_cast<uint64_t>(v);
    do { tmp[k++] = static_cast<char>('0' + u % 10); u /= 10; } while (u);
    if (v < 0) raw('-');
    while (k) raw(tmp[--k]);
    valueDone();
  }
  // Fixed decimals via the C library (correctly rounded, like Python's round()+repr).
  void fixed(double v, int decimals) {
    char tmp[48];
    if (!isfinite(v)) { text("null"); valueDone(); return; }
    snprintf(tmp, sizeof tmp, "%.*f", decimals, v);
    text(tmp);
    valueDone();
  }
  // Shortest-safe double: 17 significant digits, always marked as a float.
  void number(double v) {
    char tmp[40];
    if (!isfinite(v)) { text("null"); valueDone(); return; }
    snprintf(tmp, sizeof tmp, "%.17g", v);
    text(tmp);
    if (!strpbrk(tmp, ".eE")) text(".0");
    valueDone();
  }
  void val(const Val& v) {
    switch (v.type) {
      case Val::Null: text("null"); valueDone(); break;
      case Val::Bool: text(v.b ? "true" : "false"); valueDone(); break;
      case Val::Int: integer(v.i); break;
      case Val::Num: number(v.d); break;
      case Val::Str: str(v.s); break;
      case Val::Obj: text("null"); valueDone(); break;
    }
  }

 private:
  static constexpr int kDepth = 4;
  char* b_;
  size_t cap_;
  size_t n_ = 0;
  bool ok_ = true;
  int depth_ = 0;
  bool comma_[kDepth] = {false, false, false, false};

  int dIdx() const { return depth_ < kDepth ? depth_ : kDepth - 1; }
  void valueDone() { comma_[dIdx()] = true; }
  void raw(char c) {
    if (n_ + 1 < cap_) { b_[n_++] = c; b_[n_] = 0; }
    else ok_ = false;
  }
  void text(const char* s) { for (; *s; ++s) raw(*s); }
};

}  // namespace json
}  // namespace winch
}  // namespace roomcleaner
