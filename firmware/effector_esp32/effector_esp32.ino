/*
 * RoomCleaner wireless effector -- ESP32 on the claw.
 *
 * The gripper servo lives here, not on the central Arduino. The ESP32 joins your
 * WiFi and runs a tiny HTTP server; the host computer sends grip/release:
 *
 *     GET /grip?angle=140     -> close clamp, replies "OK 140"
 *     GET /release?angle=20   -> open the clamp, replies "OK 20"
 *     GET /status             -> replies "READY <angle>"
 *     GET /setup               -> park at DEFAULT_RELEASE so the horn/drum can be
 *                                  attached at a known zero (D8), replies
 *                                  "SETUP <angle> -- attach horn/drum now"
 *
 * Only the 4 Dyneema cables touch the effector -- no wire crosses the room.
 * Grip/release aren't time-critical, so WiFi latency here is harmless.
 *
 * Power: a small LiPo on the effector (through a 5-6 V buck/boost to the servo).
 * Optionally add charging contacts at the rest/dock position.
 *
 * Board: any ESP32 dev board. Set the servo pin to a free GPIO.
 * Library: ESP32Servo (Library Manager -> "ESP32Servo").
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <ESPmDNS.h>
#include <Wire.h>
#include <math.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* HOSTNAME  = "roomcleaner-claw";   // -> http://roomcleaner-claw.local

const int SERVO_PIN = 13;
const int DEFAULT_RELEASE = 20;

WebServer server(80);
Servo gripper;
int currentAngle = DEFAULT_RELEASE;

bool imuPresent=false,imuFresh=false,filterInit=false,gyroCalibrated=false;
float rollDeg=0,pitchDeg=0,gxBias=0,gyBias=0,gzBias=0;
unsigned long imuLast=0,stationarySince=0;
bool imuRead(uint8_t reg,uint8_t* data,int n){
 Wire.beginTransmission(0x68);Wire.write(reg);if(Wire.endTransmission(false)!=0)return false;
 if(Wire.requestFrom(0x68,n)!=n)return false;
 for(int i=0;i<n;i++)data[i]=Wire.read();return true;
}
void imuWrite(uint8_t reg,uint8_t value){Wire.beginTransmission(0x68);Wire.write(reg);Wire.write(value);Wire.endTransmission();}
void updateTilt(){
 unsigned long now=millis();if(now-imuLast<10)return;
 float dt=(now-imuLast)/1000.f;uint8_t b[14];
 if(!imuPresent || !imuRead(0x3B,b,14)){imuFresh=false;stationarySince=0;return;}
 float ax=(int16_t)((b[0]<<8)|b[1])/16384.f,ay=(int16_t)((b[2]<<8)|b[3])/16384.f,az=(int16_t)((b[4]<<8)|b[5])/16384.f;
 float gx=(int16_t)((b[8]<<8)|b[9])/131.f-gxBias,gy=(int16_t)((b[10]<<8)|b[11])/131.f-gyBias,gz=(int16_t)((b[12]<<8)|b[13])/131.f-gzBias;
 float ar=atan2f(ay,az)*180.f/PI,ap=atan2f(-ax,sqrtf(ay*ay+az*az))*180.f/PI;
 float norm=sqrtf(ax*ax+ay*ay+az*az);
 bool quiet=fabsf(norm-1)<.08f && fabsf(gx)<5 && fabsf(gy)<5 && fabsf(gz)<5;
 if(!filterInit || dt>.1f){rollDeg=ar;pitchDeg=ap;filterInit=true;stationarySince=0;}
 else {rollDeg+=gx*dt;pitchDeg+=gy*dt;if(quiet){rollDeg=.98f*rollDeg+.02f*ar;pitchDeg=.98f*pitchDeg+.02f*ap;}}
 if(quiet){if(!stationarySince)stationarySince=now;}else stationarySince=0;
 imuLast=now;imuFresh=true;
}
bool tiltReady(){return gyroCalibrated && imuPresent && imuFresh && millis()-imuLast<100 && stationarySince && millis()-stationarySince>=500;}
bool levelEnough(){return tiltReady() && fabsf(rollDeg)<=5 && fabsf(pitchDeg)<=5;}
void handleTilt(){
 char buf[160];snprintf(buf,sizeof(buf),"{\"valid\":%s,\"roll_deg\":%.3f,\"pitch_deg\":%.3f,\"level\":%s,\"age_ms\":%lu}",tiltReady()?"true":"false",rollDeg,pitchDeg,levelEnough()?"true":"false",(unsigned long)(millis()-imuLast));
 server.send(200,"application/json",buf);
}

void handleCalibrate(){
 if(!server.hasArg("stationary") || server.arg("stationary")!="1" || !imuPresent){server.send(400,"text/plain","Place unloaded clamp still; use stationary=1");return;}
 float sx=0,sy=0,sz=0;
 for(int i=0;i<200;i++){
  uint8_t b[14];if(!imuRead(0x3B,b,14)){server.send(503,"text/plain","IMU read failed");return;}
  float ax=(int16_t)((b[0]<<8)|b[1])/16384.f,ay=(int16_t)((b[2]<<8)|b[3])/16384.f,az=(int16_t)((b[4]<<8)|b[5])/16384.f;
  float gx=(int16_t)((b[8]<<8)|b[9])/131.f,gy=(int16_t)((b[10]<<8)|b[11])/131.f,gz=(int16_t)((b[12]<<8)|b[13])/131.f;
  if(fabsf(sqrtf(ax*ax+ay*ay+az*az)-1)>.08f || fabsf(gx)>5 || fabsf(gy)>5 || fabsf(gz)>5){server.send(409,"text/plain","Not stationary; calibration rejected");return;}
  sx+=gx;sy+=gy;sz+=gz;delay(10);
 }
 gxBias=sx/200;gyBias=sy/200;gzBias=sz/200;gyroCalibrated=true;filterInit=false;stationarySince=0;
 server.send(200,"text/plain","CALIBRATED gyro; physical board alignment still required");
}

void setAngle(int a) {
  currentAngle = constrain(a, 20, 140);
  gripper.write(currentAngle);
}

void handleGrip() {
  if(!levelEnough()){server.send(409,"text/plain","ERR tilt unsettled/unhealthy/outside5deg");return;}
  int a = server.hasArg("angle") ? server.arg("angle").toInt() : 140;
  setAngle(a);
  server.send(200, "text/plain", "OK " + String(currentAngle));
}

void handleRelease() {
  int a = server.hasArg("angle") ? server.arg("angle").toInt() : DEFAULT_RELEASE;
  setAngle(a);
  server.send(200, "text/plain", "OK " + String(currentAngle));
}

void handleStatus() {
  server.send(200, "text/plain", "READY " + String(currentAngle));
}

void handleSetup() {
  // D8: park the servo at DEFAULT_RELEASE so the drum/horn is pressed on at a
  // known zero.
  setAngle(DEFAULT_RELEASE);
  server.send(200, "text/plain", "SETUP " + String(currentAngle) + " -- attach horn/drum now");
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21,22);Wire.setClock(400000);Wire.setTimeOut(10);
  uint8_t who=0;imuPresent=imuRead(0x75,&who,1) && who==0x68;
  if(imuPresent){imuWrite(0x6B,0);imuWrite(0x1A,3);imuWrite(0x1B,0);imuWrite(0x1C,0);}
  gripper.attach(SERVO_PIN);
  setAngle(DEFAULT_RELEASE);          // start open

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.println("\nWiFi: " + WiFi.localIP().toString());

  if (MDNS.begin(HOSTNAME)) Serial.println("mDNS: http://" + String(HOSTNAME) + ".local");

  server.on("/grip", handleGrip);
  server.on("/release", handleRelease);
  server.on("/status", handleStatus);
  server.on("/tilt", handleTilt);
  server.on("/calibrate", handleCalibrate);
  server.on("/setup", handleSetup);
  server.begin();
}

void loop() {
  updateTilt();
  server.handleClient();
}
