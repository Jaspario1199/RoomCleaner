// Shared rotation-comparison math, also exercised by native bench tests.
#pragma once
#include <stdint.h>
static inline int64_t encoderErrorNumerator(int32_t ticks,int32_t baseTicks,int32_t steps,int32_t baseSteps){
 return ((int64_t)ticks-baseTicks)*3200-((int64_t)steps-baseSteps)*4096;
}
static inline bool encoderOutsideTolerance(int64_t error){
 const int64_t limit=48LL*4096;return error>limit || error<-limit;
}
