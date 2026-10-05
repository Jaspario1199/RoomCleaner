"""Reproducible preliminary screening; no runtime configuration or CAD changes."""
from pathlib import Path
import math,json

def main():
    root=Path(__file__).resolve().parents[1]
    ideal=math.degrees(math.acos(1/math.sqrt(3)))
    front=[]
    # The experimental collar has13mm radius and rear face6.75mm fromthroat.
    # Assumed0.6mm cable,5.1mm throat. In a radial edge-started ray,
    # edge-started centerline radius2.55 plus projected tube halfwidth0.3/cos(alpha). No tolerance added here.
    for angle in (40,55,60):
        needed=2*(2.55+6.75*math.tan(math.radians(angle))+.3/math.cos(math.radians(angle)))
        front.append(dict(half_angle_deg=angle,edge_started_oblique_tube_bore_mm_no_tolerance=needed,
                          clearance_to_current_ID26_mm=(26-needed)/2))
    rear=[dict(angle_deg=a,opening_at_10mm_mm=2*(2.85+10*math.tan(math.radians(a))))for a in (55,65,70)]
    # Four equal-height rectangular anchors and corresponding rectangular
    # attachment points; platform exactly level with yaw0. Force balance fixes
    # horizontal COM shifts needed for roll/pitch moment balance. Any positive
    # tension distribution has these required shifts; no solver weighting.
    positions=[]
    for x,y in ((2.,1.5),(1.,1.),(.3,.3)):
        cx=.069*(x-2)/(2-.069);cy=.064*(y-1.5)/(1.5-.064)
        positions.append(dict(platform_xy_m=[x,y],required_COM_xy_m=[cx,cy],
                              centered_COM_level_pose_possible=(abs(cx)+abs(cy)<1e-12)))
    pair_pressed=2*.65*(9.65-5)
    home=[dict(angle_deg=a,spring_only_minimum_line_force_N=pair_pressed/math.cos(math.radians(a)),
               line_travel_for_2mm_collar_mm=2/math.cos(math.radians(a)),
               note='Ideal axial projection only; excludes switch force, guide friction and ring friction.')for a in (0,30,55,60)]
    data=dict(status='screening_only',ideal_orthant_half_angle_deg=ideal,
        margin_55_deg=55-ideal,margin_60_deg=60-ideal,
        front_collar_screen=front,rear_opening_screen=rear,level_equilibrium_screen=positions,
        home_force_screen=home,
        encoder_float_stack_mm=.2+.15+.1,
        encoder_reference_centering_mm=.25,
        fuse_bare_headroom_mm=70.9-(11+55.63),
        stopped_travel_examples=[dict(cable_speed_m_s=v,age_s=t,additional_travel_m=v*t)for v,t in ((.02,.5),(.02,.25),(.008,.25))],
        limits='Illustrative room and CAD defaults only; actual anchors, COM, diameter, field, force, wire bends and timing unmeasured. Stop examples exclude braking and buffering.')
    path=root/'calculations/design_skeleton_screening.json';path.write_text(json.dumps(data,indent=2)+'\n')
    print('Preliminary screening saved:',path.name)

if __name__=='__main__':main()
