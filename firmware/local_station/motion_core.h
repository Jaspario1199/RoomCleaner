#pragma once
#include <stdint.h>
#include <math.h>
#include <stdlib.h>
#include <limits.h>
// Detached single-axis bench controller. No suspended four-axis coordination.
namespace roomcleaner {
enum class Mode { Off, Idle, Move, Settle, Release, Seek, Backoff, Refine, Fault };
enum class Fault { None, Encoder, Driver, Heartbeat, Timing, Tracking, HomeLimit, Switch };
struct Config {
 int stepsPerRev=3200, countsPerRev=4096, encoderSign=1;
 int homeDirection=-1, maxHomeSteps=6400, backoffSteps=256;
 int trackingTolerance=64; uint32_t trackingDwellUs=150000;
 uint32_t heartbeatTimeoutUs=500000, encoderTimeoutUs=30000;
 // Encoder counts and microseconds; detached-bench placeholders, not qualification.
 int arrivalTolerance=4;
 uint32_t arrivalDwellUs=50000, settleTimeoutUs=500000;
 uint32_t switchDebounceUs=10000, maxTickIntervalUs=10000;
 double acceleration=1000, maxSpeed=1000, seekSpeed=320, refineSpeed=80;
};
class MotionCore {
public:
 Config cfg; Mode mode=Mode::Off; Fault fault=Fault::None;
 int32_t position=0,target=0; bool homed=false, enabled=false;
 explicit MotionCore(Config c=Config()):cfg(c){}
 void heartbeat(uint32_t now){lastHeartbeat=now;}
 void encoder(int32_t ticks,bool valid,uint32_t now){encoderTicks=ticks;encoderValid=valid;lastEncoder=now;}
 bool arm(uint32_t now,bool driverOK){
  if(!validConfig() || mode!=Mode::Off || !driverOK || !encoderValid || now-lastEncoder>cfg.encoderTimeoutUs)return false;
  enabled=true;homed=false;position=0;origin=encoderTicks;mode=Mode::Idle;fault=Fault::None;
  lastTick=lastHeartbeat=now;phase=velocity=0;trackingBad=false;return true;
 }
 void disarm(){enabled=false;homed=false;mode=Mode::Off;fault=Fault::None;phase=velocity=0;}
 void hold(){if(mode!=Mode::Off&&mode!=Mode::Fault){if(active()||mode==Mode::Settle)homed=false;mode=Mode::Idle;target=position;phase=velocity=0;}}
 bool move(int32_t delta,double speed){
  if(mode!=Mode::Idle||!homed||delta==0||delta>32000||delta< -32000||!isfinite(speed)||speed<=0||speed>cfg.maxSpeed)return false;
  int64_t next=int64_t(position)+delta; if(next>INT32_MAX||next<INT32_MIN)return false;
  target=int32_t(next);requestedSpeed=speed;direction=delta>0?1:-1;phase=velocity=0;mode=Mode::Move;return true;
 }
 bool home(bool switchOpen){
  if(mode!=Mode::Idle)return false;
  homed=false;phase=velocity=0;homeSteps=0;filteredOpen=candidateOpen=switchOpen;edgeSince=lastTick;mode=switchOpen?Mode::Release:Mode::Seek;return true;
 }
 // Returns exactly one signed pulse to emit, or zero. No burst catch-up.
 int tick(uint32_t now,bool switchOpen,bool driverOK){
  if(!enabled||mode==Mode::Off||mode==Mode::Fault)return 0;
  if(!driverOK)return fail(Fault::Driver);
  if(!encoderValid||now-lastEncoder>cfg.encoderTimeoutUs)return fail(Fault::Encoder);
  if(now-lastHeartbeat>cfg.heartbeatTimeoutUs)return fail(Fault::Heartbeat);
  uint32_t elapsed=now-lastTick;lastTick=now;
  if(elapsed>cfg.maxTickIntervalUs && active())return fail(Fault::Timing);
  double expected=position*double(cfg.countsPerRev)/cfg.stepsPerRev;
  double actual=cfg.encoderSign*double(int64_t(encoderTicks)-origin);
  if(fabs(expected-actual)>cfg.trackingTolerance){
   if(!trackingBad){trackingBad=true;badSince=now;}
   else if(now-badSince>=cfg.trackingDwellUs)return fail(Fault::Tracking);
  }else trackingBad=false;
  if((mode==Mode::Move||mode==Mode::Settle) && switchOpen)return fail(Fault::Switch);
  if(switchOpen!=candidateOpen){candidateOpen=switchOpen;edgeSince=now;}
  if(now-edgeSince>=cfg.switchDebounceUs)filteredOpen=candidateOpen;
  switchOpen=filteredOpen;
  if(mode==Mode::Settle){
   if(fabs(expected-actual)<=cfg.arrivalTolerance){if(!arrivalGood){arrivalGood=true;arrivalSince=now;}else if(now-arrivalSince>=cfg.arrivalDwellUs){mode=Mode::Idle;return 0;}}else arrivalGood=false;
   if(now-settleSince>=cfg.settleTimeoutUs)return fail(Fault::Tracking);
   return 0;
  }
  if(mode==Mode::Release && !switchOpen){mode=Mode::Seek;homeSteps=0;phase=0;}
  else if(mode==Mode::Seek && switchOpen){mode=Mode::Backoff;homeSteps=0;phase=0;}
  else if(mode==Mode::Backoff && homeSteps>=cfg.backoffSteps){
   if(switchOpen)return fail(Fault::Switch);
   mode=Mode::Refine;homeSteps=0;phase=0;
  }else if(mode==Mode::Refine && switchOpen){
   position=target=0;origin=encoderTicks;homed=true;mode=Mode::Idle;phase=velocity=0;trackingBad=false;return 0;
  }
  if(!active())return 0;
  int sign;double speed;
  if(mode==Mode::Move){
   int64_t remaining=llabs(int64_t(target)-position);
   if(!remaining){mode=Mode::Idle;velocity=phase=0;return 0;}
   double wanted=fmin(requestedSpeed,sqrt(2*cfg.acceleration*remaining));
   double dv=cfg.acceleration*elapsed/1000000.;
   velocity=velocity<wanted?fmin(wanted,velocity+dv):fmax(wanted,velocity-dv);
   sign=direction;speed=velocity;
  }else{
   bool release=mode==Mode::Release||mode==Mode::Backoff;
   sign=release?-cfg.homeDirection:cfg.homeDirection;
   speed=mode==Mode::Refine?cfg.refineSpeed:cfg.seekSpeed;
   int limit=release?cfg.backoffSteps:cfg.maxHomeSteps;
   if(homeSteps>=limit)return fail(Fault::HomeLimit);
  }
  phase+=speed*elapsed/1000000.;
  if(phase>=2)return fail(Fault::Timing);
  if(phase<1)return 0;
  if((sign>0&&position==INT32_MAX)||(sign<0&&position==INT32_MIN))return fail(Fault::HomeLimit);
  phase-=1;position+=sign;
  if(mode==Mode::Move && position==target){mode=Mode::Settle;settleSince=now;arrivalGood=false;velocity=phase=0;}
  else if(mode!=Mode::Move)homeSteps++;
  return sign;
 }
private:
 bool filteredOpen=false,candidateOpen=false,arrivalGood=false;
 uint32_t edgeSince=0,settleSince=0,arrivalSince=0;
 uint32_t lastHeartbeat=0,lastEncoder=0,lastTick=0,badSince=0;
 int32_t encoderTicks=0;int64_t origin=0;bool encoderValid=false,trackingBad=false;
 int homeSteps=0,direction=1;double phase=0,velocity=0,requestedSpeed=0;
 // Keep intervals within the unambiguous half-range for wrapping timestamps.
 static bool validInterval(uint32_t us){return us>0&&us<0x80000000u;}
 bool validConfig()const{return validInterval(cfg.trackingDwellUs)&&validInterval(cfg.heartbeatTimeoutUs)&&validInterval(cfg.encoderTimeoutUs)&&validInterval(cfg.arrivalDwellUs)&&validInterval(cfg.settleTimeoutUs)&&validInterval(cfg.switchDebounceUs)&&validInterval(cfg.maxTickIntervalUs)&&cfg.arrivalDwellUs<cfg.settleTimeoutUs&&cfg.arrivalTolerance>0&&cfg.arrivalTolerance<=cfg.trackingTolerance&&cfg.stepsPerRev>0&&cfg.countsPerRev>0&&(cfg.encoderSign==1||cfg.encoderSign==-1)&&(cfg.homeDirection==1||cfg.homeDirection==-1)&&cfg.backoffSteps>0&&cfg.maxHomeSteps>cfg.backoffSteps&&cfg.trackingTolerance>0&&isfinite(cfg.acceleration)&&cfg.acceleration>0&&isfinite(cfg.maxSpeed)&&cfg.maxSpeed>0&&cfg.maxSpeed<=1000&&cfg.seekSpeed>0&&cfg.seekSpeed<=cfg.maxSpeed&&cfg.refineSpeed>0&&cfg.refineSpeed<=cfg.seekSpeed;}
 bool active()const{return mode==Mode::Move||mode==Mode::Release||mode==Mode::Seek||mode==Mode::Backoff||mode==Mode::Refine;}
 int fail(Fault f){fault=f;mode=Mode::Fault;homed=false;phase=velocity=0;return 0;}
};
}
