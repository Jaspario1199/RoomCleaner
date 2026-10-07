"""Illustrative payload reserve and equal-share torque; never a capacity rating."""
from pathlib import Path
import json,math
G=9.81
JEANS_REFERENCE_KG=.9 # previous design assumption; weigh Jasper's actual garment
EFFECTOR_REFERENCE_KG=.45 # old assembly assumption; extended assembly must be weighed
RESERVE_PAYLOAD_KG=5*.45359237 # requested reserve investigation, not rated payload

def shared_tension(payload_kg,effector_kg,axes,angle_from_vertical_deg,upward_acceleration=0.):
    """Symmetric ideal equal sharing only; no off-centre moment/friction/snag."""
    if any(not math.isfinite(v) or v<0 for v in (payload_kg,effector_kg,upward_acceleration)) or axes not in (2,4) or not 0<=angle_from_vertical_deg<90:
        raise ValueError('Invalid illustrative load case')
    return (payload_kg+effector_kg)*(G+upward_acceleration)/(axes*math.cos(math.radians(angle_from_vertical_deg)))

def main():
    rows=[]
    for payload in (JEANS_REFERENCE_KG,RESERVE_PAYLOAD_KG):
        for axes in (2,4):
            for angle in (0,45,60,75):
                for acceleration in (0,2):
                    tension=shared_tension(payload,EFFECTOR_REFERENCE_KG,axes,angle,acceleration)
                    rows.append(dict(payload_kg=payload,effector_reference_kg=EFFECTOR_REFERENCE_KG,axes=axes,angle_from_vertical_deg=angle,upward_acceleration_m_s2=acceleration,tension_N=tension,required_spool_torque_Nm={str(radius):tension*radius/1000 for radius in (10,15,20)}))
    total_ratio=(RESERVE_PAYLOAD_KG+EFFECTOR_REFERENCE_KG)/(JEANS_REFERENCE_KG+EFFECTOR_REFERENCE_KG)
    data=dict(scope='Illustrative equal-share screening. No actual running torque, material/joint capacity, COM or angle envelope measured; no achieved FoS.',working_payload_reference_kg=JEANS_REFERENCE_KG,reserve_payload_kg=RESERVE_PAYLOAD_KG,payload_only_ratio=RESERVE_PAYLOAD_KG/JEANS_REFERENCE_KG,total_static_load_ratio=total_ratio,reserve_static_to_working_2m_s2_ratio=total_ratio*G/(G+2),cases=rows)
    Path(__file__).with_suffix('.json').write_text(json.dumps(data,indent=2)+'\n')
    print(f'{len(rows)} illustrative cases; payload-only ratio {data["payload_only_ratio"]:.3f}, total static ratio {total_ratio:.3f}, static reserve / working accelerated ratio {data["reserve_static_to_working_2m_s2_ratio"]:.3f}; achieved safety factor unknown.')
if __name__=='__main__':main()
