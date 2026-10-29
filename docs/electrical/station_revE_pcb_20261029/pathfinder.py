"""Negotiated-congestion (PathFinder-style) router, two copper layers with vias.  Own code.

Hard obstacles: pads (THT pads on both layers, SMD pads on their layer), NPTH holes, board edge.
Soft obstacles: other nets' tracks and vias.  Every net is routed; a cell where a track would come
closer than TRACK_CLR to another net's copper costs extra (a present-congestion factor that grows
every iteration, plus an accumulated history cost).  Nets in conflict are ripped up and re-routed
until no conflict remains.  The result is then checked independently by KiCad's DRC.

Layer 0 = F.Cu (top), layer 1 = B.Cu (bottom).
"""
import heapq
import math

import numpy as np
from scipy.ndimage import distance_transform_edt

from maze_router import DIRS, NO_DIR, SQ2, turn_cost, simplify

TRACK_CLR = 0.5          # track/via to other-net track/via clearance (mm)
VIA_R = 0.5              # via pad radius (1.0 mm via, 0.5 mm drill)
NL = 2


class Net:
    def __init__(self, name, hw, pins):
        self.name, self.hw = name, hw
        self.pins = pins          # [(ref_pin, x, y, cell, layers)]  layers: tuple of allowed layers
        self.paths = []           # [(layer, [cell, ...])]
        self.vias = []            # [cell]


class Negotiator:
    def __init__(self, grid, nets, hard_free, via_ok, via_cost=14.0, margin=0.08):
        self.g = grid
        self.nets = {n.name: n for n in nets}
        self.hard_free = hard_free      # name -> [bytearray per layer]
        self.via_ok = via_ok            # name -> bytearray
        self.via_cost = via_cost
        self.margin = margin
        self.hist = np.zeros((NL, grid.ny, grid.nx))
        self.D = {}                     # name -> [distance map per layer] (mm to its centreline)
        self.DV = {}                    # name -> distance map to its vias
        self.center = {}
        self.vmask = {}

    def _update_maps(self, name):
        g, n = self.g, self.nets[name]
        c = np.zeros((NL, g.ny, g.nx), dtype=bool)
        v = np.zeros((g.ny, g.nx), dtype=bool)
        for layer, chain in n.paths:
            for k in chain:
                c[layer, k // g.nx, k % g.nx] = True
        for k in n.vias:
            v[k // g.nx, k % g.nx] = True
        self.center[name], self.vmask[name] = c, v
        big = np.full((g.ny, g.nx), 1e9)
        self.D[name] = [distance_transform_edt(~c[l]) * g.pitch if c[l].any() else big for l in range(NL)]
        self.DV[name] = distance_transform_edt(~v) * g.pitch if v.any() else big

    def occupancy(self, name, hw, layer):
        occ = np.zeros((self.g.ny, self.g.nx), dtype=np.int16)
        lim = hw + TRACK_CLR + self.margin
        for m, net in self.nets.items():
            if m == name or m not in self.D:
                continue
            occ += self.D[m][layer] < lim + net.hw
            occ += self.DV[m] < lim + VIA_R
        return occ

    def route(self, name, pres):
        g, n = self.g, self.nets[name]
        N = g.nx * g.ny
        cost = []
        for l in range(NL):
            cost += (1.0 + self.hist[l] + pres * self.occupancy(name, n.hw, l)).ravel().tolist()
        occv = sum(self.occupancy(name, VIA_R, l) for l in range(NL))
        vcost = (self.via_cost + pres * 4.0 * occv + self.hist.sum(axis=0)).ravel().tolist()
        free = self.hard_free[name][0] + self.hard_free[name][1]      # flat, layer-major
        vok = self.via_ok[name]
        pins = sorted(n.pins)
        tree = {l * N + pins[0][3] for l in pins[0][4]}
        done, todo = [pins[0]], pins[1:]
        n.paths, n.vias = [], []
        while todo:
            todo.sort(key=lambda t: min(math.hypot(t[1] - c[1], t[2] - c[2]) for c in done))
            tgt = todo.pop(0)
            goals = {l * N + tgt[3] for l in tgt[4]}
            res = self._astar(free, cost, vok, vcost, tree, goals, tgt[3])
            if res is None:
                return False
            chain_l, chain = None, []
            for node, kind in res:
                l, c = divmod(node, N)
                if kind == "v":
                    if len(chain) > 1:
                        n.paths.append((chain_l, chain))
                    n.vias.append(c)
                    chain_l, chain = l, [c]
                else:
                    if chain_l is None:
                        chain_l = l
                    chain.append(c)
                tree.add(node)
            if len(chain) > 1:
                n.paths.append((chain_l, chain))
            done.append(tgt)
            # a via cell is usable on both layers by later branches
            for c in n.vias:
                tree.add(c)
                tree.add(N + c)
        self._update_maps(name)
        return True

    def _astar(self, free, cost, vok, vcost, sources, goals, goal_cell):
        g = self.g
        nx, ny = g.nx, g.ny
        N = nx * ny
        gi, gj = goal_cell % nx, goal_cell // nx

        def h(c):
            i, j = c % nx, c // nx
            dx, dy = abs(i - gi), abs(j - gj)
            return (dx + dy) + (SQ2 - 2) * min(dx, dy)

        best, came, heap = {}, {}, []
        for s in sources:
            st = s * 9 + NO_DIR
            best[st] = 0.0
            came[st] = None
            heapq.heappush(heap, (h(s % N), 0.0, st))
        while heap:
            f, gc, st = heapq.heappop(heap)
            if gc > best.get(st, 1e18):
                continue
            node, d = divmod(st, 9)
            if node in goals:
                out = []
                while st is not None:
                    prev = came[st]
                    if prev is None:
                        out.append((st // 9, "s"))
                        break
                    pst, kind = prev
                    out.append((st // 9, kind))
                    st = pst
                out.reverse()
                return out
            l, c = divmod(node, N)
            base = l * N
            i, j = c % nx, c // nx
            for nd, (di, dj) in enumerate(DIRS):
                tc = turn_cost(d, nd)
                if tc is None:
                    continue
                ni, nj = i + di, j + dj
                if ni < 0 or nj < 0 or ni >= nx or nj >= ny:
                    continue
                nb = base + nj * nx + ni
                if not free[nb]:
                    continue
                if di and dj:
                    if not free[base + j * nx + ni] or not free[base + nj * nx + i]:
                        continue
                    step = SQ2
                else:
                    step = 1.0
                ng = gc + step * cost[nb] + tc
                nst = nb * 9 + nd
                if ng < best.get(nst, 1e18):
                    best[nst] = ng
                    came[nst] = (st, "w")
                    heapq.heappush(heap, (ng + h(nb - base), ng, nst))
            if vok[c]:
                nb = (1 - l) * N + c
                if free[nb]:
                    ng = gc + vcost[c]
                    nst = nb * 9 + NO_DIR
                    if ng < best.get(nst, 1e18):
                        best[nst] = ng
                        came[nst] = (st, "v")
                        heapq.heappush(heap, (ng + h(c), ng, nst))
        return None

    def conflicts(self):
        out = {}
        cells = np.zeros((NL, self.g.ny, self.g.nx), dtype=bool)
        for name, n in self.nets.items():
            if name not in self.center:
                continue
            k = 0
            for l in range(NL):
                bad = (self.occupancy(name, n.hw, l) > 0) & self.center[name][l]
                k += int(bad.sum())
                cells[l] |= bad
            vm = self.vmask[name]
            if vm.any():
                occv = sum(self.occupancy(name, VIA_R, l) for l in range(NL))
                badv = (occv > 0) & vm
                k += int(badv.sum())
                cells[:, badv] = True
            if k:
                out[name] = k
        return out, cells

    def run(self, order, iters=40, pres0=0.6, pres_mul=1.5, hist_add=0.6, log=print):
        for name in order:
            if not self.route(name, 0.0):
                log(f"   {name}: no route (hard obstacles)")
        pres = pres0
        for it in range(iters):
            conf, cells = self.conflicts()
            nv = sum(len(n.vias) for n in self.nets.values())
            log(f"   iter {it:2d}: conflicts {sum(conf.values()):4d} in {sorted(conf)}  vias {nv}")
            if not conf:
                return True
            self.hist[cells] += hist_add
            for name in sorted(conf, key=lambda k: -conf[k]):
                self.route(name, pres)
            pres *= pres_mul
        return not self.conflicts()[0]

    def tracks(self, width_of, exact):
        g = self.g
        out = []
        for name, n in self.nets.items():
            for layer, chain in n.paths:
                pts = simplify([(k % g.nx, k // g.nx) for k in chain])
                xy = [g.xy(i, j) for i, j in pts]
                for end in (0, -1):
                    k = g.idx(*pts[end])
                    if k in exact:
                        ex, ey = exact[k]
                        if math.hypot(ex - xy[end][0], ey - xy[end][1]) > 1e-6:
                            if end == 0:
                                xy.insert(0, (ex, ey))
                            else:
                                xy.append((ex, ey))
                for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
                    if math.hypot(x2 - x1, y2 - y1) > 1e-6:
                        out.append((name, layer, round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4),
                                    width_of(name)))
        return out

    def via_list(self):
        g = self.g
        return [(name, *g.xy(k % g.nx, k // g.nx)) for name, n in self.nets.items() for k in n.vias]
