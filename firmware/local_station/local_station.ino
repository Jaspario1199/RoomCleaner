// EXPERIMENTAL: detached single-axis USB bench only. Never suspended operation.
#include <Arduino.h>
#if !defined(ARDUINO_USB_CDC_ON_BOOT) || !ARDUINO_USB_CDC_ON_BOOT
#error "Select XIAO ESP32C3 with USB CDC On Boot enabled; UART RX conflicts with GPIO20 nFAULT."
#endif
#include <Wire.h>
#include <errno.h>
#include <stdlib.h>
#include "motion_core.h"
inline int unwrapEncoderDelta(int raw,int previous){return (raw-previous+6144)%4096-2048;}
using namespace roomcleaner;
constexpr int STEP_PIN=3, DIR_PIN=4, ENABLE_PIN=5, HOME_PIN=10, FAULT_PIN=20;
MotionCore axis;
uint32_t nextSample=0; int previousRaw=0; int32_t ticks=0; bool haveRaw=false;
char input[80]; size_t used=0;
int readRegister(uint8_t reg,int count){
 Wire.beginTransmission(0x36);Wire.write(reg);
 if(Wire.endTransmission(false)!=0)return -1;
 if(Wire.requestFrom(0x36,count)!=count)return -1;
 int result=0;while(Wire.available())result=(result<<8)|Wire.read();return result;
}
void sampleEncoder(uint32_t now){
 int status=readRegister(0x0B,1),raw=readRegister(0x0C,2);
 bool valid=status>=0&&raw>=0&&(status&0x20)&&!(status&0x18);
 if(valid){raw&=4095;if(haveRaw)ticks+=unwrapEncoderDelta(raw,previousRaw);previousRaw=raw;haveRaw=true;}
 axis.encoder(ticks,valid,now);
}
void command(char* line,uint32_t now){
 bool ok=false;
 if(!strcmp(line,"HB")){axis.heartbeat(now);return;}
 if(!strcmp(line,"ARM BENCH"))ok=axis.arm(now,digitalRead(FAULT_PIN)==HIGH);
 else if(!strcmp(line,"HOME"))ok=axis.home(digitalRead(HOME_PIN)==HIGH);
 else if(!strcmp(line,"HOLD")){axis.hold();ok=true;}
 else if(!strcmp(line,"DISARM")){axis.disarm();ok=true;}
 else if(!strcmp(line,"STATUS")){Serial.printf("mode=%d fault=%d homed=%d enabled=%d steps=%ld encoder=%ld\n",int(axis.mode),int(axis.fault),axis.homed,axis.enabled,long(axis.position),long(ticks));return;}
 else if(!strncmp(line,"MOVE ",5)){
  char* end;errno=0;long delta=strtol(line+5,&end,10);
  bool valid=errno==0&&end!=line+5&&(*end==' '||*end=='\t')&&delta>=-32000&&delta<=32000;
  char* start=end;errno=0;double speed=strtod(start,&end);
  valid=valid&&errno==0&&end!=start;while(*end==' '||*end=='\t')end++;
  if(valid&&*end==0)ok=axis.move(int32_t(delta),speed);
 }
 Serial.println(ok?"OK":"REJECTED");
}
void setup(){
 pinMode(ENABLE_PIN,OUTPUT);digitalWrite(ENABLE_PIN,HIGH); // Also external 10k pull-up mandatory.
 pinMode(STEP_PIN,OUTPUT);digitalWrite(STEP_PIN,LOW);pinMode(DIR_PIN,OUTPUT);
 pinMode(HOME_PIN,INPUT_PULLUP);pinMode(FAULT_PIN,INPUT_PULLUP);
 Serial.begin(115200);Wire.begin(6,7);Wire.setClock(400000);Wire.setTimeOut(5);
}
void loop(){
 uint32_t now=micros();
 if(int32_t(now-nextSample)>=0){sampleEncoder(now);nextSample=micros()+5000;}
 // Limit parser work per loop; discard overlong commands entirely.
 for(int n=0;n<16&&Serial.available();n++){
  char ch=Serial.read();if(ch=='\n'){input[used]=0;if(used<sizeof(input)-1)command(input,micros());used=0;}
  else if(ch!='\r'){if(used<sizeof(input)-1)input[used++]=ch;}
 }
 int pulse=axis.tick(micros(),digitalRead(HOME_PIN)==HIGH,digitalRead(FAULT_PIN)==HIGH);
 digitalWrite(ENABLE_PIN,axis.enabled?LOW:HIGH);
 if(pulse){digitalWrite(DIR_PIN,pulse>0?HIGH:LOW);delayMicroseconds(3);digitalWrite(STEP_PIN,HIGH);delayMicroseconds(3);digitalWrite(STEP_PIN,LOW);}
}
