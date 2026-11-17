#!/usr/bin/env bash
# TR10 layout signoff for the RX_TIA block of the I/Q receiver example.
#
#   gen_tia.py        -> rx_tia.gds  (KLayout python, drawing layers)
#   KLayout run.drc   -> 0 violations
#   KLayout run.lvs   -> TR10_LVS PASS against rx_tia.strict.cir
#   Magic PEX         -> pex/rx_tia.spice (devices + node capacitances)
#
# Usage:
#   bash examples/rf_iq_receiver/layout/run_signoff.sh [pex_dir]
#
# Exit 0 only when DRC is clean and LVS passes.  Requires klayout, magic.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDK="$(cd "$HERE/../../.." && pwd)"
GDS="$HERE/rx_tia.gds"
TOP="rx_tia_layout"
CIRCUIT="$HERE/rx_tia.strict.cir"
DRC_RUNSET="$PDK/libs.tech/klayout/tech/drc/run.drc"
LVS_RUNSET="$PDK/libs.tech/klayout/tech/lvs/run.lvs"
PEX_DIR="${1:-$HERE/pex}"

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

echo "== generate layout"
klayout -b -z -r "$HERE/gen_tia.py" | tail -2

echo "== DRC"
klayout -b -zz -r "$DRC_RUNSET" \
    -rd "input=$GDS" -rd "top_cell=$TOP" \
    -rd "report=$WORK/rx_tia.lyrdb" >"$WORK/drc.log" 2>&1
python3 - "$WORK/rx_tia.lyrdb" <<'PY'
import re, sys
txt = open(sys.argv[1]).read()
items = re.findall(r"<item>(.*?)</item>", txt, re.S)
print(f"   DRC violations: {len(items)}")
for it in items[:10]:
    print("   ", re.search(r"<category>(.*?)</category>", it).group(1))
sys.exit(1 if items else 0)
PY

echo "== LVS"
klayout -b -zz -r "$LVS_RUNSET" \
    -rd "input=$GDS" -rd "top_cell=$TOP" \
    -rd "circuit=$CIRCUIT" -rd "report=$WORK/rx_tia_lvs.lyrdb" \
    >"$WORK/lvs.log" 2>&1
if ! grep -q "TR10_LVS PASS" "$WORK/lvs.log"; then
    echo "   LVS FAIL"; tail -20 "$WORK/lvs.log"; exit 1
fi
echo "   TR10_LVS PASS"

echo "== PEX -> $PEX_DIR"
mkdir -p "$PEX_DIR"
PEX_GDS="$GDS" PEX_TOP="$TOP" PEX_OUT="$PEX_DIR/rx_tia.spice" \
PEX_FASTHENRY=1 PEX_FASTHENRY_RUN=0 \
    bash "$PDK/flow/signoff/run_magic_pex.sh" >"$WORK/pex.log" 2>&1
grep -E "devices=|capacitors=" "$WORK/pex.log" | tail -1
grep -E "^C[0-9]+ (OUT|IN|VSS) " "$PEX_DIR/rx_tia.spice" || true

echo "== SIGNOFF OK"
