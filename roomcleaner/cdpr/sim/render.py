"""Minimal image synthesis of what the claw camera sees (for perception tests).

Not photorealistic: a neutral textured floor, saturated-colour square "garments"
projected exactly through the camera model from the TRUE claw pose, the held
garment as a large patch at the jaw, and fixed dark finger bars at the jaw
(drawn in both the empty and the held case so the empty reference is not
trivially uniform).
"""
from __future__ import annotations

import colorsys

import cv2
import numpy as np

ITEM_SIDE_M = 0.18
HELD_SIDE_M = 0.12
FINGER_OFFSETS_BODY_M = ((-0.045, 0.0), (0.045, 0.0), (0.0, 0.05))     # (x, y) about the jaw point
FINGER_SIZE_M = (0.012, 0.05)                                          # (width, length) of each bar
FINGER_BGR = (28, 28, 32)


def item_bgr(index: int) -> tuple:
    """Saturated colour per item (golden-ratio hue spacing so neighbours differ)."""
    h = (0.07 + 0.618034 * index) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.85, 0.9)
    return int(b * 255), int(g * 255), int(r * 255)


def _fill(img, camera, pts_cam, color):
    pts_cam = np.asarray(pts_cam, float)
    if np.any(pts_cam[:, 2] <= 0.03):
        return
    uv = camera.project(pts_cam)
    if not np.all(np.isfinite(uv)) or np.abs(uv).max() > 1e5:
        return
    cv2.fillPoly(img, [np.round(uv).astype(np.int32).reshape(-1, 1, 2)], color, lineType=cv2.LINE_AA)


def _square(center_xy, z, side, yaw=0.0):
    h = side / 2
    c, s = np.cos(yaw), np.sin(yaw)
    R = np.array([[c, -s], [s, c]])
    corners = np.array([[-h, -h], [h, -h], [h, h], [-h, h]]) @ R.T + np.asarray(center_xy, float)
    return np.c_[corners, np.full(4, z)]


def render_claw_view(world, camera, T_B_C, *, floor_bgr=(150, 150, 150), noise=2.0, rng=None):
    """BGR uint8 image of the claw camera at the world's true claw pose."""
    rng = np.random.default_rng(0) if rng is None else rng
    w, h = camera.image_size
    # floor: base grey + low-frequency blotches + fine grain
    low = rng.normal(0.0, 5.0, (max(h // 40, 2), max(w // 40, 2)))
    tex = cv2.resize(low, (w, h), interpolation=cv2.INTER_CUBIC)
    img = np.empty((h, w, 3), np.float32)
    img[:] = np.asarray(floor_bgr, np.float32)
    img += tex[:, :, None].astype(np.float32)
    if noise > 0:
        img += rng.normal(0.0, noise, (h, w, 1)).astype(np.float32)
    img = np.clip(img, 0, 255).astype(np.uint8)

    T_R_B = np.eye(4)
    T_R_B[:3, :3] = world.R
    T_R_B[:3, 3] = world.p
    T_C_R = np.linalg.inv(T_R_B @ np.asarray(T_B_C, float))

    def to_cam(p_R):
        return (np.asarray(p_R, float) @ T_C_R[:3, :3].T) + T_C_R[:3, 3]

    # floor garments and garments dropped in the hamper (at their last drop location)
    for k, it in enumerate(world.items):
        if it["state"] == "floor":
            _fill(img, camera, to_cam(_square(it["xy"], it["height"], ITEM_SIDE_M)), item_bgr(k))
        elif it["state"] == "hamper" and it.get("last_drop") is not None:
            _fill(img, camera, to_cam(_square(it["last_drop"], it["height"], ITEM_SIDE_M)), item_bgr(k))

    # jaw geometry in the body frame
    low_b = np.asarray(world.cfg.claw.lowest_point_body_m, float)
    T_C_B = np.linalg.inv(np.asarray(T_B_C, float))

    def body_to_cam(p_B):
        return np.asarray(p_B, float) @ T_C_B[:3, :3].T + T_C_B[:3, 3]

    if world.held is not None:
        k = next(i for i, it in enumerate(world.items) if it is world.held)
        _fill(img, camera, body_to_cam(_square(low_b[:2], low_b[2], HELD_SIDE_M)), item_bgr(k))

    # fixed dark fingers at the jaw (present whether or not something is held)
    fw, fl = FINGER_SIZE_M
    for ox, oy in FINGER_OFFSETS_BODY_M:
        c = low_b[:2] + [ox, oy]
        quad = np.array([[-fw / 2, -fl / 2], [fw / 2, -fl / 2], [fw / 2, fl / 2], [-fw / 2, fl / 2]])
        if abs(ox) < 1e-9:                       # the rear finger lies along x
            quad = quad[:, ::-1]
        _fill(img, camera, body_to_cam(np.c_[quad + c, np.full(4, low_b[2])]), FINGER_BGR)
    return img
