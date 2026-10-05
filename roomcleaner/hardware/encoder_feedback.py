"""UDP encoder telemetry and fail-closed relay to the step-controller watchdog."""
from dataclasses import dataclass
import socket, threading, time, math

class EncoderFault(RuntimeError): pass
@dataclass(frozen=True)
class Sample:
    uid: int
    boot: int
    seq: int
    healthy: bool
    ticks: int
    raw: int
    received: float

class EncoderBank:
    def __init__(self, node_ids, signs, max_age=.15):
        if len(node_ids)!=4 or len(set(node_ids))!=4 or any(type(v) is not int or not 0<v<=0xffffffff for v in node_ids):
            raise ValueError('Four unique measured node IDs required')
        if len(signs)!=4 or any(type(v) is not int or v not in (-1,1) for v in signs):
            raise ValueError('Calibrate four encoder signs (+1/-1)')
        if isinstance(max_age,bool) or not isinstance(max_age,(int,float)) or not math.isfinite(max_age) or max_age<=0:
            raise ValueError('Encoder maximum age must be finite and positive')
        self.ids=tuple(node_ids);self.signs=tuple(signs);self.max_age=max_age
        self.samples=[None]*4;self.fault=None;self.lock=threading.Lock()
    def ingest(self, packet, now=None):
        now=time.monotonic() if now is None else now
        try:
            fields=packet.decode('ascii').strip().split()
            if len(fields)!=9 or fields[0]!='ENC1': raise ValueError()
            axis,uid,boot,seq,health,ticks,raw,age=map(int,fields[1:])
            if not 0<=axis<4 or uid!=self.ids[axis] or not 0<=boot<=0xffffffff or not 0<=seq<=0xffffffff or health not in (0,1) or not 0<=raw<4096 or abs(ticks)>1_000_000_000 or not 0<=age<=100:raise ValueError()
        except (ValueError,UnicodeError):return False
        with self.lock:
            old=self.samples[axis]
            if old and old.boot!=boot:
                self.fault=f'encoder {axis} rebooted; rehome required';return False
            if old and seq<=old.seq:return False # duplicates do NOT refresh age
            if not health:self.fault=f'encoder {axis} field/read/tracking fault'
            self.samples[axis]=Sample(uid,boot,seq,bool(health),ticks,raw,now-age/1000.)
        return True
    def counts(self, now=None):
        now=time.monotonic() if now is None else now
        with self.lock:
            if self.fault:raise EncoderFault(self.fault)
            if any(s is None or not s.healthy or now-s.received>self.max_age for s in self.samples):
                raise EncoderFault('missing/stale encoder feedback')
            return [s.ticks*sign for s,sign in zip(self.samples,self.signs)]

class EncoderRelay:
    def __init__(self, write, node_ids, signs, port=8765):
        self.bank=EncoderBank(node_ids,signs);self.write=write;self.port=port
        self.stop_event=threading.Event();self.ready=threading.Event();self.error=None
    def start(self):
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0',self.port));self.sock.settimeout(.005)
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start();return self
    def _run(self):
        next_send=0;armed=False
        while not self.stop_event.is_set():
            try:packet,_=self.sock.recvfrom(256);self.bank.ingest(packet)
            except socket.timeout:pass
            except OSError:break
            now=time.monotonic()
            if now<next_send:continue
            next_send=now+.02
            try:counts=self.bank.counts(now)
            except EncoderFault as e:
                if armed:
                    self.error=str(e)
                    try:self.write('X')
                    except Exception:pass
                    break
                continue
            try:self.write('E '+' '.join(map(str,counts)))
            except Exception as e:self.error=str(e);break
            armed=True;self.ready.set()
    def wait_ready(self,timeout=5):
        if not self.ready.wait(timeout):raise EncoderFault('No healthy calibrated telemetry from all four winches')
        if self.error:raise EncoderFault(self.error)
    def close(self):
        self.stop_event.set();self.sock.close();self.thread.join(timeout=1)
