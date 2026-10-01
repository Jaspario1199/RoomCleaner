"""Detached sign/scale calibration. Does not home or attach the claw."""
import argparse,json,socket,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--port');p.add_argument('--detached',action='store_true');p.add_argument('--output',default='encoder_calibration.json');args=p.parse_args()
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('0.0.0.0',8765));sock.settimeout(.01)
    latest={};epochs={}
    def receive():
        try:f=sock.recvfrom(256)[0].decode().split()
        except socket.timeout:return
        if len(f)!=9 or f[0]!='ENC1':return
        a,uid,boot,seq,health,ticks,raw,age=map(int,f[1:])
        if not 0<=a<4:return
        if a in epochs and epochs[a]!=(uid,boot):raise RuntimeError('Duplicate axis ID or node reboot; restart commission')
        epochs[a]=(uid,boot)
        if not health or age>100:raise RuntimeError('Bad magnet/tracking/read status')
        old=latest.get(a)
        if old and seq<=old[3]:return
        latest[a]=(ticks,time.monotonic()-age/1000,uid,seq)
    deadline=time.monotonic()+10
    while len(latest)<4 and time.monotonic()<deadline:receive()
    if len(latest)!=4:raise RuntimeError('Need all four nodes; axis 0/1/2/3; host UDP port8765')
    print('Node IDs:',[latest[i][2] for i in range(4)])
    if not args.port:
        print('Observe only. Use --port DEVICE --detached for bounded sign/scale tests.');return
    if not args.detached:raise RuntimeError('Detach the claw and acknowledge --detached')
    import serial
    ser=serial.Serial(args.port,115200,timeout=.01)
    try:
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            receive()
            if ser.readline().strip()==b'READY':break
        else:raise RuntimeError('No firmware READY')
        def fresh():
            if any(time.monotonic()-latest[i][1]>.15 for i in range(4)):raise RuntimeError('Stale encoder')
        def jog(axis,steps):
            fresh();ser.write(f'B DETACHED {axis} {steps}\n'.encode());end=time.monotonic()+5
            while time.monotonic()<end:
                receive();fresh();line=ser.readline().decode().strip()
                if line=='BENCH_DONE':
                    settle=time.monotonic()+.2
                    while time.monotonic()<settle:receive();fresh()
                    return
                if line.startswith('ERR'):raise RuntimeError(line)
            raise TimeoutError('Bench jog timeout')
        signs=[]
        for axis in range(4):
            start=latest[axis][0];jog(axis,100);delta=latest[axis][0]-start
            if not 96<=abs(delta)<=160:raise RuntimeError(f'Axis{axis}: wrong scale/slip/wiring: 100 steps produced {delta} ticks; expected128')
            signs.append(1 if delta>0 else -1);jog(axis,-100)
            if abs(latest[axis][0]-start)>8:raise RuntimeError(f'Axis{axis}: return error >8 ticks')
        Path(args.output).write_text(json.dumps({'node_ids':[latest[i][2] for i in range(4)],'signs':signs,'steps_per_rev':3200,'ticks_per_rev':4096},indent=2))
        print('Calibrated:',args.output,'; next run detached homing with EncoderRelay enabled')
    except Exception:
        ser.write(b'X\n');raise
    finally:ser.close();sock.close()
if __name__=='__main__':main()
