import time
import numpy as np
import pytest
from roomcleaner.config import DEFAULT_CONFIG
from roomcleaner.kinematics import CableRobot
from roomcleaner.perception.detector import Detection, SimulatedDetector
from roomcleaner.perception.live import LiveDetector
from roomcleaner.perception.verification import CameraVerifier, Observation, VerificationError, SimulatedVerifier
from roomcleaner.control.state_machine import Controller, State
from roomcleaner.hardware.driver import SerialDriver


class Evidence(SimulatedVerifier):
    def __init__(self, pickups=(True,), delivery=True):
        self.pickups=iter(pickups); self.delivery=delivery; self.release_checks=0
    def verify_pickup(self, target, probe): return next(self.pickups)
    def before_release(self,target): self.release_checks+=1
    def verify_delivery(self,target,hamper): return self.delivery


def setup(evidence):
    robot=CableRobot(DEFAULT_CONFIG)
    detector=SimulatedDetector(DEFAULT_CONFIG,1,1)
    return Controller(robot,detector,(3.5,.5),verifier=evidence), detector


def test_preview_does_not_remove_or_deliver_or_change_pose():
    ctrl,det=setup(Evidence()); pos=ctrl.position.copy()
    assert ctrl._plan_cycle()
    assert ctrl.picked_up==0 and len(det.detect())==1
    assert np.array_equal(ctrl.position,pos)


def test_release_does_not_count_until_following_camera_verification():
    ctrl,det=setup(Evidence()); stream=ctrl.iter_actions(return_to_rest=False)
    for kind,payload in stream:
        if kind=='release':
            assert ctrl.picked_up==0 and len(det.detect())==1
    assert ctrl.picked_up==1 and not det.detect()


def test_retry_before_delivery():
    e=Evidence((False,True)); ctrl,det=setup(e)
    actions=list(ctrl.iter_actions(return_to_rest=False))
    assert [k for k,p in actions].count('grip')==2
    assert [k for k,p in actions].count('release')==2
    assert e.release_checks==1 and ctrl.picked_up==1


def test_failed_delivery_keeps_item_and_count():
    ctrl,det=setup(Evidence(delivery=False))
    with pytest.raises(VerificationError,match='released into hamper'):
        list(ctrl.iter_actions())
    assert ctrl.picked_up==0 and len(det.detect())==1 and ctrl.state==State.FAULT


def test_retry_limit_never_delivers():
    e=Evidence((False,False,False)); ctrl,det=setup(e)
    with pytest.raises(VerificationError,match='retry limit'):
        list(ctrl.iter_actions())
    assert e.release_checks==0 and ctrl.picked_up==0 and len(det.detect())==1


def test_live_execution_cannot_use_missing_camera_evidence():
    r=CableRobot(DEFAULT_CONFIG); holder=LiveDetector(None)
    with pytest.raises(VerificationError,match='camera verifier'):
        list(Controller(r,holder,(3.5,.5)).iter_actions())


def test_serial_requires_real_home_measurements():
    with pytest.raises(ValueError,match='measured bead'):
        SerialDriver(CableRobot(DEFAULT_CONFIG))


def camera_fixture():
    projection=np.array([[100,0,0,0],[0,100,0,0],[0,0,0,1]])
    patch=np.random.default_rng(4).integers(0,255,(20,20,3),dtype=np.uint8)
    def observation(x, timestamp=None, duplicate=False):
        frame=np.zeros((220,220,3),np.uint8)
        frame[50:70,x:x+20]=patch
        items=[Detection(np.zeros(3),'sock',.9,bbox=(x,50,x+20,70))]
        if duplicate:
            frame[100:120,30:50]=patch
            items.append(Detection(np.zeros(3),'sock',.9,bbox=(30,100,50,120)))
        return Observation(time.monotonic() if timestamp is None else timestamp,frame,items)
    return projection,observation


def test_camera_requires_positive_motion_and_stable_hamper_payload():
    p,obs=camera_fixture(); frames=iter([obs(20),obs(70),obs(70),obs(70),obs(150),obs(150),obs(150),obs(150)])
    v=CameraVerifier(lambda:next(frames),p,(140,40,190,90),settle_s=0)
    target=Detection(np.zeros(3),'sock',.9,bbox=(20,50,40,70))
    v.before_pickup(target)
    assert v.verify_pickup(target,np.array([.8,.6,.5]))
    v.before_release(target)
    assert v.verify_delivery(target,np.array([1.6,.6,.5]))


@pytest.mark.parametrize('mode',['stationary','missing','ambiguous'])
def test_disappearance_stationary_and_lookalike_are_not_success(mode):
    p,obs=camera_fixture(); first=obs(20)
    after=obs(20 if mode=='stationary' else 70,duplicate=mode=='ambiguous')
    if mode=='missing': after.detections=[]
    frames=iter([first,after])
    v=CameraVerifier(lambda:next(frames),p,(140,40,190,90),settle_s=0)
    target=first.detections[0]; v.before_pickup(target)
    assert not v.verify_pickup(target,np.array([.8,.6,.5]))


def test_repeated_frame_rejected():
    p,obs=camera_fixture(); first=obs(20); repeated=obs(70,timestamp=first.timestamp)
    frames=iter([first,repeated])
    v=CameraVerifier(lambda:next(frames),p,(140,40,190,90),settle_s=0)
    v.before_pickup(first.detections[0])
    with pytest.raises(VerificationError,match='Stale'):
        v.verify_pickup(first.detections[0],np.array([.8,.6,.5]))


def test_home_is_not_a_claw_pose_and_confirmation_requires_preparation():
    from roomcleaner.hardware.driver import MockDriver
    r=CableRobot(DEFAULT_CONFIG); d=MockDriver(r)
    d.home()
    assert d.homed and not d.pose_initialized
    with pytest.raises(RuntimeError): d.confirm_pose(attached=True)
    with pytest.raises(RuntimeError): d.prepare_pose(r.find_rest_position())
    pose=r.find_rest_position(); d.prepare_pose(pose,detached=True)
    assert not d.pose_initialized
    assert np.allclose(d.confirm_pose(attached=True),pose)
    d.stop()
    assert not d.homed and not d.pose_initialized and d.prepared_pose is None


def test_subsampling_preserves_right_angle_corner():
    from roomcleaner.hardware.executor import subsample_path
    path=np.array([[0,0,0],[.03,0,0],[.03,.03,0],[.03,.06,0]])
    thinned=subsample_path(path,step_m=.15)
    assert any(np.allclose(p,[.03,0,0]) for p in thinned)


def live_session_with_mock_hardware():
    pytest.importorskip('flask')
    from roomcleaner.app.server import LiveSession
    from roomcleaner.hardware.driver import MockDriver
    from roomcleaner.hardware.gripper import MockGripper
    session=LiveSession(demo=True)
    session.driver=MockDriver(session.robot)
    session.driver.home()
    session.driver.prepare_pose(session.rest,detached=True)
    session.driver.confirm_pose(attached=True)
    session.gripper=MockGripper()
    session._hw_connected=True
    return session


@pytest.mark.parametrize('delivery,expected',[(True,1),(False,0)])
def test_console_counts_only_verified_delivery(delivery,expected):
    session=live_session_with_mock_hardware()
    detector=SimulatedDetector(session.robot.cfg,1,1)
    ctrl=Controller(session.robot,detector,session.hamper_xy,verifier=Evidence(delivery=delivery))
    session._run_mission(ctrl)
    assert session._picked_total==expected
    assert session._controller is None


def test_live_stop_bypasses_lock_held_by_manual_setup():
    import threading
    session=live_session_with_mock_hardware()
    errors=[]
    def stop():
        try: session.command('stop',{})
        except Exception as e: errors.append(e)
    session._lock.acquire()
    t=threading.Thread(target=stop,daemon=True)
    try:
        t.start();t.join(.5)
        assert not t.is_alive(), 'STOP blocked behind a manual setup command'
    finally:
        session._lock.release();t.join(1)
    assert not errors and session._stop_flag.is_set()
    assert session.driver.commands[-1]=='X'
