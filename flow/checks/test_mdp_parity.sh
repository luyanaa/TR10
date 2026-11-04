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

# KLayout python + module path: prefer env overrides, then nix-shell env,
# then the pinned /nix/store paths as a last resort.
KPY="${KPY:-${PYTHON_BIN:-python3}}"
KPP="${KPP:-${KLAYOUT_PYTHONPATH:-/nix/store/xppxb7azjilh33kvgp12830bzwhsq4kq-python3.14-klayout-0.30.12/lib/python3.14/site-packages}}"
if ! PYTHONPATH="$KPP" "$KPY" -c 'import klayout.db' 2>/dev/null; then
  for cand in /nix/store/*python3*/bin/python3; do
    for pp in /nix/store/*klayout*/lib/python*/site-packages; do
      if PYTHONPATH="$pp" "$cand" -c 'import klayout.db' 2>/dev/null; then
        KPY="$cand"; KPP="$pp"; break 2
      fi
    done
  done
fi

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
# F_RS: poly resistor on drawn GR (8/2).  W=6um, 2um-wide merged-CO head at
# each end; Drawing extracts L = GR length - 2x(CO enclosure + 2.0um halo).
# CO enclosure is 1.5um, so drawn L = 24.0 - 2*(1.5+2.0) = 17.0um.
box((8,2),-60,80,-36,86)                 # GR 24 x 6
box((11,0),-60,81.5,-58,84.5)            # head CO cluster x1
box((11,0),-60,83.0,-58,85.0)
box((11,0),-38,81.5,-36,84.5)            # head CO cluster x2
box((11,0),-38,83.0,-36,85.0)
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

# ---------------------------------------------------------------------------
# Topology stage: a count match does not prove connectivity -- the Mask RS
# extractor once emitted F_RS with both terminals on one net while still
# reporting F_RS count=1.  Parse each .ext, group every device's terminal nets
# per device class, and compare the resulting partition (which terminals are
# shorted together) plus device degree multiset between the two views.
# ---------------------------------------------------------------------------
topo_rc=0
PYTHONPATH="$KPP" "$KPY" - <<'PY' || topo_rc=$?
import re, sys

def parse(path):
    """Return {class: [(name, [terminal nets])]}, nets resolved through |."""
    devs, pins = {}, set()
    for line in open(path):
        line = line.strip()
        mp = re.match(r'\* pin (\S+)', line)
        if mp:
            pins.update(mp.group(1).split('|')); continue
        m = re.match(r'(?:X?R|M|D|\d)(\$\d+)\s+(.+)', line)
        if not m: continue
        toks = m.group(2).split()
        # device model = first token that is a known class name
        model = next((t for t in toks if re.fullmatch(
            r'PMOSE?|NMOSE?|DN|DP|F_RS|F_RR|F_CSIO', t)), None)
        if model is None: continue
        nets = [t for t in toks[:toks.index(model)]]
        # canonical: merge alias nets written as A|B
        canon = []
        for n in nets:
            parts = sorted(n.split('|'))
            canon.append('|'.join(parts))
        devs.setdefault(model, []).append((m.group(1), canon))
    return devs, pins

def topo(path):
    devs, pins = parse(path)
    # union-find over terminal nets so A|B aliases unify across devices
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    for _, nets in [d for ds in devs.values() for d in ds]:
        for n in nets:
            for part in n.split('|'):
                union(n, part)
    sig = {}
    for cls, ds in devs.items():
        degs, shorts = [], 0
        for _, nets in ds:
            roots = {find(n) for n in nets}
            degs.append(len(roots))
            if len(roots) < len(nets): shorts += 1
        sig[cls] = (sorted(degs), shorts)
    return sig, len(devs and {find(n) for ds in devs.values() for _, ns in ds for n in ns})

dsig, dnets = topo('draw.ext')
msig, mnets = topo('mask.ext')
ok = True
for cls in sorted(set(dsig) | set(msig)):
    d, m = dsig.get(cls), msig.get(cls)
    if d is None or m is None:
        print(f"TOPO {cls}: present in one view only"); ok = False; continue
    if d != m:
        print(f"TOPO {cls}: draw={d} mask={m}"); ok = False
if dnets != mnets:
    print(f"TOPO nets: draw={dnets} mask={mnets}"); ok = False
print("TOPOLOGY: PASS" if ok else "TOPOLOGY: FAIL")
sys.exit(0 if ok else 1)
PY
[ "$topo_rc" -ne 0 ] && fail=1

if [ "$fail" -eq 0 ]; then
  echo "MDP parity: device counts AND connectivity match between Drawing and Mask views"
else
  echo "MDP parity: DIVERGENCE detected (see above)" >&2
fi
exit "$fail"
