# TR10: Copyright 2025 OpenSUSI non-profit organaization
#
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ -----
"""Square-spiral inductor geometry shared by the KLayout PCell and the SPICE
model generator.

Deliberately free of `pya` so the same code can run in a plain CPython
interpreter (flow/scripts/gen_inductor_model.py) and inside KLayout
(cells/inductor.py).  Keeping one definition is what makes the extracted
SPICE parameters and the drawn layout describe the same inductor.

Layout style
------------
M2 square spiral, M1 underpass from the centre out to the second terminal.
Both terminals end in an M2 pad.  The spiral is a polyline of 90-degree
segments stroked at `width`; consecutive turns are pitched by width+spacing,
so the edge-to-edge gap is exactly `spacing`.

All coordinates are snapped to the 0.05 um DRC grid.

Units: um everywhere (except where a name says otherwise).
"""
from __future__ import annotations

import math

GRID = 0.05          # um -- 01_Basics.drc: all drawn layers on 0.050 grid
V1_SIZE = 1.4        # um -- V1.W1 is fixed at 1.4 x 1.4
V1_ENC = 1.0         # um -- V1.M1 and M2.V1 enclosure
M2_WMIN = 3.0        # um -- M2.W1
M2_SMIN = 2.0        # um -- M2.S1
M1_WMIN = 1.8        # um -- M1.W1

# A V1 landing needs width >= V1_SIZE + 2*V1_ENC, which is stricter than
# M2.W1.  The spiral trace therefore cannot be narrower than this.
TRACE_WMIN = V1_SIZE + 2 * V1_ENC      # 3.4 um

# Conductor thicknesses from libs.tech/parasitics/TR10_stackup.xml.
M2_T_UM = 0.5747126437      # Zmax 101.4195402299 - Zmin 100.8448275862
M1_T_UM = 0.3448275862      # Zmax 100.5448275862 - Zmin 100.200

# Conductivity presets, S/m.  The stackup file labels the material
# "Aluminum" but carries 58 MS/m, which is copper.  Thin-film Al is about
# 35 MS/m; bulk Al is 37.7 MS/m.  The default here is the thin-film value
# because the process is an aluminium 1 um CMOS.
METALS = {
    "al": 35.0e6,
    "cu": 58.0e6,
}
DEFAULT_METAL = "al"

V1_OHM_PER_CUT = 1.0


def sheet_ohm(metal: str, thickness_um: float) -> float:
    """Sheet resistance in ohm/sq for a metal preset and a thickness."""
    try:
        sigma = METALS[metal]
    except KeyError:
        raise ValueError(f"unknown metal {metal!r}; choose from {sorted(METALS)}")
    return 1.0 / (sigma * thickness_um * 1e-6)


def snap(v: float) -> float:
    """Snap to the 0.05 um drawing grid."""
    return round(round(v / GRID) * GRID, 6)


def spiral_points(turns: int, d_out: float, width: float, spacing: float):
    """Centreline polyline of the M2 square spiral, outer terminal first.

    The outer terminal is at (r, -r) and the winding runs up, left, down,
    right with the radius shrinking by one pitch per turn.  Each turn's
    last two segments are shortened by one pitch so the path stays
    continuous when the radius steps in.
    """
    pitch = width + spacing
    r0 = d_out / 2.0 - width / 2.0
    pts = [(r0, -r0)]
    for i in range(turns):
        ri = r0 - i * pitch
        pts.append((ri, ri))                 # up
        pts.append((-ri, ri))                # left
        pts.append((-ri, -ri + pitch))       # down
        pts.append((ri - pitch, -ri + pitch))  # right
    return [(snap(x), snap(y)) for x, y in pts]


def geometry(turns: int, d_out: float, width: float, spacing: float,
             pad: float = 20.0, pad_gap: float = 10.0,
             metal: str = DEFAULT_METAL) -> dict:
    """Full layout + electrical description of one square spiral.

    Returns a dict with the polyline, the derived diameters, the drawn
    centreline lengths and the terminal/via/pad rectangles.  Every
    rectangle is (x0, y0, x1, y1) in um.
    """
    if turns < 1:
        raise ValueError("turns must be >= 1")
    if width < TRACE_WMIN - 1e-9:
        raise ValueError(
            f"width {width} < {TRACE_WMIN} um: a V1 needs "
            f"{V1_SIZE} + 2*{V1_ENC} um of M2 to land on")
    if spacing < M2_SMIN - 1e-9:
        raise ValueError(f"spacing {spacing} < M2.S1 = {M2_SMIN} um")

    pitch = width + spacing
    r0 = d_out / 2.0 - width / 2.0
    r_in = r0 - (turns - 1) * pitch          # innermost centreline radius
    d_in = 2.0 * r_in - width                # actual hole (metal edge to edge)
    if d_in <= 0:
        raise ValueError(
            f"inner hole {d_in:.2f} um is not positive: reduce turns/width/"
            f"spacing or increase d_out")

    pts = spiral_points(turns, d_out, width, spacing)

    # Centreline length: per turn 2*ri + 2*ri + (2*ri-pitch) + (2*ri-pitch).
    length_m2 = 0.0
    for i in range(turns):
        ri = r0 - i * pitch
        length_m2 += 8.0 * ri - 2.0 * pitch

    # ---- inner terminal: V1 in the middle of the last (innermost) segment
    (x_a, y_a), (x_b, y_b) = pts[-2], pts[-1]
    x_via = snap(0.5 * (x_a + x_b))
    y_via = y_a                              # last segment is horizontal
    # ---- outer terminal: the spiral starts at (r0, -r0) heading up, so the
    # free end continues downward into its pad.
    x_out, y_out = pts[0]

    pad = snap(pad) if pad > 0 else 0.0
    pad_gap = snap(pad_gap)
    if pad > 0:
        y_pad = snap(-(d_out / 2.0 + pad_gap + pad / 2.0))
        half = pad / 2.0
        # Keep the outer pad inside the d_out envelope so the cell bbox stays
        # exactly d_out wide; the stub from the spiral end lands on it.
        x_pad = snap(min(x_out, d_out / 2.0 - half))
        pad_p = (snap(x_pad - half), snap(y_pad - half),
                 snap(x_pad + half), snap(y_pad + half))
        pad_n = (snap(x_via - half), snap(y_pad - half),
                 snap(x_via + half), snap(y_pad + half))
        # M2 stub from the outer spiral end down into pad_p.
        stub_p = (snap(x_out - width / 2.0), snap(pad_p[3]),
                  snap(x_out + width / 2.0), snap(y_out))
        # The stub must actually reach the pad: it starts at the pad's top
        # edge, which is pad_gap below the spiral's outer edge.
        assert stub_p[1] == pad_p[3], (stub_p, pad_p)
        # M1 underpass: centre -> below the spiral -> up into pad_n.
        up_len = 2 * V1_ENC + V1_SIZE / 2.0   # extend past the via
        m1_x0 = snap(x_via - TRACE_WMIN / 2.0)
        m1_x1 = snap(x_via + TRACE_WMIN / 2.0)
        m1_y0 = snap(y_pad - up_len)
        m1_y1 = snap(y_via + up_len)
        underpass = (m1_x0, m1_y0, m1_x1, m1_y1)
        length_m1 = m1_y1 - m1_y0
    else:
        pad_p = pad_n = stub_p = underpass = None
        y_pad = snap(-(d_out / 2.0 + pad_gap))
        length_m1 = snap(y_via - y_pad)

    via_inner = (snap(x_via - V1_SIZE / 2.0), snap(y_via - V1_SIZE / 2.0),
                 snap(x_via + V1_SIZE / 2.0), snap(y_via + V1_SIZE / 2.0))
    via_outer = None
    if pad > 0:
        via_outer = (snap(x_via - V1_SIZE / 2.0), snap(y_pad - V1_SIZE / 2.0),
                     snap(x_via + V1_SIZE / 2.0), snap(y_pad + V1_SIZE / 2.0))

    rsh_m2 = sheet_ohm(metal, M2_T_UM)
    rsh_m1 = sheet_ohm(metal, M1_T_UM)
    r_dc_metal = (rsh_m2 * (length_m2 + (stub_p[3] - stub_p[1] if stub_p else 0.0))
                  / width)
    r_dc_metal += rsh_m1 * length_m1 / TRACE_WMIN
    n_via = 2 if via_outer else 1
    r_dc = r_dc_metal + n_via * V1_OHM_PER_CUT

    return {
        "turns": turns,
        "d_out_um": d_out,
        "d_in_um": d_in,
        "d_avg_um": 0.5 * (d_out + d_in),
        "rho": (d_out - d_in) / (d_out + d_in),
        "width_um": width,
        "spacing_um": spacing,
        "points": pts,
        "length_m2_um": length_m2,
        "length_m1_um": length_m1,
        "r_dc_ohm": r_dc,
        "r_dc_metal_ohm": r_dc_metal,
        "n_via": n_via,
        "metal": metal,
        "rsh_m2_ohm_sq": rsh_m2,
        "rsh_m1_ohm_sq": rsh_m1,
        "pad_um": pad,
        "pad_gap_um": pad_gap,
        "pad_p": pad_p,
        "pad_n": pad_n,
        "stub_p": stub_p,
        "underpass": underpass,
        "via_inner": via_inner,
        "via_outer": via_outer,
        "bbox": (-d_out / 2.0, -d_out / 2.0, d_out / 2.0, d_out / 2.0),
    }


def wheeler_nh(turns: int, d_out: float, width: float, spacing: float) -> float:
    """Wheeler square-spiral inductance, nH.

    L = 2.34 * mu0 * n^2 * d_avg / (1 + 2.75 * rho)
    with d_avg and rho taken from the *drawn* inner hole so the number
    matches the layout, not a textbook approximation of it.
    """
    g = geometry(turns, d_out, width, spacing, pad=0.0)
    mu0 = 4e-7 * math.pi
    l_h = (2.34 * mu0 * turns * turns * (g["d_avg_um"] * 1e-6)
           / (1.0 + 2.75 * g["rho"]))
    return l_h * 1e9
