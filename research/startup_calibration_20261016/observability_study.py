"""Offline synthetic sensitivity study. NO hardware, network, or motion interface.

Run from any directory: python observability_study.py
Writes synthetic_results.json beside this file. These are NOT robot test results.
Assumes point attachment, straight taut cables, fixed payout scale, independent
Gaussian position/payout noise, and bounded rough anchor estimates.
"""
import json
from pathlib import Path
import numpy as np
import scipy
from scipy.optimize import least_squares

SEED = 20261016
ANCHORS = np.array([[-1.6764, -1.3716, 2.7432], [1.6764, -1.3716, 2.7432],
                    [1.6764, 1.3716, 2.7432], [-1.6764, 1.3716, 2.7432]])
CENTER = np.array([0., 0., .6])

def run():
    rng = np.random.default_rng(SEED)
    results = {}
    for name, halfspan in [('small_3d', [.025, .025, .025]),
                           ('medium_3d', [.15, .15, .10]),
                           ('larger_3d', [.40, .40, .25])]:
        anchor_errors, heldout_errors, fit_errors, conditions = [], [], [], []
        for _ in range(30):
            poses = CENTER + rng.uniform(-1, 1, (60, 3)) * np.array(halfspan)
            measured = poses + rng.normal(0, .002, poses.shape)
            witness = CENTER + rng.uniform(-1, 1, (100, 3)) * [.6, .6, .3]
            for anchor in ANCHORS:
                l0 = np.linalg.norm(anchor - CENTER)
                delta = np.linalg.norm(poses - anchor, axis=1) - l0
                delta += rng.normal(0, .0003, len(delta))
                prior = anchor + rng.uniform(-.1, .1, 3)
                x0 = np.r_[prior, np.linalg.norm(prior-CENTER)]
                lo, hi = np.r_[prior-.3, l0-.75], np.r_[prior+.3, l0+.75]
                def residual(x):
                    return np.linalg.norm(measured-x[:3], axis=1)-x[3]-delta
                fit = least_squares(residual, x0, bounds=(lo, hi),
                                    loss='soft_l1', f_scale=.003,
                                    xtol=1e-10, ftol=1e-10, gtol=1e-10)
                anchor_errors.append(np.linalg.norm(fit.x[:3]-anchor))
                predicted_delta = np.linalg.norm(witness-fit.x[:3], axis=1)-fit.x[3]
                true_delta = np.linalg.norm(witness-anchor, axis=1)-l0
                heldout_errors.append(np.sqrt(np.mean((predicted_delta-true_delta)**2)))
                fit_errors.append(np.sqrt(np.mean(residual(fit.x)**2)))
                # Unweighted geometric Jacobian, metres for all four parameters.
                d = anchor-poses
                J = np.c_[d/np.linalg.norm(d, axis=1)[:, None], -np.ones(len(poses))]
                conditions.append(float(np.linalg.cond(J)))
        results[name] = {
            'sample_box_full_width_m': (2*np.array(halfspan)).tolist(),
            'median_anchor_error_mm': float(np.median(anchor_errors)*1000),
            'p95_anchor_error_mm': float(np.percentile(anchor_errors,95)*1000),
            'median_fit_residual_rms_mm': float(np.median(fit_errors)*1000),
            'median_heldout_cable_delta_rms_mm': float(np.median(heldout_errors)*1000),
            'p95_heldout_cable_delta_rms_mm': float(np.percentile(heldout_errors,95)*1000),
            'median_geometric_jacobian_condition': float(np.median(conditions))}
    output = {
        'status': 'SYNTHETIC ONLY; not a camera, startup, or robot validation',
        'seed': SEED, 'numpy': np.__version__, 'scipy': scipy.__version__,
        'assumptions': {
            'room_m': [3.3528,2.7432,2.7432], 'reference_attachment_height_m': .6,
            'trials_per_case': 30, 'poses_per_trial': 60, 'anchors_per_trial': 4,
            'position_noise_std_per_axis_m': .002, 'payout_noise_std_m': .0003,
            'prior_anchor_error_uniform_halfwidth_m': .1,
            'fit_anchor_bounds_around_prior_m': .3,
            'witness_box_full_width_m': [1.2,1.2,.6],
            'not_modeled': ['camera bias/pose ambiguity','tension and slack','collisions',
                           'spool radius change','motor dynamics','suspension orientation',
                           'camera field of view','network latency']},
        'results': results}
    # A noiseless algebra check, independent of any mechanical feasibility claim.
    p = CENTER + rng.uniform(-.4,.4,(60,3))
    a = ANCHORS[0]; l0=np.linalg.norm(a-CENTER)
    dl=np.linalg.norm(p-a,axis=1)-l0
    check=least_squares(lambda x: np.linalg.norm(p-x[:3],axis=1)-x[3]-dl,
                        np.r_[a+[.05,-.03,.02],l0+.02],gtol=1e-13,ftol=1e-13,xtol=1e-13)
    assert np.linalg.norm(check.x[:3]-a)<1e-6
    output['noiseless_fit_anchor_error_m']=float(np.linalg.norm(check.x[:3]-a))
    target=Path(__file__).with_name('synthetic_results.json')
    target.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__ == '__main__':
    run()
