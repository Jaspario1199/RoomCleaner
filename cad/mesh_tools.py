"""
Small mesh helpers (no trimesh dependency): tessellate CadQuery shapes,
render shaded PNGs with matplotlib, and cast rays against triangle meshes.
"""

from __future__ import annotations

import numpy as np
import cadquery as cq


def tessellate(shape, tol: float = 0.5, ang: float = 0.4):
    """Return (V[n,3], F[m,3]) for a cq.Shape / Workplane."""
    if isinstance(shape, cq.Workplane):
        shape = shape.val()
    verts, tris = shape.tessellate(tol, ang)
    V = np.array([[v.x, v.y, v.z] for v in verts], dtype=float)
    F = np.array(tris, dtype=int).reshape(-1, 3)
    return V, F


def render(meshes, out_png, elev, azim, title="", bounds=None, size=(7.5, 6.5), dpi=130,
           light=(0.4, -0.5, 0.75), up="z", ortho=True):
    """meshes: list of (V, F, rgb, alpha).  `up` selects which world axis is vertical
    on screen ('z' default matplotlib; 'y' swaps so +Y points up)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def T(V):
        # map world (x, y, z) -> plot (X, Y, Z) so the chosen up axis is plot Z
        if up == "y":
            return np.stack([V[:, 0], -V[:, 2], V[:, 1]], axis=1)
        return V

    fig = plt.figure(figsize=size)
    ax = fig.add_subplot(111, projection="3d")
    if ortho:
        ax.set_proj_type("ortho")
    lt = np.array(light) / np.linalg.norm(light)
    allv = []
    for V, F, rgb, alpha in meshes:
        P = T(V)
        tri = P[F]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nn = np.linalg.norm(n, axis=1)
        nn[nn == 0] = 1
        n = n / nn[:, None]
        # light rotates with the camera so every view is lit from the viewer's side
        az, el = np.radians(azim), np.radians(elev)
        cam = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        right = np.cross([0, 0, 1], cam)
        right = right / (np.linalg.norm(right) or 1)
        upv = np.cross(cam, right)
        L = 0.55 * cam + 0.45 * upv + 0.25 * right
        shade = 0.30 + 0.70 * np.abs(n @ (L / np.linalg.norm(L)))
        cols = np.clip(shade[:, None] * np.array(rgb)[None, :], 0, 1)
        cols = np.concatenate([cols, np.full((len(cols), 1), alpha)], axis=1)
        coll = Poly3DCollection(tri, facecolors=cols, edgecolors=(0, 0, 0, 0.0), linewidths=0)
        ax.add_collection3d(coll)
        allv.append(P)
    allv = np.concatenate(allv)
    if bounds is None:
        lo, hi = allv.min(axis=0), allv.max(axis=0)
    else:
        lo, hi = np.array(bounds[0], float), np.array(bounds[1], float)
        lo, hi = T(np.array([lo]))[0], T(np.array([hi]))[0]
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
    ctr = (lo + hi) / 2
    r = (hi - lo).max() / 2 or 1.0
    ax.set_xlim(ctr[0] - r, ctr[0] + r)
    ax.set_ylim(ctr[1] - r, ctr[1] + r)
    ax.set_zlim(ctr[2] - r, ctr[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out_png


def ray_mesh_first_hit(origin, dirs, V, F, chunk=4000):
    """Moller-Trumbore. origin (3,), dirs (n,3).  Returns t (n,) of the nearest
    hit with t > 1e-6, or inf."""
    origin = np.asarray(origin, float)
    dirs = np.asarray(dirs, float)
    tri = V[F]
    v0 = tri[:, 0]
    e1 = tri[:, 1] - v0
    e2 = tri[:, 2] - v0
    best = np.full(len(dirs), np.inf)
    # cheap AABB reject of the whole mesh per ray via slab test
    lo, hi = V.min(axis=0), V.max(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / dirs
        t1 = (lo - origin) * inv
        t2 = (hi - origin) * inv
    tmin = np.nanmax(np.minimum(t1, t2), axis=1)
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    # rays parallel to a slab with origin outside it
    par = dirs == 0
    outside = ((origin < lo) | (origin > hi))[None, :] & par
    cand = np.where((tmax >= np.maximum(tmin, 0)) & ~outside.any(axis=1))[0]
    for k in range(0, len(cand), 200):
        idx = cand[k:k + 200]
        d = dirs[idx]                                  # (r,3)
        for s in range(0, len(F), chunk):
            a = v0[s:s + chunk]
            b1 = e1[s:s + chunk]
            b2 = e2[s:s + chunk]
            # (r, m)
            pv = np.cross(d[:, None, :], b2[None, :, :])
            det = np.einsum("mj,rmj->rm", b1, pv)
            ok = np.abs(det) > 1e-12
            invd = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
            tv = origin[None, None, :] - a[None, :, :]
            u = np.einsum("rmj,rmj->rm", np.broadcast_to(tv, pv.shape), pv) * invd
            qv = np.cross(np.broadcast_to(tv, pv.shape), b1[None, :, :])
            v = np.einsum("rj,rmj->rm", d, qv) * invd
            t = np.einsum("mj,rmj->rm", b2, qv) * invd
            hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
            t = np.where(hit, t, np.inf).min(axis=1)
            best[idx] = np.minimum(best[idx], t)
    return best
