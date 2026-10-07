#include "../../firmware/local_station/motion_core.h"
#include <cassert>
#include <iostream>
using namespace roomcleaner;
struct Sim{MotionCore c;uint32_t t=0;int physical=0;Sim(Config cfg=Config()):c(cfg){sample();assert(c.arm(t,true));}void sample(){c.encoder(lround(physical*double(c.cfg.countsPerRev)/c.cfg.stepsPerRev),true,t);c.heartbeat(t);}void tick(bool open=false,bool follow=true){t+=1000;sample();int p=c.tick(t,open,true);if(follow)physical+=p;}void home(){assert(c.home(false));for(int i=0;i<20000&&!c.homed&&c.mode!=Mode::Fault;i++)tick(physical<=-20);assert(c.homed);}};
int main(){
 {Sim s;assert(s.c.home(false));s.tick(true);s.tick(false);assert(s.c.mode==Mode::Seek&&!s.c.homed);}
 {Sim s;assert(s.c.home(false));for(int i=0;i<10000&&s.c.mode!=Mode::Refine;i++)s.tick(s.physical<=-20);assert(s.c.mode==Mode::Refine);assert(s.physical>0);s.tick(true);s.tick(false);assert(!s.c.homed&&s.c.mode==Mode::Refine);for(int i=0;i<20;i++)s.tick(false);assert(!s.c.homed);}
 {Sim s;s.home();assert(s.c.move(10,100));for(int i=0;i<3000&&s.c.mode==Mode::Move;i++)s.tick(false,false);assert(s.c.mode==Mode::Settle);assert(!s.c.move(10,100));for(int i=0;i<600&&s.c.mode!=Mode::Fault;i++)s.tick(false,false);assert(s.c.fault==Fault::Tracking&&!s.c.homed);}
 {Sim s;s.home();assert(s.c.move(10,100));for(int i=0;i<3000&&s.c.mode!=Mode::Move&&s.c.mode!=Mode::Fault;i++)s.tick();for(int i=0;i<3000&&s.c.mode==Mode::Move;i++)s.tick();assert(s.c.mode==Mode::Settle);for(int i=0;i<60;i++)s.tick();assert(s.c.mode==Mode::Idle&&s.c.homed);}
 // Every timing setting rejects zero and ambiguous wraparound intervals at arm.
 {uint32_t Config::* timings[]={&Config::trackingDwellUs,&Config::heartbeatTimeoutUs,&Config::encoderTimeoutUs,&Config::arrivalDwellUs,&Config::settleTimeoutUs,&Config::switchDebounceUs,&Config::maxTickIntervalUs};
  for(auto field:timings)for(uint32_t value:{0u,0x80000000u,UINT32_MAX}){Config x;x.*field=value;MotionCore c(x);c.encoder(0,true,0);assert(!c.arm(0,true)&&!c.enabled&&c.mode==Mode::Off);}}
 {Config x;x.arrivalDwellUs=x.settleTimeoutUs;MotionCore c(x);c.encoder(0,true,0);assert(!c.arm(0,true));}
 {for(int tolerance:{0,-1,65}){Config x;x.arrivalTolerance=tolerance;MotionCore c(x);c.encoder(0,true,0);assert(!c.arm(0,true));}}
 // A configured debounce accepts an edge only after the full stable window.
 {Config x;x.switchDebounceUs=3000;Sim s(x);assert(s.c.home(false));s.tick(true);s.tick(true);s.tick(true);assert(s.c.mode==Mode::Seek);s.tick(true);assert(s.c.mode==Mode::Backoff);}
 // Configured arrival tolerance and dwell both govern MOVE completion.
 {Config x;x.arrivalTolerance=20;x.arrivalDwellUs=5000;Sim s(x);s.home();assert(s.c.move(10,100));while(s.c.mode==Mode::Move)s.tick(false,false);assert(s.c.mode==Mode::Settle);s.tick(false,false);for(int i=0;i<4;i++)s.tick(false,false);assert(s.c.mode==Mode::Settle);s.tick(false,false);assert(s.c.mode==Mode::Idle&&s.c.homed);}
 // A shorter configured settle timeout faults at its boundary when error persists.
 {Config x;x.arrivalDwellUs=5000;x.settleTimeoutUs=20000;Sim s(x);s.home();assert(s.c.move(10,100));while(s.c.mode==Mode::Move)s.tick(false,false);for(int i=0;i<19;i++)s.tick(false,false);assert(s.c.mode==Mode::Settle);s.tick(false,false);assert(s.c.fault==Fault::Tracking&&!s.c.homed);}
 // The configured active tick limit is inclusive; exceeding it faults.
 {Config x;x.maxTickIntervalUs=2000;Sim s(x);assert(s.c.home(false));s.t=2000;s.sample();s.c.tick(s.t,false,true);assert(s.c.mode==Mode::Seek);s.t+=2001;s.sample();s.c.tick(s.t,false,true);assert(s.c.fault==Fault::Timing);}
 std::cout<<"4 fresh debounce/arrival regression scenarios passed\n";
 std::cout<<"7 configuration regression groups passed\n";
}
