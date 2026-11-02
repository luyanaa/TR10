#!/usr/bin/env python3
"""Generate TR10.rcx_rules (OpenRCX extraction rules) for the TR10 stack.

The rules are derived from the routing techlef
(libs.ref/TR10_fd_sc/techlef/TR10_tech.tlef):

    layer   width (um)   spacing (um)   Rs (ohm/sq)   CPERSQDIST (fF/um^2)
    M1      1.8          1.4            0.050         3.5e-05
    M2      3.0          2.0            0.030         1.75e-05

EDGECAPACITANCE is 5.0e-05 fF/um on both layers.

Capacitance model (engineering values consistent with the geometry JSON and
the parasitics stackup):

    area      CAREA    = CPERSQDIST per layer
    fringe    CFRINGE  = EDGECAPACITANCE (5.0e-05 fF/um)
    coupling  CC(s)    = eps0 * eps_r * t / s   (sidewall, per um of length)
                8.854e-6 * 3.9 * t / s  fF/um

Metal thicknesses come from TR10_stackup.xml, which back-derives them from
RPERSQ at 58 MS/m conductivity:

    M1: t = 1 / (58e6 * 0.050) um ~= 0.3448 um
    M2: t = 1 / (58e6 * 0.030) um ~= 0.5747 um

Usage:
    python3 gen_rcx_rules.py > TR10.rcx_rules      (or with an output path)
"""
import sys

N_LAYERS = 2
T = {1: 1.0 / (58e6 * 0.050), 2: 1.0 / (58e6 * 0.030)}   # um (from stackup)
LEF_RPERSQ = {1: 0.050, 2: 0.030}                        # ohm/sq
CAREA = {1: 3.5e-05, 2: 1.75e-05}                        # fF/um^2
CFRINGE = 5.0e-05                                        # fF/um
EPS0 = 8.854e-6                                          # fF/um
EPSR = 3.9

WIDTHS = {1: [1.8], 2: [3.0]}                            # routing width (um)
SPACINGS = {
    1: [1.4, 2.8, 3.5, 4.2, 4.9, 5.6, 6.3, 7.0, 8.4, 11.2, 14.0, 16.8],
    2: [2.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 16.0, 20.0, 24.0],
}
# neighbour-context width grid for the RESOVER table (col0 = context width)
RESWIDTHS = {
    1: [1.8, 3.6, 5.4, 7.2, 9.0, 10.8, 14.4, 18.0],
    2: [3.0, 6.0, 9.0, 12.0, 15.0, 18.0, 24.0, 30.0],
}


def coupling(layer, s):
    """Sidewall capacitance to a neighbour at spacing s (fF per um)."""
    return EPS0 * EPSR * T[layer] / s


def r_per_nm(layer, w):
    """Resistance per nm of a wire of width w (ohm/nm)."""
    return LEF_RPERSQ[layer] / (w * 1000.0)


def dist_block(count, width, rows):
    out = ["DIST count %d width %g" % (count, width)]
    out += [" ".join("%g" % v if i < 2 else "%.6g" % v for i, v in enumerate(r)) for r in rows]
    out.append("END DIST")
    return out


def width_table(out, m):
    out.append("WIDTH Table %d entries: %s" % (len(WIDTHS[m]), " ".join("%g" % w for w in WIDTHS[m])))
    out.append("")


def emit(out):
    # OpenRCX grammar (extRCmodel.cpp readRules{,Over,Under,OverUnder,res2}).
    # With a single width-table entry each section has ONE DIST block per
    # context.  RESOVER rows are (neighbour_width, spacing, 0, res); cap rows
    # are (spacing, cc, cfringe, res).
    out.append("Extraction Rules for OpenRCX")
    out.append("")
    out.append("DIAGMODEL ON")
    out.append("")
    out.append("LayerCount %d" % N_LAYERS)
    out.append("DensityRate 1  0")
    out.append("")
    out.append("DensityModel 0")
    out.append("")

    for m in range(1, N_LAYERS + 1):
        w0 = WIDTHS[m][0]

        # ---- RESOVER k : resistance with layer k below (0 = substrate) ----
        out.append("Metal %d RESOVER" % m)
        width_table(out, m)
        for k in range(0, m):
            out.append("Metal %d RESOVER %d" % (m, k))
            if k == 0:
                rows = []
                for a in [0.0] + RESWIDTHS[m]:
                    for b in RESWIDTHS[m]:
                        if a > 0 and b < a:
                            continue
                        # res grows slightly as the context wire narrows /
                        # spacing shrinks, giving the parser distinct values
                        # to index while staying centred on RPERSQ/w.
                        res = r_per_nm(m, w0) * (1.0 + 0.15 * a / (b + 0.5))
                        rows.append((a, b, 0.0, res))
                out += dist_block(len(rows), w0, rows)
            else:
                # a metal directly below shields resistance -> flat substrate
                # value, single row.
                out += dist_block(1, w0, [(0.0, 0.0, 0.0, r_per_nm(m, w0))])
        out.append("")

        # ---- OVER k : coupling to layer k below (0 = substrate) ----
        out.append("Metal %d OVER" % m)
        width_table(out, m)
        for k in range(0, m):
            out.append("Metal %d OVER %d" % (m, k))
            rows = []
            for s in SPACINGS[m]:
                cc = CAREA[m] if k == 0 else coupling(m, s)
                rows.append((s, cc, CAREA[m], r_per_nm(m, w0)))
            out += dist_block(len(rows), w0, rows)
        out.append("")

        # ---- UNDER j : coupling to layer j above ----
        if m < N_LAYERS:
            out.append("Metal %d UNDER" % m)
            width_table(out, m)
            for j in range(m + 1, N_LAYERS + 1):
                out.append("Metal %d UNDER %d" % (m, j))
                rows = [(s, coupling(m, s), CAREA[m], r_per_nm(m, w0)) for s in SPACINGS[m]]
                out += dist_block(len(rows), w0, rows)
            out.append("")

            out.append("Metal %d DIAGUNDER" % m)
            width_table(out, m)
            for j in range(m + 1, N_LAYERS + 1):
                out.append("Metal %d DIAGUNDER %d" % (m, j))
                rows = [(s, coupling(m, s) * 0.5, CAREA[m], r_per_nm(m, w0)) for s in SPACINGS[m]]
                out += dist_block(len(rows), w0, rows)
            out.append("")

        # ---- OVERUNDER : interior metal coupling to a neighbour below AND a
        # neighbour above.  Required for 1 < m < N_LAYERS; without it the
        # parser leaves _capOverUnder[m] null and calcMinMaxRC segfaults.
        # TR10 is a 2-metal stack so this section never triggers, but keep the
        # logic for forward compatibility.
        if m > 1 and m < N_LAYERS:
            out.append("Metal %d OVERUNDER" % m)
            width_table(out, m)
            for u in range(1, m):
                for o in range(m + 1, N_LAYERS + 1):
                    out.append("Metal %d OVER %d UNDER %d" % (m, u, o))
                    rows = [(s, coupling(m, s), CAREA[m], r_per_nm(m, w0)) for s in SPACINGS[m]]
                    out += dist_block(len(rows), w0, rows)
                    out.append("")

    out.append("END DensityModel 0")


def main():
    out = []
    emit(out)
    text = "\n".join(out) + "\n"
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
