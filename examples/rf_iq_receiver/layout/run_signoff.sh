#!/usr/bin/env bash
# TR10 layout signoff for the I/Q receiver blocks.
#
#   gen_tia.py / gen_modules.py -> rx_<mod>.gds   (KLayout python, drawing layers)
#   KLayout run.drc             -> 0 violations per module
#   KLayout run.lvs             -> TR10_LVS PASS per module (strict netlist)
#   Magic PEX                   -> pex/rx_<mod>.spice (devices + node capacitances)
#
# Modules: tia lna mixer ssb fm vco amdemod
#
# Usage:
#   bash examples/rf_iq_receiver/layout/run_signoff.sh [pex_dir]
#
# Exit 0 only when DRC is clean and LVS passes for every module.
# Requires klayout, magic.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDK="$(cd "$HERE/../../.." && pwd)"
DRC_RUNSET="$PDK/libs.tech/klayout/tech/drc/run.drc"
LVS_RUNSET="$PDK/libs.tech/klayout/tech/lvs/run.lvs"
PEX_DIR="${1:-$HERE/pex}"

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

MODULES="tia lna mixer ssb fm vco amdemod"

for MOD in $MODULES; do
    echo "== module $MOD"

    if [ "$MOD" = "tia" ]; then
        GEN="$HERE/gen_tia.py"; TOP="rx_tia_layout"
        klayout -b -z -r "$GEN" | tail -1
    else
        GEN="$HERE/gen_modules.py"; TOP="rx_$MOD"
        MOD="$MOD" klayout -b -z -r "$GEN" | tail -1
    fi
    GDS="$HERE/rx_$MOD.gds"
    CIRCUIT="$HERE/rx_$MOD.strict.cir"

    echo "-- DRC"
    klayout -b -zz -r "$DRC_RUNSET" \
        -rd "input=$GDS" -rd "top_cell=$TOP" \
        -rd "report=$WORK/rx_$MOD.lyrdb" >"$WORK/drc_$MOD.log" 2>&1
    python3 - "$WORK/rx_$MOD.lyrdb" <<'PY'
import re, sys
txt = open(sys.argv[1]).read()
items = re.findall(r"<item>(.*?)</item>", txt, re.S)
print(f"   DRC violations: {len(items)}")
for it in items[:10]:
    print("   ", re.search(r"<category>(.*?)</category>", it).group(1))
sys.exit(1 if items else 0)
PY

    echo "-- LVS"
    klayout -b -zz -r "$LVS_RUNSET" \
        -rd "input=$GDS" -rd "top_cell=$TOP" \
        -rd "circuit=$CIRCUIT" -rd "report=$WORK/rx_${MOD}_lvs.lyrdb" \
        >"$WORK/lvs_$MOD.log" 2>&1
    if ! grep -q "TR10_LVS PASS" "$WORK/lvs_$MOD.log"; then
        echo "   LVS FAIL"; tail -20 "$WORK/lvs_$MOD.log"; exit 1
    fi
    echo "   TR10_LVS PASS"

    echo "-- PEX -> $PEX_DIR"
    mkdir -p "$PEX_DIR"
    PEX_GDS="$GDS" PEX_TOP="$TOP" PEX_OUT="$PEX_DIR/rx_$MOD.spice" \
    PEX_FASTHENRY=1 PEX_FASTHENRY_RUN=0 \
        bash "$PDK/flow/signoff/run_magic_pex.sh" >"$WORK/pex_$MOD.log" 2>&1
    grep -E "devices=|capacitors=" "$WORK/pex_$MOD.log" | tail -1
done

echo "== SIGNOFF OK"
