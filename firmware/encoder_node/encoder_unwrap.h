#pragma once
inline int unwrapEncoderDelta(int raw,int previous){return (raw-previous+6144)%4096-2048;}
