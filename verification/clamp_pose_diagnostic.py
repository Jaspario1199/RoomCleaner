"""Offline audit only: NOT integrated six-DOF control or attitude feedback."""
import json
import numpy as np
from pathlib import Path
from roomcleaner.config import DEFAULT_CONFIG
OFFSETS_M=np.array([[-.069,-.064,0],[.069,-.064,0],[.069,.064,0],[-.069,.064,0]])
def evaluate(point,rotation=np.eye(3)):
 offsets=OFFSETS_M@rotation.T
 vec=DEFAULT_CONFIG.anchors-np.array(point)-offsets
 lengths=np.linalg.norm(vec,axis=1);directions=vec/lengths[:,None]
 wrench=np.vstack((directions.T,np.cross(offsets,directions).T))
 old=np.linalg.norm(DEFAULT_CONFIG.anchors-point,axis=1)
 return dict(point_m=list(point),length_correction_mm=list((lengths-old)*1000),wrench_rank=int(np.linalg.matrix_rank(wrench)),axes=6,cables=4)
if __name__=='__main__':
 cfg=DEFAULT_CONFIG
 rows=[evaluate(np.array(p)) for p in [(cfg.room_width/2,cfg.room_depth/2,.5),(.3,.3,.5)]]
 Path('cad/exports/clamp_v1/pose_diagnostic.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
