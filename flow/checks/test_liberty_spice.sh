#!/usr/bin/env bash
# Liberty <-> SPICE consistency regression for INV_X1.
#
# Simulates INV_X1 (PMOS W=10.2, NMOS W=3.4, L=1) at 5 V with the same
# stimulus the characterization grid uses at its smallest corner
# (input_transition = 0.5 ns, total_output_net_capacitance = 0.1 pF), and
# checks the measured propagation delays sit within a loose envelope of the
# Liberty table entry. This is a consistency gate, not a re-characterization:
# it catches a broken model include, a swapped pin order, or a 10x unit
# error -- not a 20 % characterization drift.
#
# Envelope: measured delay must be within [0.25x, 4x] of the Liberty value.
# The measured value uses an ideal 0.5 ns edge; the Liberty number was
# produced by the characterizer's own slew/load model, so exact equality is
# not expected.
#
# Requires ngspice on PATH. Exit 0 on pass, 1 on fail.
set -euo pipefail

PDK="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT; cd "$WORK"

MODELS="$PDK/libs.tech/ngspice/models"
LIB="$PDK/libs.ref/TR10_fd_sc/lib/TR10_fd_sc__typ_5p0V_25C.lib"

# Liberty reference: first cell_rise / cell_fall entry of INV_X1 (ns).
ref_rise=$(python3 - "$LIB" <<'PY'
import re, sys
txt = open(sys.argv[1]).read()
cell = txt.split('cell (INV_X1)')[1]
for name in ('cell_rise', 'cell_fall'):
    m = re.search(name + r'\s*\(delay_template\)\s*\{\s*values\s*\("([^",]+)', cell)
    print(m.group(1) if m else '0')
PY
)
ref_rise=$(echo "$ref_rise" | sed -n '1p')
ref_fall=$(echo "$ref_rise" | sed -n '2p')
# re-extract properly (two separate calls)
ref_rise=$(python3 -c "
import re
t=open('$LIB').read().split('cell (INV_X1)')[1]
print(re.search(r'cell_rise\s*\(delay_template\)\s*\{\s*values\s*\(\"([^\",]+)', t).group(1))")
ref_fall=$(python3 -c "
import re
t=open('$LIB').read().split('cell (INV_X1)')[1]
print(re.search(r'cell_fall\s*\(delay_template\)\s*\{\s*values\s*\(\"([^\",]+)', t).group(1))")

# Simulate the *shipped* INV_X1 subckt directly (real AS/AD/PS/PD parasitics
# and the characterized device sizes), not a hand-written pair.  Pin order is
# (VDD A Y GND) per libs.ref/TR10_fd_sc/spice/TR10_fd_sc.spice.
#
# Acceptance: the shipped netlist must load WITHOUT the caller rewriting
# transistor instances.  PMOS/NMOS are .subckt wrappers over level-49
# .model devices, so the shipped file uses X-instances (X$1 ... PMOS).
#
# Stage A: full-library elaboration.  Include the whole shipped netlist and
# instantiate a representative subset (combinational + sequential) so any
# M-element/subckt binding error anywhere fails fast.
CELL_NETLIST="$PDK/libs.ref/TR10_fd_sc/spice/TR10_fd_sc.spice"
if grep -qE '^M(\$|[0-9])' "$CELL_NETLIST"; then
  echo "ERROR: shipped spice still uses M-instances for .subckt models" >&2
  exit 2
fi
cat > elab.spice <<EOF
.include $MODELS/ip62_models_calibrated
.include $CELL_NETLIST
* elaborate one instance of every shipped subckt by tying its pins to a
* common net -- a parse/elaboration failure (unbound model, bad primitive)
* aborts ngspice here.
EOF
# Emit one X-instance per .SUBCKT; pin count read from the subckt header.
python3 - "$CELL_NETLIST" >>elab.spice <<'PY'
import re, sys
n = 0
for line in open(sys.argv[1]):
    m = re.match(r'\.SUBCKT\s+(\S+)\s+(.*)', line, re.I)
    if m:
        pins = m.group(2).split()
        print(f"Xe{n} " + " ".join(["n0"] * len(pins)) + " " + m.group(1))
        n += 1
print("Vn n0 0 0")
print(".end")
sys.stderr.write(f"elaborated {n} subckts\n")
PY
# ngspice exits nonzero for a deck with no analysis; that is expected for an
# elaboration-only smoke.  Success = no unbound-model / parse errors.
ngspice -n -b elab.spice -o elab.out >elab.log 2>&1 || true
if grep -qiE "could not find a valid modelname|Error on line|syntax error|unrecognized" elab.out; then
  echo "ERROR: shipped spice failed ngspice elaboration" >&2
  grep -iE "error|modelname|could not|unrecognized" elab.out | head >&2
  exit 2
fi
echo "elaboration smoke: shipped netlist loads clean"

# Stage B: real transient on INV_X1.
cat > tb.spice <<EOF
.include $MODELS/ip62_models_calibrated
.include $CELL_NETLIST
VDD vdd 0 5
VIN a 0 PULSE(0 5 1n 0.5n 0.5n 20n 40n)
Xinv vdd a y 0 INV_X1
CL y 0 0.1p
.tran 0.05n 60n
.control
run
meas tran tplh TRIG v(a) VAL=2.5 FALL=1 TARG v(y) VAL=2.5 RISE=1
meas tran tphl TRIG v(a) VAL=2.5 RISE=1 TARG v(y) VAL=2.5 FALL=1
print tplh
print tphl
.endc
.end
EOF

# -n skips the user ~/.spiceinit, which may preload unrelated osdi/model
# files and either break the deck or mask a missing TR10 dependency.
if ! ngspice -n -b tb.spice -o tb.out >tb.log 2>&1; then
  echo "ERROR: ngspice failed; see tb.out/tb.log" >&2
  tail -20 tb.out tb.log >&2 || true
  exit 2
fi
tplh=$(grep -oE 'tplh *= *[0-9.eE+-]+' tb.out | head -1 | grep -oE '[0-9.eE+-]+$')
tphl=$(grep -oE 'tphl *= *[0-9.eE+-]+' tb.out | head -1 | grep -oE '[0-9.eE+-]+$')
if [[ -z "$tplh" || -z "$tphl" ]]; then
  echo "ERROR: ngspice produced no measurands (model/netlist broken?)" >&2
  tail -20 tb.out >&2 || true
  exit 2
fi

python3 - "$ref_rise" "$ref_fall" "$tplh" "$tphl" <<'PY'
import sys
rr, rf, lh, hl = (float(x) for x in sys.argv[1:5])
# liberty values are ns; spice values are seconds -> normalize to ns
lh_ns, hl_ns = lh*1e9, hl*1e9
ok = True
for name, libv, meas in (("cell_rise", rr, lh_ns), ("cell_fall", rf, hl_ns)):
    lo, hi = 0.25*libv, 4.0*libv
    status = "OK" if lo <= meas <= hi else "FAIL"
    print(f"{name}: liberty={libv:.3f}ns spice={meas:.3f}ns envelope=[{lo:.3f},{hi:.3f}] -> {status}")
    ok &= (status == "OK")
sys.exit(0 if ok else 1)
PY
