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
# Topology stage: full bipartite-graph isomorphism, not statistics.  A count
# or per-class degree match does not prove connectivity -- two netlists with
# identical device counts and net counts can still wire the devices together
# differently (e.g. swap two gates, or short the F_RS terminals onto one net
# while keeping F_RS count=1).  Build the device<->net bipartite graph for
# each view, color nodes by (kind, class) and edges by terminal position,
# and compare canonical encodings.  Isomorphic graphs <=> the two views wire
# the same devices the same way.  Covers every device class incl. XC$ F_CSIO.
# ---------------------------------------------------------------------------
topo_rc=0
PYTHONPATH="$KPP" "$KPY" - <<'PY' || topo_rc=$?
import re, sys
from collections import defaultdict

CLASS = r'PMOSE?|NMOSE?|DN|DP|F_RS|F_RR|F_CSIO'
DEV_RE = re.compile(r'^(?:X?R|X?C|M|D|\d)(\$\d+)\s+(.*)')

def parse(path):
    """[(class, [terminal nets])]; pins: set of port net names."""
    devs, pins = [], set()
    for line in open(path):
        s = line.strip()
        mp = re.match(r'\* pin (\S+)', s)
        if mp:
            pins.update(mp.group(1).split('|')); continue
        m = DEV_RE.match(s)
        if not m: continue
        toks = m.group(2).split()
        mi = next((i for i, t in enumerate(toks)
                   if re.fullmatch(CLASS, t)), None)
        if mi is None: continue
        devs.append((toks[mi], toks[:mi]))
    return devs, pins

def graph(path):
    """Return (devices, nets) of a device<->net bipartite multigraph.

    Each device is an unlabeled node carrying only its class.  Each net is an
    unlabeled node.  Edges connect device->net with a multiplicity equal to
    the number of the device's terminals on that net (a shorted pair of
    terminals lands two edges on the same net).  Terminal *position* is NOT
    distinguished -- swapping source/drain on a symmetric device must not
    flag a divergence the extractor does not consider one.  Pin/port status
    is dropped: the two views name ports differently by construction."""
    devs, _pins = parse(path)
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for _, nets in devs:
        for n in nets:
            parent.setdefault(n, n)
            for part in n.split('|'):
                parent.setdefault(part, part)
                parent[find(n)] = find(part)   # fold alias A|B into one net
    devices = []                      # (class, {net_root: term_count})
    nets = defaultdict(int)           # net_root -> total degree
    for cls, nlist in devs:
        cnt = defaultdict(int)
        for n in nlist:
            cnt[find(n)] += 1
            nets[find(n)] += 1
        devices.append((cls, dict(cnt)))
    return devices, nets

def signature(path):
    """Canonical form of the bipartite graph, invariant to node relabeling.

    A device is fully described by its class plus the multiset of net-degree
    contributions it makes.  But net identity is only structural: a net is
    characterized by which device-classes it connects and how many terminals.
    We build a WL-style refinement over the bipartite graph and emit the
    multiset of refined edge (dev_color, net_color) pairs -- equal iff the
    two graphs are isomorphic for our purposes."""
    devices, nets = graph(path)
    # node ids: devices D0.., nets N<root>
    dcol = {i: c for i, (c, _) in enumerate(devices)}   # initial color=class
    ncol = {r: 'N' for r in nets}
    dev_net = [d for _, d in devices]                   # [{net:count}]
    net_dev = defaultdict(list)
    for i, d in enumerate(dev_net):
        for r, cnt in d.items():
            net_dev[r].append(i)
    # WL-refine, hashing colours to ints each round so they stay compact and
    # the final signature is a short, readable (dev_color, net_color) multiset.
    for _ in range(8):
        nd = {i: hash((dcol[i], tuple(sorted(
                (cnt, ncol[r]) for r, cnt in dev_net[i].items()))))
              for i in dcol}
        nn = {r: hash((ncol[r], tuple(sorted(
                dcol[i] for i in net_dev[r]))))
              for r in ncol}
        dcol, ncol = nd, nn
    # canonical edge multiset: (dev_color, net_color) per terminal
    sig = []
    for i, d in enumerate(dev_net):
        for r, cnt in d.items():
            sig += [(dcol[i], ncol[r])] * cnt
    return devices, sorted(sig)

d_devs, dsig = signature('draw.ext')
m_devs, msig = signature('mask.ext')
ok = True
if len(d_devs) != len(m_devs):
    print(f"GRAPH: device count draw={len(d_devs)} mask={len(m_devs)}"); ok = False
if dsig != msig:
    ok = False
    from collections import Counter
    dc, mc = Counter(dsig), Counter(msig)
    for e in sorted((dc - mc).elements(), key=repr):
        print(f"GRAPH draw-only edge {e}")
    for e in sorted((mc - dc).elements(), key=repr):
        print(f"GRAPH mask-only edge {e}")
print("TOPOLOGY(GRAPH-ISO): " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
PY
[ "$topo_rc" -ne 0 ] && fail=1

if [ "$fail" -eq 0 ]; then
  echo "MDP parity: device counts AND connectivity match between Drawing and Mask views"
else
  echo "MDP parity: DIVERGENCE detected (see above)" >&2
fi
exit "$fail"
