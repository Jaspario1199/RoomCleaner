"""Render the slide-4 equations as PNGs (matplotlib mathtext, STIX) so subscripts and fractions are typeset.
Run: /usr/bin/python3 make_equations.py  -> fig/eq_a.png, fig/eq_b.png, fig/eq_c.png, fig/eq_d.png (homing slide)"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

plt.rcParams["mathtext.fontset"] = "stix"
plt.rcParams["font.family"] = "STIXGeneral"
OUT = Path(__file__).parent / "fig"
OUT.mkdir(exist_ok=True)

WID = {"eq_a": 1.7, "eq_d": 3.4}
EQ = {
    "eq_a": [r"$L_i = \left\| \mathbf{a}_i - \mathbf{p} \right\|$",
             r"$\mathbf{a}_i$ anchor, $\mathbf{p}$ claw"],
    "eq_b": [r"$I = \dfrac{V_{\mathrm{ref}}}{8\,R_s}$     $\tau_{\mathrm{hold}} = \tau_{\mathrm{rated}}\,\dfrac{I}{I_{\mathrm{rated}}}$",
             r"$\tau_{\mathrm{run}} \approx 0.7\,\tau_{\mathrm{hold}}$ (assumed)     $F = \dfrac{\tau}{r}$"],
    "eq_c": [r"$T = \dfrac{W}{4\,\sin\varphi}$     $\sin\varphi = \dfrac{d}{\sqrt{d^2 + D_h^2}}$"],
    "eq_d": [r"reachable$(\mathbf{p})\;\Leftrightarrow\;\left\| \mathbf{a}_i - \mathbf{p} \right\| \geq L_{i,\mathrm{home}}$  for every $i$"],
}
for name, lines in EQ.items():
    fig = plt.figure(figsize=(WID.get(name, 3.2), 0.42 * len(lines) + 0.2), dpi=400)
    y = 1.0
    step = 1.0 / len(lines)
    for t in lines:
        fig.text(0.02, y - step / 2, t, fontsize=11, va="center", ha="left")
        y -= step
    fig.savefig(OUT / f"{name}.png", dpi=400, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    plt.close(fig)
    print("wrote", OUT / f"{name}.png")
