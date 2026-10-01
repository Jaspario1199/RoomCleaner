// Seeed XIAO ESP32C3 + Grove AS5600. One local sensor per wall winch.
// No OTP programming. Each reboot creates a new tracking epoch.
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include "encoder_unwrap.h"
const char* WIFI_SSID="YOUR_WIFI";
const char* WIFI_PASS="YOUR_PASSWORD";
const char* HOST_IP="192.168.1.100"; // Python computer, reserve address in router
const int AXIS=0; // flash unique 0,1,2,3 for X,Y,Z,A
const int UDP_PORT=8765;
WiFiUDP udp;
uint32_t uid,bootId,sequence=0,lastSample=0,lastSend=0;
int previous=0,raw=0;int32_t ticks=0;
bool initialized=false,healthy=false,lost=false;
bool readReg(uint8_t reg,uint8_t* data,int count){
  Wire.beginTransmission(0x36);Wire.write(reg);
  if(Wire.endTransmission(false)!=0)return false;
  if(Wire.requestFrom(0x36,count)!=count)return false;
  for(int i=0;i<count;i++)data[i]=Wire.read();return true;
}
void sample(){
  uint32_t now=millis();
  if(initialized && now-lastSample>100)lost=true; // unobserved turns cannot be reconstructed
  lastSample=now;
  uint8_t status,bytes[2];
  healthy=readReg(0x0B,&status,1)&&readReg(0x0C,bytes,2);
  healthy=healthy && (status&0x20) && !(status&0x18) && !lost;
  if(!healthy){if(initialized)lost=true;return;}
  raw=((bytes[0]&0x0f)<<8)|bytes[1];
  if(!initialized){previous=raw;initialized=true;return;}
  int delta=unwrapEncoderDelta(raw,previous);
  if(abs(delta)>512 || abs(ticks)>999000000){lost=true;healthy=false;return;}
  ticks+=delta;previous=raw;
}
void setup(){
  Serial.begin(115200);Wire.begin(6,7);Wire.setClock(400000);Wire.setTimeOut(10);
  uid=(uint32_t)ESP.getEfuseMac();bootId=esp_random();
  WiFi.mode(WIFI_STA);WiFi.begin(WIFI_SSID,WIFI_PASS);WiFi.setSleep(false);
  Serial.printf("ENCODER axis=%d uid=%lu boot=%lu\n",AXIS,(unsigned long)uid,(unsigned long)bootId);
}
void loop(){
  uint32_t now=millis();if(now-lastSample>=5)sample();
  if(now-lastSend>=20 && WiFi.status()==WL_CONNECTED){
    lastSend=now;char packet[160];
    snprintf(packet,sizeof(packet),"ENC1 %d %lu %lu %lu %d %ld %d %lu",AXIS,(unsigned long)uid,(unsigned long)bootId,(unsigned long)++sequence,healthy?1:0,(long)ticks,raw,(unsigned long)(millis()-lastSample));
    udp.beginPacket(HOST_IP,UDP_PORT);udp.write((uint8_t*)packet,strlen(packet));udp.endPacket();
  }
  delay(1);
}
