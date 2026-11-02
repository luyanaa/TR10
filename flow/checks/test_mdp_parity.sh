#!/usr/bin/env bash
# Drawing <-> Mask (MDP) device-consistency regression.
#
# Builds a multi-device cell (PMOS, NMOS, DN diode, legal-width F_RR), then
# extracts the device inventory two ways:
#   * Drawing LVS   : run.lvs on the original GDS
#   * Mask LVS      : run_mdp.drc -> run_mask_analog.lvs on the MDP output
#
# The two inventories are compared per device class. A divergence means the
# MDP implant-recognition pipeline and the Drawing extractor disagree about
# what is physically present -- exactly the dual-view gap this guards.
#
# Known limitation (documented, not masked): the Drawing resistor extractor
# only emits F_RR when the post-contact resistor body is a clean rectangle
# (runset rule in 02_Extract.lvs); the Mask implant table does not apply that
# geometric DRC filter, so a marginal RR can appear Mask-only. The script
# reports per-class counts so such asymmetries are visible.
#
# Exit 0 when every device class has equal count on both views; 1 otherwise.
set -euo pipefail

PDK="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT; cd "$WORK"

KPY=/nix/store/xahxrjs30p3mw0a42bqg9ikgkikskw8m-python3-3.14.8/bin/python3
KPP=/nix/store/xppxb7azjilh33kvgp12830bzwhsq4kq-python3.14-klayout-0.30.12/lib/python3.14/site-packages

PYTHONPATH="$KPP" "$KPY" - <<'PY'
import klayout.db as db
lay = db.Layout(); lay.dbu = 0.001
t = lay.create_cell("PARITY")
def box(l, x1, y1, x2, y2):
    t.shapes(lay.layer(*l)).insert(
        db.Box(int(x1/0.001), int(y1/0.001), int(x2/0.001), int(y2/0.001)))
# PMOS in NW
box((140,0),-20,-20,20,20); box((3,1),-8,-4,8,4); box((8,1),-1,-6,1,6)
for x in (-5,5): box((11,0),x-0.7,-2.5,x+0.7,0.5)
box((11,0),-0.7,-6.7,0.7,-5.3)
# NMOS
box((3,2),-8,30,8,38); box((8,1),-1,26,1,42)
for x in (-5,5): box((11,0),x-0.7,33.5,x+0.7,36.5)
box((11,0),-0.7,41.3,0.7,42.7)
# DN diode
box((3,2),30,40,50,55); box((11,0),38,45,42,50)
# F_RR: legal 12um width, full-width CO strips so the contact-free body is
# a clean rectangle (required by the Drawing RR extractor's DRC filter).
box((140,0),30,-10,90,30)
box((3,3),35,5,75,17)
box((11,0),36,5,38,17); box((11,0),72,5,74,17)
lay.write("parity.gds")
PY

klayout -b -r "$PDK/libs.tech/klayout/tech/lvs/run.lvs" \
  -rd input=parity.gds -rd netlist_only=1 -rd extracted=draw.ext >/dev/null 2>&1
klayout -b -r "$PDK/libs.tech/klayout/tech/drc/run_mdp.drc" \
  -rd input=parity.gds -rd output=parity_m.gds >/dev/null 2>&1
klayout -b -r "$PDK/libs.tech/klayout/tech/lvs/run_mask_analog.lvs" \
  -rd input=parity_m.gds -rd netlist_only=1 -rd extracted=mask.ext >/dev/null 2>&1

classes="PMOS NMOS PMOSE NMOSE DN DP F_RS F_RR F_CSIO"
fail=0
printf "%-8s %6s %6s\n" CLASS DRAW MASK
for c in $classes; do
  d=$(grep -oE "\b$c\b" draw.ext 2>/dev/null | wc -l || true)
  m=$(grep -oE "\b$c\b" mask.ext 2>/dev/null | wc -l || true)
  printf "%-8s %6d %6d\n" "$c" "$d" "$m"
  if [ "$d" -ne "$m" ]; then
    fail=1
    echo "  MISMATCH $c: draw=$d mask=$m" >&2
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "MDP parity: all device classes match between Drawing and Mask views"
else
  echo "MDP parity: DIVERGENCE detected (see above)" >&2
fi
exit "$fail"
