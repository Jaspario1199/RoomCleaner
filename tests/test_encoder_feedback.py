import pytest
from roomcleaner.hardware.encoder_feedback import EncoderBank,EncoderFault

def packet(a,uid,seq=1,boot=7,health=1,ticks=4090,raw=4090,age=0):
 return f'ENC1 {a} {uid} {boot} {seq} {health} {ticks} {raw} {age}'.encode()
def bank():return EncoderBank([1,2,3,4],[1,-1,1,-1])
def fill(b,t=0):
 for a in range(4):assert b.ingest(packet(a,a+1),t)

def test_signs_and_stale():
 b=bank();fill(b);assert b.counts(.1)==[4090,-4090,4090,-4090]
 with pytest.raises(EncoderFault):b.counts(.151)
def test_duplicate_cannot_refresh_watchdog():
 b=bank();fill(b);assert not b.ingest(packet(0,1),.14)
 with pytest.raises(EncoderFault):b.counts(.16)
def test_reboot_latches_fault():
 b=bank();fill(b);b.ingest(packet(0,1,seq=2,boot=8),.01)
 with pytest.raises(EncoderFault,match='reboot'):b.counts(.02)
def test_bad_magnet_latches_fault():
 b=bank();fill(b);b.ingest(packet(0,1,seq=2,health=0),.01)
 with pytest.raises(EncoderFault,match='field'):b.counts(.02)
def test_wrong_id_malformed_and_old_samples():
 b=bank();assert not b.ingest(packet(0,9),0);assert not b.ingest(b'ENC1 junk',0)
 assert not b.ingest(packet(0,1,age=101),0)
def test_dropped_sequence_still_uses_absolute_unwrapped_counts():
 b=bank();fill(b);assert b.ingest(packet(0,1,seq=10,ticks=4102,raw=6),.02)
 assert b.counts(.02)[0]==4102


def test_udp_relay_stops_when_stream_disappears():
 import socket,time
 from roomcleaner.hardware.encoder_feedback import EncoderRelay
 sent=[];relay=EncoderRelay(sent.append,[1,2,3,4],[1]*4,port=0).start()
 sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 try:
  port=relay.sock.getsockname()[1]
  for a in range(4):sock.sendto(packet(a,a+1),('127.0.0.1',port))
  relay.wait_ready(timeout=1)
  assert any(s.startswith('E ') for s in sent)
  deadline=time.monotonic()+1
  while not relay.error and time.monotonic()<deadline:time.sleep(.005)
  assert relay.error and sent[-1]=='X'
 finally:sock.close();relay.close()

def test_firmware_ratio_tolerance_and_unwrap(tmp_path):
 import subprocess
 from pathlib import Path
 root=Path(__file__).resolve().parents[1]
 src=tmp_path/'check.cpp';exe=tmp_path/'check'
 src.write_text('#include <cassert>\n#include "'+str(root/'firmware/roomcleaner_firmware/encoder_guard.h')+'"\n#include "'+str(root/'firmware/encoder_node/encoder_unwrap.h')+'"\nint main(){assert(unwrapEncoderDelta(6,4090)==12);assert(unwrapEncoderDelta(4090,6)==-12);assert(encoderErrorNumerator(4096,0,3200,0)==0);assert(!encoderOutsideTolerance(48LL*4096));assert(encoderOutsideTolerance(49LL*4096));assert(encoderOutsideTolerance(-49LL*4096));assert(encoderErrorNumerator(-4096,0,-3200,0)==0);assert(encoderErrorNumerator(1000000000,999995904,3200,0)==0);}')
 subprocess.run(['g++','-std=c++11',str(src),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)

def test_wifi_grip_checks_tilt_before_closing(monkeypatch):
 from roomcleaner.hardware.gripper import WiFiGripper
 g=WiFiGripper();calls=[]
 monkeypatch.setattr(g,'tilt_status',lambda:{'valid':True,'level':True})
 monkeypatch.setattr(g,'_get',lambda p:calls.append(p))
 g.grip();assert calls==['/grip?angle=140']

def test_wifi_grip_refuses_unlevel_without_servo_command(monkeypatch):
 import time
 from roomcleaner.hardware.gripper import WiFiGripper
 g=WiFiGripper();calls=[];clock=iter([0,4])
 monkeypatch.setattr(time,'monotonic',lambda:next(clock))
 monkeypatch.setattr(g,'tilt_status',lambda:{'valid':True,'level':False})
 monkeypatch.setattr(g,'_get',lambda p:calls.append(p))
 with pytest.raises(RuntimeError,match='pickup refused'):g.grip()
 assert calls==[]

@pytest.mark.parametrize('age',[float('nan'),float('inf'),-1,0,True])
def test_invalid_watchdog_configuration_cannot_disable_stale_guard(age):
 with pytest.raises(ValueError,match='maximum age'):
  EncoderBank([1,2,3,4],[1]*4,max_age=age)

def test_boolean_sign_is_not_calibration():
 with pytest.raises(ValueError,match='signs'):
  EncoderBank([1,2,3,4],[True,1,1,1])

@pytest.mark.parametrize('boot,seq',[(-1,1),(2**32,1),(7,-1),(7,2**32)])
def test_invalid_epoch_sequence_does_not_refresh_feedback(boot,seq):
 b=bank();fill(b)
 assert not b.ingest(packet(0,1,boot=boot,seq=seq),.14)
 with pytest.raises(EncoderFault):b.counts(.16)
