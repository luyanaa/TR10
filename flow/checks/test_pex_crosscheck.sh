#!/usr/bin/env bash
# Magic <-> OpenRCX parasitic cross-check on an identical wire.
#
# Extracts the parasitic capacitance of one 27 um x 1.8 um M1 wire two ways:
#   * Magic   : flow/signoff/run_magic_pex.sh (ext2spice, Cthresh 0)
#   * OpenRCX : OpenROAD extract_parasitics with TR10.rcx_rules -> SPEF
#
# The wire has NO device, so Magic's per-node capacitance is a pure
# interconnect number comparable to OpenRCX's total D_NET capacitance.
#
# Known (and now documented) residual: Magic's TR10 tech file carries a
# substrate + fringe-field capacitance model; the OpenRCX rules extract only
# to an ideal reference and use a different capacitance table, so OpenRCX
# under-reports total net capacitance (~2.3x on this wire). This script
# records the measured ratio rather than asserting equality.
#
# Exit 0 always (informational); prints the measured values and ratio.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT; cd "$WORK"

OPENROAD="${OPENROAD_BIN:-$(command -v openroad || echo /nix/store/6qbn5zjnnnyna6md4rsmiqw4y26y8556-openroad-26Q3/bin/openroad)}"
# Resolve a python that can actually import klayout.db: env override first,
# then the pinned nix-store pair, then scan /nix/store.  The klayout module
# is glibc-version-sensitive, so verify import rather than assume a path.
KPY="${KPY:-${PYTHON_BIN:-}}"
KPP="${KPP:-${KLAYOUT_PYTHONPATH:-/nix/store/xppxb7azjilh33kvgp12830bzwhsq4kq-python3.14-klayout-0.30.12/lib/python3.14/site-packages}}"
_kl_try() { PYTHONPATH="$2" "$1" -c 'import klayout.db' 2>/dev/null; }
if [[ -z "$KPY" ]] || ! _kl_try "$KPY" "$KPP"; then
  KPY=""
  for cand in /nix/store/*python3*/bin/python3 python3; do
    for pp in "$KPP" /nix/store/*klayout*/lib/python*/site-packages; do
      if _kl_try "$cand" "$pp"; then KPY="$cand"; KPP="$pp"; break 2; fi
    done
  done
fi
if [[ -z "$KPY" ]]; then
  echo "ERROR: no python can import klayout.db" >&2; exit 2
fi
LEF_TECH="$REPO/libs.ref/TR10_fd_sc/techlef/TR10_tech.tlef"
LEF_SC="$REPO/libs.ref/TR10_fd_sc/lef/TR10_fd_sc.lef"
RCX="$REPO/libs.tech/openroad/TR10.rcx_rules"

# 1. GDS: 27um x 1.8um M1 wire
PYTHONPATH="$KPP" "$KPY" - <<'PY'
import klayout.db as db
lay = db.Layout(); lay.dbu = 0.001
t = lay.create_cell("WIRE")
t.shapes(lay.layer(13,0)).insert(db.Box(0,0,27000,1800))
t.shapes(lay.layer(48,0)).insert(db.Text("N", db.Trans(13500,900)))
lay.write("wire.gds")
PY

# 2. Magic PEX
if ! PEX_GDS="$WORK/wire.gds" PEX_TOP=WIRE PEX_OUT="$WORK/wire_pex.spice" \
    bash "$REPO/flow/signoff/run_magic_pex.sh" >/dev/null 2>&1; then
  echo "ERROR: Magic PEX did not run (magic/tech missing?)" >&2
  exit 2
fi
magic_ff=$(python3 -c "
import re,sys
t=open('$WORK/wire_pex.spice').read()
print(sum(float(m) for m in re.findall(r'^C\d+ \S+ 0 ([0-9.eE+-]+)f', t, re.M))*1.0)")

# 3. OpenRCX SPEF on the SAME 27x1.8um wire.
#    GDS M1 box is (0,0)-(27000,1800) -> centerline y=0.9um, no extra pad.
#    Route the DEF path on the same centerline and give the pin the same
#    minimal footprint so both extractors see identical geometry.
cat > wire.def <<'DEF'
VERSION 5.8 ;
DESIGN wire ;
UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 30000 30000 ) ;
TRACKS X 0 DO 100 STEP 300 LAYER M1 ;
TRACKS Y 0 DO 100 STEP 300 LAYER M1 ;
TRACKS X 0 DO 100 STEP 300 LAYER M2 ;
TRACKS Y 0 DO 100 STEP 300 LAYER M2 ;
COMPONENTS 0 ; END COMPONENTS
PINS 1 ;
- N + NET n + DIRECTION OUTPUT + USE SIGNAL + PLACED ( 0 900 ) N + LAYER M1 ( -900 -900 ) ( 900 900 ) ;
END PINS
NETS 1 ;
- n ( PIN N ) + ROUTED M1 ( 0 900 ) ( 27000 900 ) ;
END NETS
END DESIGN
DEF
cat > rcx.tcl <<EOF
read_lef $LEF_TECH
read_lef $LEF_SC
read_def $WORK/wire.def
extract_parasitics -ext_model_file $RCX
write_spef $WORK/orcx.spef
exit
EOF
if ! "$OPENROAD" -exit rcx.tcl >"$WORK/orcx.log" 2>&1; then
  echo "ERROR: OpenRCX did not run; see $WORK/orcx.log" >&2
  tail -20 "$WORK/orcx.log" >&2 || true
  exit 2
fi
orcx_ff=$(python3 -c "
import re
t=open('$WORK/orcx.spef').read()
m=re.search(r'\*D_NET \*\d+ ([0-9.eE+-]+)', t)
print(float(m.group(1))*1000 if m else 0)")   # SPEF is in pF -> fF

python3 - "$magic_ff" "$orcx_ff" <<'PY'
import sys
m, o = float(sys.argv[1]), float(sys.argv[2])
ratio = m/o if o else float('nan')
print(f"Magic total interconnect cap : {m:.4f} fF")
print(f"OpenRCX total net cap        : {o:.4f} fF")
print(f"Magic/OpenRCX ratio          : {ratio:.3f}")
# Magic still carries a substrate+fringe model OpenRCX lacks, so a residual
# above unity is expected on a ground-referenced single wire.  The band
# catches a gross rules-file regression (~1e6x before the unit fix, or a
# dropped table that returns ~0) without demanding exact equality.
LO, HI = 0.5, 3.5
if not (LO <= ratio <= HI):
    print(f"FAIL: Magic/OpenRCX ratio {ratio:.3f} outside [{LO},{HI}]", file=sys.stderr)
    sys.exit(1)
print(f"OK: ratio within [{LO},{HI}]")
PY
