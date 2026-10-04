#include "../../firmware/local_station/motion_core.h"
#include <cassert>
#include <iostream>
using namespace roomcleaner;
struct Sim{MotionCore c;uint32_t t=0;int physical=0;Sim(){sample();assert(c.arm(t,true));}void sample(){c.encoder(lround(physical*4096./3200),true,t);c.heartbeat(t);}void tick(bool open=false,bool follow=true){t+=1000;sample();int p=c.tick(t,open,true);if(follow)physical+=p;}void home(){assert(c.home(false));for(int i=0;i<20000&&!c.homed&&c.mode!=Mode::Fault;i++)tick(physical<=-20);assert(c.homed);}};
int main(){
 {Sim s;assert(s.c.home(false));s.tick(true);s.tick(false);assert(s.c.mode==Mode::Seek&&!s.c.homed);}
 {Sim s;assert(s.c.home(false));for(int i=0;i<10000&&s.c.mode!=Mode::Refine;i++)s.tick(s.physical<=-20);assert(s.c.mode==Mode::Refine);assert(s.physical>0);s.tick(true);s.tick(false);assert(!s.c.homed&&s.c.mode==Mode::Refine);for(int i=0;i<20;i++)s.tick(false);assert(!s.c.homed);}
 {Sim s;s.home();assert(s.c.move(10,100));for(int i=0;i<3000&&s.c.mode==Mode::Move;i++)s.tick(false,false);assert(s.c.mode==Mode::Settle);assert(!s.c.move(10,100));for(int i=0;i<600&&s.c.mode!=Mode::Fault;i++)s.tick(false,false);assert(s.c.fault==Fault::Tracking&&!s.c.homed);}
 {Sim s;s.home();assert(s.c.move(10,100));for(int i=0;i<3000&&s.c.mode!=Mode::Move&&s.c.mode!=Mode::Fault;i++)s.tick();for(int i=0;i<3000&&s.c.mode==Mode::Move;i++)s.tick();assert(s.c.mode==Mode::Settle);for(int i=0;i<60;i++)s.tick();assert(s.c.mode==Mode::Idle&&s.c.homed);}
 std::cout<<"4 fresh debounce/arrival regression scenarios passed\n";
}
