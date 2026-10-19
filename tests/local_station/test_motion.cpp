#include "../../firmware/local_station/motion_core.h"
#include <cassert>
#include <iostream>
using namespace roomcleaner;
struct Sim {
 MotionCore c; uint32_t t=0; int physical=0;
 Sim(){sample(); assert(c.arm(t,true));}
 void sample(){c.encoder(lround(physical*4096./3200),true,t);c.heartbeat(t);}
 int tick(bool open=false,bool follow=true){t+=1000;sample();int p=c.tick(t,open,true);if(follow)physical+=p;return p;}
 void home(){assert(c.home(false));for(int i=0;i<20000&&!c.homed&&c.mode!=Mode::Fault;i++)tick(physical<=-20);assert(c.homed);}
};
int main(){
 {Sim s;assert(!s.c.move(1,100));s.home();assert(s.c.move(400,500));int pulses=0;for(int i=0;i<5000&&(s.c.mode==Mode::Move||s.c.mode==Mode::Settle);i++)pulses+=s.tick();assert(pulses==400&&s.c.position==400&&s.c.mode==Mode::Idle);}
 {Sim s;s.home();assert(s.c.move(400,500));for(int i=0;i<5000&&s.c.mode!=Mode::Fault;i++)s.tick(false,false);assert(s.c.fault==Fault::Tracking&&s.c.enabled&&!s.c.homed);}
 {Sim s;s.c.encoder(0,false,1000);s.c.tick(1000,false,true);assert(s.c.fault==Fault::Encoder);}
 {Sim s;s.c.tick(1000,false,false);assert(s.c.fault==Fault::Driver&&s.c.enabled);}
 {Sim s;s.c.encoder(0,true,600000);s.c.tick(600000,false,true);assert(s.c.fault==Fault::Heartbeat);}
 {Sim s;s.c.encoder(0,true,31000);s.c.heartbeat(31000);assert(s.c.home(false));s.c.tick(31000,false,true);assert(s.c.fault==Fault::Timing);}
 {Sim s;assert(s.c.home(true));for(int i=0;i<2000&&s.c.mode!=Mode::Fault;i++)s.tick(true);assert(s.c.fault==Fault::HomeLimit);}
 {Sim s;assert(s.c.home(false));for(int i=0;i<25000&&s.c.mode!=Mode::Fault;i++)s.tick(false);assert(s.c.fault==Fault::HomeLimit);}
 {Sim s;s.home();assert(s.c.move(10,100));s.tick(true);assert(s.c.fault==Fault::Switch);}
 {Sim s;s.home();assert(!s.c.move(1,NAN));s.c.position=INT32_MAX;assert(!s.c.move(1,100));s.c.disarm();assert(!s.c.enabled&&!s.c.homed);}
 {MotionCore c;uint32_t t=UINT32_MAX-1000;c.encoder(0,true,t);assert(c.arm(t,true));c.encoder(0,true,500);c.heartbeat(500);c.tick(500,false,true);assert(c.mode==Mode::Idle);}
 {Sim s;s.home();assert(s.c.move(400,500));for(int i=0;i<5000&&s.c.mode!=Mode::Fault;i++){int p=s.tick(false,false);s.physical-=p;}assert(s.c.fault==Fault::Tracking);}
 {Sim s;s.home();assert(s.c.move(100,200));s.tick();s.c.hold();assert(s.c.mode==Mode::Idle&&s.c.enabled&&!s.c.homed&&!s.c.move(1,100));}
 {Config x;x.stepsPerRev=0;MotionCore c(x);c.encoder(0,true,0);assert(!c.arm(0,true));}
 std::cout<<"14 motion scenarios passed\n";
}
