# Parameter closure register — 4 October 2026

Generated from `unknown_parameters.json`. Selected solutions do not close hardware tests. Null values remain unset. Work packages are staged contributions to shared records; completing a package does not automatically close every referenced group. Specialist audits contain alternatives, provenance and tests.

## Filled reference values

22 fields have cited reference values. These are distinct from measured or resolved values.

| Field | Reference | Basis | Qualification |
|---|---|---|---|
| M07.spring_rate | 0.65 N/mm | supplier_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M07.spring_free_length | 9.65 mm | supplier_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M07.spring_solid_length | 3.81 mm | supplier_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M07.spring_installed_lengths | [7, 5] mm | cad_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M13.shaft_diameter | 5 mm | user_supplied | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M13.shaft_projection | 24 mm | user_supplied | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M23.extension_length | 150 mm | cad_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M25.servo_endpoints | [20, 140] deg | cad_nominal | CAD design angles; actual horn indexing and travel stops remain unmeasured. |
| M26.gear_module | 1.5 mm | cad_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M26.gear_backlash | 0.2 mm | cad_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M27.pad_thickness | 5 mm | cad_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M28.assembled_reach | 268 mm | cad_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| M34.camera_angle | 28 deg | cad_nominal | Bracket tilt magnitude; signed local X rotation is -28 deg. Not optical extrinsic calibration. |
| C06.microstep_factor | 16 1 | code_default | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| C06.encoder_counts_per_rev | 4096 count/rev | supplier_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| C07.run_error | 64 count | code_default | Detached local station tracking tolerance in encoder counts; central Uno guard uses a different profile. |
| C07.run_error_dwell | 0.15 s | code_default | Detached local station default, seconds; physical error/dwell qualification remains open. |
| C07.arrival_error | 4 count | code_default | Detached local station default, encoder counts; actual arrival precision remains open. |
| C07.settling_interval | 0.05 s | code_default | Continuous in-tolerance arrival dwell in seconds; separate timeout is 0.5 s. |
| C09.heartbeat_timeout | 0.5 s | code_default | Detached local station default in seconds; not machine-wide fault propagation latency. |
| C12.quiet_interval | 0.5 s | code_default | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |
| E02.supply_voltage | 12 V | proposed_station_nominal | Nominal/default or supplied fact; actual measurement and relevant hardware tests remain open. |

Execution priorities and remaining user inputs: [docs/PRIORITY_EXECUTION_20261004.md](../../docs/PRIORITY_EXECUTION_20261004.md).

## W01 — Scope, architecture profiles and coordinate contracts

Milestone dependencies: none.

Scope/profile and datum contracts, explicit acceptance/error-budget targets and transport/connector study recorded. Homing and IMU procedure decisions can be selected here; their physical calibration closes later.

## W02 — Room, components, mass and preliminary load/model survey

Milestone dependencies: W01.

Room/part/COM survey and preliminary finite-body force/moment/load envelope recorded. This is design-input maturity; final supported workspace/tension qualification remains W09.

## W03 — Outlet, bead, guides and secured switch

Milestone dependencies: W02.

One coherent cartridge/bracket/cover clears routing, all screw seats and service paths; qualified bead approach, switch margins, reset and retention demonstrated.

## W04 — Shaft, spool, hub, payout and encoder

Milestone dependencies: W02.

Mechanical shaft/spool/magnet interfaces and controlled payout/retention experiments defined and performed where the protected fixture permits. Local powered torque/feedback evidence joins W05/W07 results before group closure.

## W05 — Power, harness, fuse, enclosure and thermal layout

Milestone dependencies: W01, W02.

Exact retained power/harness/connector geometry and protection design fit the selected transport profile. Enclosed powered current/thermal evidence is gathered jointly with W04/W07; wire bends cannot be inferred from component bodies.

## W06 — Dock, structural sections and printable process

Milestone dependencies: W03, W04, W05.

Directional structural calculations and actual-process coupons/joint/load/creep tests support explicit working envelope; assembly/service tool checks and exports pass.

## W07 — Motion execution, synchronized four-axis control and faults

Milestone dependencies: W04, W05.

Actual firmware target compiles; pulse timing/clock/segment/fault tests pass; machine-wide supported stop/recovery policies verified, without auto-resume after boot/link loss.

## W08 — Extended clamp, horn, pads and passive attitude

Milestone dependencies: W02, W05.

Physical horn and joint stacks, travel stops, rail/gear fits, cloth retention, extension flex and near-level settled acceptance tested.

## W09 — Validated full-body workspace, pose and collision limits

Milestone dependencies: W06, W07, W08.

Measured finite-body model, cable friction/payout and all body/cable/garment obstacles constrain every path; supported pose/tilt/tension validation closes tolerances.

## W10 — Moving camera, image age and pickup/delivery evidence

Milestone dependencies: W08, W09.

Intrinsics/extrinsics and per-image camera pose calibrated; stale/occluded observations rejected; camera-only motion and failed pickup/release negative tests do not mark success.

## W11 — Inventory, versioned print/order and end-to-end commissioning

Milestone dependencies: W06, W07, W09, W10.

One consistent hardware/software/print version with real inventory and remaining orders; staged restrained tests followed by verified pickup/probe/delivery cycle and documented limits.

## Parameter groups

| ID | Named fields and unit labels | Solution state | Next action |
|---|---|---|---|
| P01 | position_accuracy [m]; attitude_accuracy [rad]; cable_length_accuracy [m]; vision_localization_accuracy [m]; maximum_settled_tilt [rad]; allowed_image_motion_error [m]; pickup_precision_target [1]; pickup_recall_target [1]; delivery_precision_target [1]; minimum_visible_payload_fraction [1]; maximum_safe_stop_distance [m]; minimum_verified_runtime [s]; declared_ambient_range [degC]; declared_duty_cycle [1]; validation_trial_count [integer]; cycle_life_target [cycles]; installation_angular_budget [deg]; allocated_survey_error [m]; allocated_payout_error [m]; allocated_pose_error [m]; allocated_vision_error [m]; allocated_timing_motion_error [m] | proposed | Define explicit accuracy, angular, timing, visibility and validation targets; label proposed targets separately from tested performance. |
| M01 | outlet_positions [m]; outlet_axes [1]; axis_uncertainty [deg]; room_dimensions [m]; obstacle_bounds [m]; survey_margin [m] | proposed | Survey real wall throats and installation axes; keep room defaults provisional. |
| M02 | outgoing_half_angle [deg]; homing_half_angle [deg]; working_pose_set [pose_set]; homing_pose_set [pose_set] | proposed | Compute feasible-direction cone plus uncertainty; develop fixed wide outlet with a distinct qualified homing cone. |
| M03 | line_diameter [mm]; terminated_break_load [N]; line_stiffness [N/m]; line_creep [percent]; line_linear_density [kg/m]; cable_sag [m] | proposed | Execute W02 measurement/design and closure criteria in the cited audit. |
| M04 | stopper_diameter [mm]; stopper_length [mm]; edge_radius [mm]; knot_cavity_diameter [mm]; stopper_retention [N]; stopper_mass [kg] | proposed | Compare rounded removable stopper shapes and oblique contact; do not order a bead based only on diameter. |
| M05 | ring_fit_clearance [mm]; capture_deflection [mm]; ring_retention [N] | proposed | Execute W03 measurement/design and closure criteria in the cited audit. |
| M06 | switch_trip [mm]; switch_release [mm]; switch_overtravel [mm]; switch_force [N] | proposed | Measure switch trip/release/overtravel and operating force; design adjustable M3-retained cradle. |
| M07 | spring_rate [N/mm]; spring_free_length [mm]; spring_solid_length [mm]; spring_installed_lengths [mm]; spring_return_force [N] | proposed | Execute W03 measurement/design and closure criteria in the cited audit. |
| M08 | guide_spacing [mm]; guide_parallel_error [deg]; slide_clearance [mm]; guide_friction [1] | proposed | Execute W03 measurement/design and closure criteria in the cited audit. |
| M09 | clamp_head_diameter [mm]; clamp_bolt_length [mm]; head_seat_height [mm]; pilot_pullout [N] | proposed | Add full clamp-head bearing seats and test service access; provisional seats currently fail. |
| M10 | incoming_half_angle [deg]; line_bend_radius [mm]; ring_friction_ratio [1]; abrasion_life [cycles] | proposed | Execute W03 measurement/design and closure criteria in the cited audit. |
| M11 | effective_radius [mm]; winding_width [mm]; line_capacity [m] | proposed | Execute W04 measurement/design and closure criteria in the cited audit. |
| M12 | running_torque_curve [N*m]; cable_working_limit [N]; cable_acceleration [m/s^2] | proposed | Execute W04 measurement/design and closure criteria in the cited audit. |
| M13 | shaft_diameter [mm]; shaft_flat [mm]; shaft_projection [mm]; motor_thread_depth [mm]; motor_bearing_limit [N] | proposed | Execute W02 measurement/design and closure criteria in the cited audit. |
| M14 | hub_clearance [mm]; spool_runout [mm]; hub_slip_torque [N*m]; hub_axial_retention [N] | proposed | Execute W04 measurement/design and closure criteria in the cited audit. |
| M15 | magnet_eccentricity [mm]; die_gap [mm]; field_strength [mT]; chip_location_error [mm] | proposed | Close eccentricity stack using a centering fixture and adjustable pedestal; verify with actual field/runout measurements. |
| M16 | station_mass [kg]; effector_mass [kg]; payload_mass [kg]; center_of_mass [m]; body_inertia [kg*m^2]; payload_CG_range [m] | proposed | Execute W02 measurement/design and closure criteria in the cited audit. |
| M17 | pose_tensions [N]; guide_reaction [N]; wall_load_offset [mm]; wall_moment [N*m] | proposed | Execute W06 measurement/design and closure criteria in the cited audit. |
| M18 | bracket_thickness [mm]; bracket_fastener_pattern [mm]; bracket_deflection [mm] | proposed | Design independent outlet load bracket and front enclosure; current cartridge is unattached and intersects case. |
| M19 | rail_overlap [mm]; rail_side_clearance [mm]; rail_face_clearance [mm]; lock_retention [N] | proposed | Execute W06 measurement/design and closure criteria in the cited audit. |
| M20 | wood_species [text]; wood_moisture [percent]; finish_thickness [mm]; effective_embedment [mm]; edge_distance [mm] | proposed | Execute W02 measurement/design and closure criteria in the cited audit. |
| M21 | sleeve_diameter [mm]; sleeve_length [mm]; sleeve_flange_thickness [mm]; shear_fit [mm] | proposed | Execute W06 measurement/design and closure criteria in the cited audit. |
| M22 | process_allowable_stress [MPa]; allowable_deflection [mm]; design_cycles [cycles]; creep_duration [h] | proposed | Execute W06 measurement/design and closure criteria in the cited audit. |
| M23 | extension_length [mm]; extension_stiffness [N/mm]; tip_deflection [mm]; joint_rotation [deg] | proposed | Execute W08 measurement/design and closure criteria in the cited audit. |
| M24 | clevis_locations [mm]; clevis_pin_diameter [mm]; termination_limit [N]; cable_clearance [mm] | proposed | Execute W02 measurement/design and closure criteria in the cited audit. |
| M25 | servo_endpoints [deg]; servo_torque [N*m]; servo_stall_current [A]; servo_spline [text]; horn_stack [mm]; servo_center_screw [mm] | proposed | Execute W08 measurement/design and closure criteria in the cited audit. |
| M26 | gear_module [mm]; gear_backlash [mm]; rail_clearance [mm]; jaw_force [N] | proposed | Execute W08 measurement/design and closure criteria in the cited audit. |
| M27 | cloth_pad_friction [1]; pad_stiffness [N/mm]; pad_thickness [mm]; cloth_pullout_limit [N] | proposed | Execute W08 measurement/design and closure criteria in the cited audit. |
| M28 | assembled_reach [mm]; floor_clearance [mm]; body_collision_envelope [mm] | proposed | Execute W02 measurement/design and closure criteria in the cited audit. |
| M29 | camera_board_envelope [mm]; component_projection [mm]; bare_edge_margin [mm]; usb_keepout [mm] | proposed | Execute W05 measurement/design and closure criteria in the cited audit. |
| M30 | insulating_pad_thickness [mm]; keeper_preload [N]; board_retention [N] | proposed | Execute W05 measurement/design and closure criteria in the cited audit. |
| M31 | battery_envelope [mm]; battery_connector_envelope [mm]; battery_expansion_allowance [mm]; battery_strap_load [N] | proposed | Execute W05 measurement/design and closure criteria in the cited audit. |
| M32 | harness_diameter [mm]; wire_bend_radius [mm]; wire_length [mm]; strain_relief_load [N] | proposed | Execute W05 measurement/design and closure criteria in the cited audit. |
| M33 | motor_temperature [degC]; regulator_temperature [degC]; battery_temperature [degC]; ambient_temperature [degC]; temperature_rise [degC] | proposed | Execute W05 measurement/design and closure criteria in the cited audit. |
| M34 | camera_angle [deg]; camera_extrinsics [pose]; FOV [deg]; payload_visibility [pose_set] | proposed | Execute W10 measurement/design and closure criteria in the cited audit. |
| M35 | xy_process_error [mm]; z_process_error [mm]; hole_process_error [mm]; part_warp [mm]; print_profile [text] | proposed | Execute W06 measurement/design and closure criteria in the cited audit. |
| M36 | driver_diameter [mm]; driver_length [mm]; service_sweep [volume] | proposed | Execute W06 measurement/design and closure criteria in the cited audit. |
| C01 | surveyed_anchors [m]; attachment_vectors [m]; gravity_COM [m]; pose_rotation [rad] | proposed | Use finite attachment pose and six-component force/moment balance; do not assume level equilibrium across room. |
| C02 | unloaded_mass [kg]; maximum_payload [kg]; loaded_inertia [kg*m^2] | proposed | Execute W02 measurement/design and closure criteria in the cited audit. |
| C03 | trigger_lengths [m]; setup_position [m]; setup_rotation [rad]; home_repeatability [m] | selected for development | Preserve detached home → measured payout → supported setup-pose verification; actual trigger lengths stay null. |
| C04 | payout_lookup [m/turn]; line_slip [m]; line_extension [m] | proposed | Execute W04 measurement/design and closure criteria in the cited audit. |
| C05 | minimum_lengths [m]; maximum_lengths [m]; maximum_turns [turn]; stopping_margin [m] | proposed | Execute W04 measurement/design and closure criteria in the cited audit. |
| C06 | motor_direction [1]; step_angle [rad]; microstep_factor [1]; encoder_counts_per_rev [count/rev] | proposed | Execute W01 measurement/design and closure criteria in the cited audit. |
| C07 | run_error [count]; run_error_dwell [s]; arrival_error [count]; settling_interval [s] | implemented pending test | Bench Config thresholds are explicit and invalid intervals are rejected. Measure actual encoder/pulse/fault timing; preserve central-versus-local profile distinction. |
| C08 | axis_skew [s]; start_time [s]; clock_error [s]; segment_id [integer]; selected_transport [enum]; connector_contact_count [integer]; network_topology [text]; link_rate [bit/s]; interlock_pin_map [text]; clock_drift_limit [s/s] | proposed | Decide transport/connector/boot-safe pin resources at W01/W05 design milestones; implement and validate timing/global starts at W07. |
| C09 | global_stop_latency [s]; heartbeat_timeout [s]; session_epoch [text]; power_loss_recovery [state_machine] | proposed | Bench Config thresholds are explicit and invalid intervals are rejected. Measure actual encoder/pulse/fault timing; preserve central-versus-local profile distinction. |
| C10 | pickup_speed [m/s]; travel_speed [m/s]; cable_speed [m/s]; cable_acceleration [m/s^2]; cable_jerk [m/s^3] | proposed | Execute W07 measurement/design and closure criteria in the cited audit. |
| C11 | minimum_tensions [N]; maximum_tensions [N]; snag_tensions [N]; feasible_workspace [pose_set] | proposed | Execute W02 measurement/design and closure criteria in the cited audit. |
| C12 | roll [rad]; pitch [rad]; yaw [rad]; quiet_interval [s]; imu_alignment [rad]; IMU_bias [rad]; gyro_drift [rad/s]; dynamic_acceleration_bias [m/s^2] | selected for development | Use IMU as settled attitude acceptance; full-room leveling remains a model/architecture gate. |
| E01 | phase_current [A]; input_current [A]; driver_VREF [V]; driver_thermal_limit [degC]; regulator_thermal_limit [degC]; case_thermal_limit [degC] | proposed | Execute W05 measurement/design and closure criteria in the cited audit. |
| E02 | supply_voltage [V]; wire_ampacity [A]; fuse_current [A]; fuse_DC_voltage [V]; interrupt_rating [A]; source_protection [text]; harness_voltage_drop [V]; connector_temperature_rise [degC]; supply_fault_current [A]; fuse_time_current_curve [text]; inrush_envelope [A]; transient_voltage_envelope [V]; reverse_polarity_policy [text]; USB_isolation_policy [text] | proposed | Model actual fuse lead bends and protection coordination; compare holder rotation, external service pocket and compact part. |
| E03 | battery_capacity [Ah]; battery_discharge_limit [A]; low_voltage_cutoff [V]; runtime [s]; servo_peak_current [A] | proposed | Execute W05 measurement/design and closure criteria in the cited audit. |
| V01 | intrinsic_matrix [pixel]; lens_distortion [1]; camera_body_transform [pose]; image_camera_pose [pose]; floor_plane [m]; hamper_plane [m] | implemented pending test | Calibrated moving-camera plane geometry utility exists separately; supply real K/T_WC/undistortion and validate localization before live integration. |
| V02 | image_acquisition_time [s]; pose_age [s]; frame_age [s]; useful_frame_rate [frame/s]; pose_time_uncertainty [s] | proposed | Execute W10 measurement/design and closure criteria in the cited audit. |
| V03 | probe_distance [m]; cloth_motion_threshold [m]; identity_confidence [1]; retry_count [integer]; delivery_evidence [text] | proposed | Register background/world motion before accepting pickup probe evidence; confirm release after retreat. |
| V04 | garment_envelope [m]; usable_FOV [rad]; verification_view_set [pose_set] | proposed | Execute W10 measurement/design and closure criteria in the cited audit. |
| O01 | part_number [text]; hardware_revision [text]; quantity [integer]; order_state [enum]; receipt_state [enum]; selected_profile [enum]; project_budget [USD] | proposed | Reconcile historical BOM into configuration-specific selection/order/receipt records; no automatic purchase inference. |
