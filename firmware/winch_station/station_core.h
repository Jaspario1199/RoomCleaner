// station_core.h - winch-station control logic, portable C++17.
//
// Line-for-line port of roomcleaner/cdpr/station_core.py (the executable
// specification). The caller supplies time, encoder samples, switch level and
// received datagrams, and drains outgoing datagrams from the outbox; the core
// does no I/O. Behaviour is checked against recorded Python traces by
// tests/firmware/conformance_main.cpp.
//
// Constraints: no heap, no exceptions, no RTTI, no std::string/containers.
// Everything is fixed-size. Compiles with g++ -std=c++17 and the ESP32-C3
// Arduino toolchain. Floating point is IEEE double throughout, exactly like
// the Python reference (rounding = round-half-even via nearbyint, int() =
// truncation via cast).
#pragma once
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "json_lite.h"

namespace roomcleaner {
namespace winch {

constexpr int kMaxQueue = 32;
constexpr int64_t kMinSegUs = 5000;
constexpr int64_t kMaxSegUs = 1000000;
constexpr int64_t kMinLeadUs = 2000;
constexpr int64_t kTelemetryUs = 20000;
constexpr int kOutboxCap = 16;
constexpr int kSidMax = 16;        // incl. NUL
constexpr int kProtocolVersion = 1;

// Mirrors protocol.State / protocol.Fault.
struct State { enum : int { OFF = 0, IDLE = 1, RUN = 2, HOLD = 3, FAULT = 4 }; };
struct Fault {
  enum : int { NONE = 0, TRACKING = 1, ENCODER = 2, SWITCH = 3, LEASE = 4, UNDERRUN = 5, TIMING = 6, CONFIG = 7 };
  // protocol.Fault.REACTION: true = coordinated path hold first, false = stop pulses now.
  static bool holdReaction(int code) { return code == LEASE || code == UNDERRUN; }
};

// Same canonical string/CRC as protocol.params_hash (zlib crc32).
inline uint32_t crc32Update(uint32_t crc, const char* p, size_t n) {
  crc = ~crc;
  for (size_t i = 0; i < n; ++i) {
    crc ^= static_cast<uint8_t>(p[i]);
    for (int k = 0; k < 8; ++k) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
  }
  return ~crc;
}

// Cubic Hermite position/velocity at u in [0,1]; d_s in seconds.
// Operation order is identical to the Python reference.
inline void hermite(double p0, double p1, double v0, double v1, double d_s, double u,
                    double* x_out, double* v_out) {
  const double u2 = u * u, u3 = u * u * u;
  const double h00 = 2 * u3 - 3 * u2 + 1;
  const double h10 = u3 - 2 * u2 + u;
  const double h01 = -2 * u3 + 3 * u2;
  const double h11 = u3 - u2;
  *x_out = h00 * p0 + h10 * d_s * v0 + h01 * p1 + h11 * d_s * v1;
  const double dh00 = 6 * u2 - 6 * u;
  const double dh10 = 3 * u2 - 4 * u + 1;
  const double dh01 = -6 * u2 + 6 * u;
  const double dh11 = 3 * u2 - 2 * u;
  *v_out = (dh00 * p0 + dh01 * p1) / d_s + dh10 * v0 + dh11 * v1;
}

// One outgoing datagram, already encoded (includes "v":1, sid, boot, seq).
struct OutMsg {
  bool broadcast = false;      // true = "*" (peers + host), false = "host"
  uint16_t len = 0;
  char data[json::kMaxDatagram + 1];
};

class StationCore {
 public:
  struct Params {
    char sid[kSidMax] = {0};
    double usteps_per_rev = 0, step_sign = 0, max_rate_hz = 0, counts_per_rev = 0, enc_sign = 0,
           enc_max_age_us = 0, track_tol = 0, track_dwell_us = 0, lease_us = 0, sw_nc = 0,
           debounce_us = 0, hold_us = 0;
  };
  struct Seg {
    int64_t m = 0, i = 0, t0 = 0, d = 0;
    double p0 = 0, p1 = 0, v0 = 0, v1 = 0;
    bool last = false;
    int64_t ref = 0;
    double tau0 = 0;
  };
  struct Snapshot {          // reference capture / release record
    bool valid = false;
    int64_t ts = 0, pos = 0, enc = 0, tau = 0, m = 0;
    bool confirmed = false;
  };

  // disarm_key: per-boot random number the host must echo in "disarm" (firmware
  // passes esp_random()); default mirrors the Python reference for tests.
  explicit StationCore(uint32_t boot_id, int64_t period_us = 1000, int64_t disarm_key = -1)
      : boot_(boot_id), period_us_(period_us), dt_(period_us),
        disarmKey_((disarm_key >= 0 ? static_cast<uint64_t>(disarm_key)
                                    : (static_cast<uint64_t>(boot_id) * 2654435761ULL) >> 7) & 0xFFFFFFULL) {
    emitEvt("boot");
  }

  // ------------------------------------------------------- inbound
  // Decode one datagram (as protocol.decode: ASCII JSON object, "v" == 1, "t" a
  // string) and dispatch it. Returns false if it was dropped as invalid.
  bool handleDatagram(const char* data, size_t len, int64_t now, bool from_host = true) {
    if (!json::decode(data, len, scratch_)) return false;
    const json::Val& v = scratch_.get("v");
    double dv;
    if (!v.toDouble(dv) || dv != static_cast<double>(kProtocolVersion)) return false;
    if (scratch_.get("t").type != json::Val::Str) return false;
    handle(scratch_, now, from_host);
    return true;
  }

  void handle(const json::Doc& msg, int64_t now, bool from_host = true) {
    const json::Val& tv = msg.get("t");
    if (tv.strEq("hold")) {
      onHold(msg, now);
      if (from_host) { lastHost_ = now; hasLastHost_ = true; }
      return;
    }
    if (!from_host) return;
    lastHost_ = now;
    hasLastHost_ = true;
    if (tv.strEq("ping")) {
      return;
    } else if (tv.strEq("sync")) {
      json::Writer w = begin("sync_r");
      w.kvVal("h", msg.get("h"));
      w.kvInt("rx", now);
      w.kvInt("tx", now);
      finish(w, false, false);
    } else if (tv.strEq("cfg")) {
      onCfg(msg);
    } else if (tv.strEq("arm")) {
      onArm(msg, now);
    } else if (tv.strEq("disarm")) {
      double k;
      if (!msg.get("confirm").strEq("claw_supported")) {
        ack("disarm", false, "confirm");
      } else if (!msg.get("k").toDouble(k) || k != static_cast<double>(disarmKey_)) {
        ack("disarm", false, "key");
      } else if (state_ == State::RUN || state_ == State::HOLD) {
        ack("disarm", false, "moving");
      } else if (state_ == State::OFF) {
        ack("disarm", true, "");
      } else {
        state_ = State::OFF;
        qn_ = 0;
        ack("disarm", true, "");
      }
    } else if (tv.strEq("seg")) {
      onSeg(msg, now);
    } else if (tv.strEq("cancel")) {
      if (state_ == State::IDLE) {
        const json::Val& m = msg.get("m");
        int k = 0;
        for (int j = 0; j < qn_; ++j)
          if (!m.idEq(q_[j].m)) q_[k++] = q_[j];
        qn_ = k;
        ackKw("cancel", true, "", false, &m, nullptr);
      } else {
        ackKw("cancel", false, "not idle", false, &msg.get("m"), nullptr);
      }
    } else if (tv.strEq("clear")) {
      if (state_ == State::FAULT) {
        fault_ = Fault::NONE;
        state_ = State::IDLE;
        pos0_ = pos_;
        enc0_ = enc_;     // re-origin tracking
        hasTrackBad_ = false;
        capture_.valid = false;
        release_.valid = false;
        ack("clear", true, "");
      } else if (state_ == State::OFF && fault_ != Fault::NONE) {
        fault_ = Fault::NONE;        // disarmed with a latched fault: safe to clear
        hasTrackBad_ = false;
        capture_.valid = false;
        release_.valid = false;
        ack("clear", true, "");
      } else if ((state_ == State::IDLE || state_ == State::OFF) && fault_ == Fault::NONE) {
        ack("clear", true, "");      // idempotent
      } else {
        ack("clear", false, "moving");
      }
    }
  }

  // Advance one control period. Returns signed steps to emit evenly over the
  // next period. enc_present=false models Python's enc_counts=None.
  int update(int64_t now, int64_t enc_counts, bool enc_valid, bool sw_active, bool enc_present = true) {
    if (enc_valid && enc_present) {
      enc_ = enc_counts;
      encValid_ = true;
      encT_ = now;
    } else if (!enc_valid) {
      encValid_ = false;
    }
    const bool edge = debounce(sw_active, now);
    // path time integrates the measured elapsed time (clamped to 3 periods)
    if (hasLastUpdate_) {
      int64_t e = now - lastUpdate_;
      if (e < 0) e = 0;
      if (e > 3 * period_us_) e = 3 * period_us_;
      dt_ = e;
    } else {
      dt_ = period_us_;
    }
    if (hasLastUpdate_ && armed() && static_cast<double>(now - lastUpdate_) > 3.0 * static_cast<double>(period_us_))
      setFault(Fault::TIMING, now);
    lastUpdate_ = now;
    hasLastUpdate_ = true;
    if (!hasParams_) {
      telemetry(now);
      return 0;
    }
    if (armed()) {
      if (!encoderFresh(now)) setFault(Fault::ENCODER, now);
      if (hasLastHost_ && static_cast<double>(now - lastHost_) > p_.lease_us) setFault(Fault::LEASE, now);
    }
    int steps = 0;
    if (state_ == State::IDLE && qn_ > 0 && now >= q_[0].t0) {
      motion_ = q_[0].m;
      motionT0_ = q_[0].t0;
      tau_ = static_cast<double>(now - motionT0_);
      rate_ = 1.0;
      hasHoldTau_ = false;
      holding_ = false;
      postCapture_ = false;
      capture_.valid = false;
      release_.valid = false;
      state_ = State::RUN;
    }
    if (state_ == State::RUN || state_ == State::HOLD) steps = run(now);
    checkSwitch(now, edge);
    checkTracking(now);
    telemetry(now);
    return steps;
  }

  // ------------------------------------------------------ outbox
  int outboxCount() const { return obCount_; }
  const OutMsg* outboxFront() const { return obCount_ ? &outbox_[obHead_] : nullptr; }
  void outboxPop() {
    if (obCount_) { obHead_ = (obHead_ + 1) % kOutboxCap; --obCount_; }
  }
  // Copies out and removes the oldest message; false if empty.
  bool drain(OutMsg& out) {
    if (!obCount_) return false;
    out = outbox_[obHead_];
    outboxPop();
    return true;
  }
  uint32_t droppedMessages() const { return dropped_; }   // outbox full / datagram too large

  // ------------------------------------------------------ inspection
  bool armed() const { return state_ != State::OFF; }
  int state() const { return state_; }
  int fault() const { return fault_; }
  int64_t pos() const { return pos_; }
  int queueDepth() const { return qn_; }
  uint32_t paramsHash() const { return hash_; }
  uint64_t disarmKey() const { return disarmKey_; }
  // Accepted host configuration (nullptr until a valid cfg has been accepted).
  bool configured() const { return hasParams_; }
  const Params* params() const { return hasParams_ ? &p_ : nullptr; }

 private:
  struct Parked {
    bool used = false;
    bool bad = false;       // numeric fields failed to parse: nack "malformed" on append
    Seg s;
  };

  // ---- state (names follow the Python attributes)
  uint32_t boot_;
  int64_t period_us_;
  int64_t dt_;
  uint64_t disarmKey_;
  Params p_;
  bool hasParams_ = false;
  uint32_t hash_ = 0;
  int state_ = State::OFF;
  int fault_ = Fault::NONE;
  int64_t pos_ = 0, pos0_ = 0, enc_ = 0, enc0_ = 0;
  bool encValid_ = false;
  int64_t encT_ = -1000000000000000000LL;
  Seg q_[kMaxQueue];
  int qn_ = 0;
  Parked pend_[kMaxQueue];
  int64_t pendM_ = 0;
  bool hasPendM_ = false;
  int64_t motion_ = -1;
  int64_t laM_ = -1, laI_ = -1;      // last_appended
  int64_t motionT0_ = 0;
  double tau_ = 0.0, rate_ = 0.0;
  double holdTau_ = 0.0;
  bool hasHoldTau_ = false;
  bool holding_ = false;
  int64_t holdT_ = 0;
  bool postCapture_ = false;
  int64_t lastHost_ = 0;
  bool hasLastHost_ = false;
  bool swRaw_ = false, swCand_ = false, sw_ = false, swInit_ = false;
  int64_t swSince_ = 0;
  int64_t trackBadSince_ = 0;
  bool hasTrackBad_ = false;
  double terr_ = 0.0;
  Snapshot capture_, release_;
  int64_t seq_ = 0, evt_ = 0;
  int64_t nextTel_ = 0;
  int64_t lastUpdate_ = 0;
  bool hasLastUpdate_ = false;

  OutMsg outbox_[kOutboxCap];
  OutMsg scratchOut_;
  int obHead_ = 0, obCount_ = 0;
  uint32_t dropped_ = 0;
  json::Doc scratch_;

  // ------------------------------------------------------ emit helpers
  json::Writer begin(const char* type) {
    OutMsg& slot = obCount_ < kOutboxCap ? outbox_[(obHead_ + obCount_) % kOutboxCap] : scratchOut_;
    json::Writer w(slot.data, sizeof slot.data);
    w.objBegin();
    w.kvStr("t", type);
    return w;
  }
  // Stamps sid/boot/seq(/e)/v and commits the message to the outbox.
  void finish(json::Writer& w, bool broadcast, bool isEvt) {
    ++seq_;
    if (isEvt) ++evt_;
    w.kvStr("sid", hasParams_ ? p_.sid : "?");
    w.kvInt("boot", boot_);
    w.kvInt("seq", seq_);
    if (isEvt) w.kvInt("e", evt_);
    w.kvInt("v", kProtocolVersion);
    w.objEnd();
    if (obCount_ >= kOutboxCap || !w.ok()) { ++dropped_; return; }
    OutMsg& slot = outbox_[(obHead_ + obCount_) % kOutboxCap];
    slot.broadcast = broadcast;
    slot.len = static_cast<uint16_t>(w.size());
    ++obCount_;
  }
  void emitEvt(const char* kind) {
    json::Writer w = begin("evt");
    w.kvStr("k", kind);
    finish(w, false, true);
  }
  void emitEvtMotion(const char* kind, int64_t m, int64_t pos, int64_t tau) {
    json::Writer w = begin("evt");
    w.kvStr("k", kind);
    w.kvInt("m", m);
    w.kvInt("pos", pos);
    w.kvInt("tau", tau);
    finish(w, false, true);
  }
  void emitHoldBroadcast() {
    json::Writer w = begin("hold");
    w.kvInt("m", motion_);
    w.kvInt("tau", static_cast<int64_t>(tau_));
    finish(w, true, false);
  }
  void emitSnapshotEvt(const char* kind, const Snapshot& s, bool withConfirmed) {
    json::Writer w = begin("evt");
    w.kvStr("k", kind);
    w.kvInt("ts", s.ts);
    w.kvInt("pos", s.pos);
    w.kvInt("enc", s.enc);
    w.kvInt("tau", s.tau);
    w.kvInt("m", s.m);
    if (withConfirmed) w.kvBool("confirmed", s.confirmed);
    finish(w, false, true);
  }
  void ack(const char* re, bool ok, const char* why) { ackKw(re, ok, why, false, nullptr, nullptr); }
  void ackKw(const char* re, bool ok, const char* why, bool withHash, const json::Val* m, const json::Val* i) {
    json::Writer w = begin("ack");
    w.kvStr("re", re);
    w.kvBool("ok", ok);
    w.kvStr("why", why);
    if (withHash) w.kvInt("hash", hash_);
    if (m) w.kvVal("m", *m);
    if (i) w.kvVal("i", *i);
    finish(w, false, false);
  }
  void segAck(bool ok, const char* why, const json::Val& m, const json::Val& i) {
    ackKw("seg", ok, why, false, &m, &i);
  }

  // ------------------------------------------------------ cfg / arm
  static const json::Val* paramVal(const json::Doc& d, const char* name) {
    char key[40];
    key[0] = 'p'; key[1] = '.';
    size_t n = strlen(name);
    memcpy(key + 2, name, n + 1);
    return d.find(key);
  }
  // protocol.REQUIRED_PARAMS in canonical order.
  static constexpr const char* kReq[13] = {"sid", "usteps_per_rev", "step_sign", "max_rate_hz", "counts_per_rev",
                                           "enc_sign", "enc_max_age_us", "track_tol", "track_dwell_us",
                                           "lease_us", "sw_nc", "debounce_us", "hold_us"};
  static const double* numField(const Params& p, int idx) {
    switch (idx) {
      case 1: return &p.usteps_per_rev;
      case 2: return &p.step_sign;
      case 3: return &p.max_rate_hz;
      case 4: return &p.counts_per_rev;
      case 5: return &p.enc_sign;
      case 6: return &p.enc_max_age_us;
      case 7: return &p.track_tol;
      case 8: return &p.track_dwell_us;
      case 9: return &p.lease_us;
      case 10: return &p.sw_nc;
      case 11: return &p.debounce_us;
      case 12: return &p.hold_us;
    }
    return nullptr;
  }
  // protocol._canon: bool -> "1"/"0"; integral float/int -> integer digits;
  // other floats -> "%.6f".
  static void canon(double v, char* out, size_t cap) {
    if (v == 0.0) snprintf(out, cap, "0");                          // also -0.0
    else if (v == floor(v)) snprintf(out, cap, "%.0f", v);
    else snprintf(out, cap, "%.6f", v);
  }

  uint32_t computeHash(const Params& p) const {
    uint32_t crc = 0;
    char buf[400];
    for (int k = 0; k < 13; ++k) {
      if (k) crc = crc32Update(crc, ";", 1);
      crc = crc32Update(crc, kReq[k], strlen(kReq[k]));
      crc = crc32Update(crc, "=", 1);
      if (k == 0) {
        crc = crc32Update(crc, p.sid, strlen(p.sid));
      } else {
        canon(*numField(p, k), buf, sizeof buf);
        crc = crc32Update(crc, buf, strlen(buf));
      }
    }
    return crc;
  }

  void onCfg(const json::Doc& msg) {
    const json::Val* pv = msg.find("p");
    const bool isDict = pv && pv->type == json::Val::Obj;
    if (state_ != State::OFF) {
      bool same = isDict && hasParams_;
      if (same) {
        for (int k = 0; k < 13 && same; ++k) {
          const json::Val* v = paramVal(msg, kReq[k]);
          if (!v) { same = false; break; }
          if (k == 0) {
            same = v->strEq(p_.sid);
          } else {
            double d;
            same = v->toDouble(d) && d == *numField(p_, k);
          }
        }
      }
      if (same) ackKw("cfg", true, "", true, nullptr, nullptr);   // same config re-sent: idempotent
      else ack("cfg", false, "armed");
      return;
    }
    bool incomplete = !isDict;
    if (!incomplete) {
      for (int k = 0; k < 13; ++k) {
        const json::Val* v = paramVal(msg, kReq[k]);
        if (!v || v->type == json::Val::Null) { incomplete = true; break; }
      }
    }
    if (incomplete) { ack("cfg", false, "incomplete"); return; }
    // Convert; a non-numeric value where Python would compare numbers is "invalid"
    // (Python would raise TypeError there).
    Params np;
    bool typed = true;
    {
      const json::Val* sv = paramVal(msg, "sid");
      if (sv->type != json::Val::Str || sv->trunc || strlen(sv->s) >= static_cast<size_t>(kSidMax)) typed = false;
      else memcpy(np.sid, sv->s, strlen(sv->s) + 1);
    }
    double* fields[13] = {nullptr, &np.usteps_per_rev, &np.step_sign, &np.max_rate_hz, &np.counts_per_rev,
                          &np.enc_sign, &np.enc_max_age_us, &np.track_tol, &np.track_dwell_us, &np.lease_us,
                          &np.sw_nc, &np.debounce_us, &np.hold_us};
    for (int k = 1; k < 13 && typed; ++k) {
      if (!paramVal(msg, kReq[k])->toDouble(*fields[k])) typed = false;
    }
    const bool ok = typed && np.usteps_per_rev > 0 && np.counts_per_rev > 0 && np.max_rate_hz > 0 &&
                    (np.step_sign == 1 || np.step_sign == -1) && (np.enc_sign == 1 || np.enc_sign == -1) &&
                    np.track_tol > 0 && np.lease_us > 0 && np.hold_us > 0 && np.debounce_us >= 0 &&
                    np.enc_max_age_us > 0 && np.track_dwell_us > 0;
    if (!ok) { ack("cfg", false, "invalid"); return; }
    p_ = np;
    hasParams_ = true;
    hash_ = computeHash(p_);
    ackKw("cfg", true, "", true, nullptr, nullptr);
  }

  bool encoderFresh(int64_t now) const {
    return encValid_ && hasParams_ && static_cast<double>(now - encT_) <= p_.enc_max_age_us;
  }

  void onArm(const json::Doc& msg, int64_t now) {
    const char* why = "";
    if (!hasParams_) {
      why = "no config";
    } else if (state_ == State::IDLE && fault_ == Fault::NONE) {
      ackKw("arm", true, "", true, nullptr, nullptr);      // idempotent (lost ack retried)
      return;
    } else if (state_ != State::OFF) {
      why = "busy";
    } else if (fault_ != Fault::NONE) {
      why = "fault latched";
    } else if (!encoderFresh(now)) {
      why = "encoder";
    } else if (sw_ && !msg.get("sw_ok").truthy()) {
      why = "switch active";
    }
    if (why[0]) { ack("arm", false, why); return; }
    state_ = State::IDLE;
    pos0_ = pos_;
    enc0_ = enc_;
    hasTrackBad_ = false;
    ackKw("arm", true, "", true, nullptr, nullptr);
  }

  // ------------------------------------------------------ segments
  // Mirrors the try/except in _append_seg: any missing/non-numeric field -> false.
  static bool parseSeg(const json::Doc& msg, Seg& s) {
    int64_t t0, d, ref = 0;
    double p0, p1, v0, v1;
    if (!msg.get("t0").toInt(t0) || !msg.get("d").toInt(d)) return false;
    if (!msg.get("p0").toDouble(p0) || !msg.get("p1").toDouble(p1) || !msg.get("v0").toDouble(v0) ||
        !msg.get("v1").toDouble(v1))
      return false;
    const json::Val* rv = msg.find("ref");
    if (rv && !rv->toInt(ref)) return false;
    s.t0 = t0; s.d = d; s.p0 = p0; s.p1 = p1; s.v0 = v0; s.v1 = v1;
    s.last = msg.get("last").truthy();
    s.ref = ref;
    return true;
  }

  int pendFind(int64_t i) const {
    for (int k = 0; k < kMaxQueue; ++k)
      if (pend_[k].used && pend_[k].s.i == i) return k;
    return -1;
  }
  int pendCount() const {
    int n = 0;
    for (int k = 0; k < kMaxQueue; ++k) n += pend_[k].used ? 1 : 0;
    return n;
  }

  void onSeg(const json::Doc& msg, int64_t now) {
    const json::Val& mv = msg.get("m");
    const json::Val& iv = msg.get("i");
    if (iv.type != json::Val::Int || mv.type != json::Val::Int) { segAck(false, "malformed", mv, iv); return; }
    const int64_t m = mv.i, i = iv.i;
    int64_t expected = (laM_ == m) ? laI_ + 1 : 0;
    if (i < expected) {                                    // retransmitted duplicate
      segAck(true, "", mv, iv);
      return;
    }
    if (i > expected) {                                    // arrived early: park it
      if (!hasPendM_ || pendM_ != m) {
        for (int k = 0; k < kMaxQueue; ++k) pend_[k].used = false;
        pendM_ = m;
        hasPendM_ = true;
      }
      if (pendCount() >= kMaxQueue) { segAck(false, "full", mv, iv); return; }
      int slot = pendFind(i);
      if (slot < 0) {
        for (int k = 0; k < kMaxQueue; ++k)
          if (!pend_[k].used) { slot = k; break; }
      }
      Parked& pk = pend_[slot];
      pk.used = true;
      pk.s = Seg();
      pk.s.m = m;
      pk.s.i = i;
      pk.bad = !parseSeg(msg, pk.s);
      segAck(true, "", mv, iv);
      return;
    }
    Seg s;
    s.m = m;
    s.i = i;
    const bool bad = !parseSeg(msg, s);
    appendSeg(s, bad, now);
    while (hasPendM_ && pendM_ == m && laM_ == m && laI_ == expected) {
      const int k = pendFind(expected + 1);
      if (k < 0) break;
      ++expected;
      Parked nxt = pend_[k];
      pend_[k].used = false;
      appendSeg(nxt.s, nxt.bad, now);
    }
  }

  void appendSeg(const Seg& s, bool bad, int64_t now) {
    const json::Val mv = json::Val::ofInt(s.m), iv = json::Val::ofInt(s.i);
    auto nack = [&](const char* why) { segAck(false, why, mv, iv); };
    if (bad) return nack("malformed");
    if (!hasParams_ || !armed()) return nack("not armed");
    if (fault_ != Fault::NONE) return nack("fault");
    if (holding_ || state_ == State::HOLD) return nack("holding");
    if (!(s.d >= kMinSegUs && s.d <= kMaxSegUs) || !(s.ref == 0 || s.ref == 1 || s.ref == 2)) return nack("range");
    if (!(isfinite(s.p0) && isfinite(s.p1) && isfinite(s.v0) && isfinite(s.v1))) return nack("range");
    if (qn_ >= kMaxQueue) return nack("full");
    const double vmax = p_.max_rate_hz * 1.02;
    static const double us[5] = {0.0, 0.25, 0.5, 0.75, 1.0};
    for (int k = 0; k < 5; ++k) {
      double x, v;
      hermite(s.p0, s.p1, s.v0, s.v1, static_cast<double>(s.d) / 1e6, us[k], &x, &v);
      if (fabs(v) > vmax) return nack("speed");
    }
    const Seg* tail = qn_ ? &q_[qn_ - 1] : nullptr;
    if (!tail && state_ == State::RUN && motion_ == s.m) return nack("starved");  // queue drained mid-motion
    double tau0;
    if (!tail || tail->m != s.m) {
      // first segment of a new motion
      if (state_ != State::IDLE || s.i != 0) return nack("sequence");
      if (fabs(s.p0 - static_cast<double>(pos_)) > 0.5) return nack("position");
      if (s.t0 < now + kMinLeadUs) return nack("late");
      tau0 = 0.0;
    } else {
      if (tail->last) return nack("after last");
      if (s.i != tail->i + 1 || s.t0 != tail->t0 + tail->d) return nack("sequence");
      if (fabs(s.p0 - tail->p1) > 1e-6 || fabs(s.v0 - tail->v1) > 1e-6) return nack("continuity");
      if (s.t0 + s.d < now) return nack("late");
      tau0 = tail->tau0 + static_cast<double>(tail->d);
    }
    q_[qn_] = s;
    q_[qn_].tau0 = tau0;
    ++qn_;
    laM_ = s.m;
    laI_ = s.i;
    segAck(true, "", mv, iv);
  }

  // ------------------------------------------------------ hold / faults
  void onHold(const json::Doc& msg, int64_t now) {
    (void)now;
    const json::Val& m = msg.get("m");
    if ((state_ != State::RUN && state_ != State::IDLE) || m.type == json::Val::Null) return;
    if (state_ == State::IDLE) {
      // not started yet: drop the queued motion so it never starts
      if (qn_ > 0 && m.idEq(q_[0].m)) {
        qn_ = 0;
        json::Writer w = begin("evt");
        w.kvStr("k", "hold");
        w.kvVal("m", m);
        w.kvInt("pos", pos_);
        w.kvInt("tau", 0);
        finish(w, false, true);
      }
      return;
    }
    if (!m.idEq(motion_) || holding_) return;
    double tau = tau_;
    const json::Val* tv = msg.find("tau");
    if (tv && !tv->toDouble(tau)) return;     // Python would raise TypeError
    if (!hasHoldTau_ || tau < holdTau_) { holdTau_ = tau; hasHoldTau_ = true; }
  }

  void beginHold(int64_t now, bool broadcast) {
    if (state_ != State::RUN || holding_) return;
    holding_ = true;
    holdT_ = now;
    state_ = State::HOLD;
    if (broadcast) emitHoldBroadcast();
  }

  void setFault(int code, int64_t now) {
    if (fault_ != Fault::NONE) return;
    fault_ = code;
    const bool running = state_ == State::RUN || state_ == State::HOLD;
    {
      json::Writer w = begin("evt");
      w.kvStr("k", "fault");
      w.kvInt("f", code);
      w.kvInt("pos", pos_);
      w.kvInt("m", motion_);
      w.kvInt("tau", static_cast<int64_t>(tau_));
      finish(w, false, true);
    }
    if (Fault::holdReaction(code) && running) {
      beginHold(now, true);
      return;
    }
    if (running) emitHoldBroadcast();   // stop pulses now, ask the others to stop at this path point
    if (state_ != State::OFF) state_ = State::FAULT;
    qn_ = 0;
    rate_ = 0.0;
    holding_ = false;
  }

  // ------------------------------------------------------ inputs
  bool debounce(bool raw, int64_t now) {
    if (!swInit_) {
      swRaw_ = swCand_ = sw_ = raw;
      swSince_ = now;
      swInit_ = true;
      return false;
    }
    const bool edge = raw != swRaw_;
    swRaw_ = raw;
    if (raw != swCand_) {
      swCand_ = raw;
      swSince_ = now;
    }
    const double deb = hasParams_ ? p_.debounce_us : 10000.0;
    if (sw_ != swCand_ && static_cast<double>(now - swSince_) >= deb) sw_ = swCand_;
    return edge;
  }

  // ------------------------------------------------------ run loop
  const Seg* segmentAt(double tau) const {
    for (int k = 0; k < qn_; ++k)
      if (tau < q_[k].tau0 + static_cast<double>(q_[k].d)) return &q_[k];
    return nullptr;
  }
  const Seg& segmentOrTail(double tau) const {
    const Seg* s = segmentAt(tau);
    return s ? *s : q_[qn_ - 1];
  }
  int maxSteps() const {
    return static_cast<int>(ceil(p_.max_rate_hz * static_cast<double>(period_us_) / 1e6));
  }

  int run(int64_t now) {
    if (qn_ == 0) return 0;     // cannot happen in RUN/HOLD; guard instead of UB
    const double dt = static_cast<double>(dt_);
    if (!holding_ && hasHoldTau_ && tau_ >= holdTau_) beginHold(now, false);
    if (holding_) {
      const double r = 1.0 - static_cast<double>(now - holdT_) / p_.hold_us;
      rate_ = r > 0.0 ? r : 0.0;
    }
    if (state_ == State::RUN) {
      const double end0 = q_[qn_ - 1].tau0 + static_cast<double>(q_[qn_ - 1].d);
      if (!q_[qn_ - 1].last && end0 - tau_ < p_.hold_us / 2 + 2 * dt) {
        setFault(Fault::UNDERRUN, now);
        if (state_ != State::HOLD) return 0;
      }
    }
    if (qn_ == 0) return 0;
    double tauNext = tau_ + rate_ * dt;
    const double end = q_[qn_ - 1].tau0 + static_cast<double>(q_[qn_ - 1].d);
    bool finished = false;
    if (tauNext >= end) {
      tauNext = end;
      finished = true;
    }
    tau_ = tauNext;
    const Seg& seg = segmentOrTail(tau_ - 1e-9);
    double u = (tau_ - seg.tau0) / static_cast<double>(seg.d);
    u = (0.0 > u) ? 0.0 : u;            // max(u, 0.0)
    u = (1.0 < u) ? 1.0 : u;            // min(u, 1.0)
    double x, vdummy;
    hermite(seg.p0, seg.p1, seg.v0, seg.v1, static_cast<double>(seg.d) / 1e6, u, &x, &vdummy);
    int64_t xr;
    if (x >= 9.0e18) xr = INT64_MAX / 2;
    else if (x <= -9.0e18) xr = -(INT64_MAX / 2);
    else xr = static_cast<int64_t>(nearbyint(x));       // Python round(): half to even
    int64_t want = xr - pos_;
    if (postCapture_ && want < 0) want = 0;
    const int64_t lim = maxSteps();
    int64_t steps = want < lim ? want : lim;
    steps = steps > -lim ? steps : -lim;
    pos_ += steps;
    while (qn_ > 1 && q_[0].tau0 + static_cast<double>(q_[0].d) <= tau_) {
      for (int k = 1; k < qn_; ++k) q_[k - 1] = q_[k];
      --qn_;
    }
    const bool stopped = holding_ && rate_ <= 0.0;
    if (finished || stopped) {
      const int64_t m = motion_;
      qn_ = 0;
      holding_ = false;
      hasHoldTau_ = false;
      rate_ = 0.0;
      state_ = (fault_ != Fault::NONE) ? State::FAULT : State::IDLE;
      emitEvtMotion(finished && !stopped ? "done" : "hold", m, pos_, static_cast<int64_t>(tau_));
    }
    return static_cast<int>(steps);
  }

  int activeRef() const {
    if ((state_ == State::RUN || state_ == State::HOLD) && qn_ > 0) return static_cast<int>(segmentOrTail(tau_ - 1e-9).ref);
    return 0;
  }

  Snapshot snapshot(int64_t now) const {
    Snapshot s;
    s.valid = true;
    s.ts = now;
    s.pos = pos_;
    s.enc = enc_;
    s.tau = static_cast<int64_t>(tau_);
    s.m = motion_;
    s.confirmed = false;
    return s;
  }

  void checkSwitch(int64_t now, bool edge) {
    const int ref = activeRef();
    if (edge && swRaw_ && ref == 1 && !capture_.valid) capture_ = snapshot(now);
    if (capture_.valid && !capture_.confirmed && !swRaw_ && !sw_)
      capture_.valid = false;       // contact shorter than the debounce: a glitch, not the bead
    if (sw_ && ref == 1) {
      if (!capture_.valid) capture_ = snapshot(now);      // debounced without a seen edge (started active)
      if (!capture_.confirmed) {
        capture_.confirmed = true;
        postCapture_ = true;
        emitSnapshotEvt("capture", capture_, true);
        beginHold(now, true);
      }
      return;
    }
    if (ref == 2) {
      if (!sw_ && !release_.valid) {
        release_ = snapshot(now);
        emitSnapshotEvt("release", release_, false);
      }
      return;
    }
    if (sw_ && armed() && !postCapture_) setFault(Fault::SWITCH, now);
  }

  void checkTracking(int64_t now) {
    if (!armed() || !encValid_ || !hasParams_) return;
    const double expected = static_cast<double>(pos_ - pos0_) * p_.counts_per_rev / p_.usteps_per_rev;
    const double measured = p_.enc_sign * static_cast<double>(enc_ - enc0_);
    terr_ = measured - expected;
    if (fabs(terr_) > p_.track_tol) {
      if (!hasTrackBad_) {
        trackBadSince_ = now;
        hasTrackBad_ = true;
      } else if (static_cast<double>(now - trackBadSince_) >= p_.track_dwell_us) {
        setFault(Fault::TRACKING, now);
      }
    } else {
      hasTrackBad_ = false;
    }
  }

  void telemetry(int64_t now) {
    if (now < nextTel_) return;
    nextTel_ = now + kTelemetryUs;
    json::Writer w = begin("tel");
    w.kvInt("now", now);
    w.kvInt("st", state_);
    w.kvInt("flt", fault_);
    w.kvInt("pos", pos_);
    w.kvInt("enc", enc_);
    w.kvBool("encv", encoderFresh(now));
    w.kvBool("sw", sw_);
    w.kvBool("swr", swRaw_);
    w.kvInt("m", motion_);
    w.kvInt("i", qn_ ? q_[0].i : -1);
    w.kvInt("tau", static_cast<int64_t>(tau_));
    w.kvInt("buf", qn_);
    w.kvFixed("terr", terr_, 1);
    if (capture_.valid) {
      w.kvObjBegin("cap");
      w.kvInt("ts", capture_.ts);
      w.kvInt("pos", capture_.pos);
      w.kvInt("enc", capture_.enc);
      w.kvInt("tau", capture_.tau);
      w.kvInt("m", capture_.m);
      w.kvBool("confirmed", capture_.confirmed);
      w.objEnd();
    } else {
      w.kvNull("cap");
    }
    w.kvFixed("rate", rate_, 4);
    w.kvInt("hash", hash_);
    w.kvBool("en", armed());
    w.kvInt("dk", static_cast<int64_t>(disarmKey_));
    finish(w, false, false);
  }
};

}  // namespace winch
}  // namespace roomcleaner
