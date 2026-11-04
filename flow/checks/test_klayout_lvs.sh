#!/usr/bin/env bash
# Assert KLayout LVS on a LibreLane run of this PDK.
#
# Usage:
#   test_klayout_lvs.sh <run-dir> <top-cell> [<libs.ref library>]
#
# <run-dir> is the LibreLane run directory (e.g. examples/inv/runs/smoke).
# The script:
#   1. extracts the layout netlist from final/gds/<top>.gds with the PDK's
#      KLayout LVS deck (run.lvs, netlist_only);
#   2. builds a non-circular strict SPICE contract from the powered Verilog
#      netlist (final/pnl/<top>.pnl.v) plus the checked-in cell CDL/Liberty;
#   3. runs the full KLayout LVS comparison and asserts the deck's verdict.
#
# Exit 0 on "TR10_LVS PASS", 1 otherwise.  Requires klayout + python3.
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "usage: $0 <run-dir> <top-cell> [libs.ref library]" >&2
    exit 2
fi

PDK="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_DIR="$(realpath "$1")"
TOP="$2"
LIB="${3:-TR10_fd_sc}"

GDS="$RUN_DIR/final/gds/$TOP.gds"
PNL="$RUN_DIR/final/pnl/$TOP.pnl.v"
CDL="$PDK/libs.ref/$LIB/cdl/$LIB.cdl"
LIBERTY="$PDK/libs.ref/$LIB/lib/${LIB}__typ_5p0V_25C.lib"
RUNSET="$PDK/libs.tech/klayout/tech/lvs/run.lvs"
CONTRACT_BUILDER="$PDK/flow/checks/lvs_contract/build_core_lvs_contract.py"

for f in "$GDS" "$PNL" "$CDL" "$LIBERTY" "$RUNSET" "$CONTRACT_BUILDER"; do
    [[ -f "$f" ]] || { echo "ERROR: missing input $f" >&2; exit 2; }
done

WORK="$(realpath "$(mktemp -d)")"
trap 'rm -rf "$WORK"' EXIT

echo "== KLayout LVS: $TOP ($RUN_DIR)"
echo "   layout: $GDS"
echo "   ref   : $PNL + $(basename "$CDL")"

# 1. Extract the layout netlist (also validates the GDS hierarchy).
if ! klayout -b -zz -r "$RUNSET" \
        -rd input="$GDS" -rd top_cell="$TOP" \
        -rd netlist_only=1 -rd extracted="$WORK/extracted.cir" \
        >"$WORK/extract.log" 2>&1; then
    echo "ERROR: layout extraction failed" >&2
    tail -20 "$WORK/extract.log" >&2
    exit 1
fi
[[ -s "$WORK/extracted.cir" ]] || {
    echo "ERROR: extraction produced no netlist" >&2
    tail -20 "$WORK/extract.log" >&2
    exit 1
}

# 2. Build the strict transistor-level contract (connectivity from the
#    powered netlist, devices from the checked-in CDL).
python3 "$CONTRACT_BUILDER" \
    --physical-extracted "$WORK/extracted.cir" \
    --powered-netlist "$PNL" \
    --cell-cdl "$CDL" \
    --cell-liberty "$LIBERTY" \
    --top "$TOP" \
    --output "$WORK/contract.cir" >"$WORK/contract.log" 2>&1 || {
    echo "ERROR: strict LVS contract generation failed" >&2
    tail -20 "$WORK/contract.log" >&2
    exit 1
}

# 3. Full KLayout LVS comparison.
if ! klayout -b -zz -r "$RUNSET" \
        -rd input="$GDS" -rd top_cell="$TOP" \
        -rd circuit="$WORK/contract.cir" \
        -rd report="$WORK/lvs.lvsdb" \
        -rd extracted="$WORK/lvs.extracted" \
        >"$WORK/lvs.log" 2>&1; then
    echo "ERROR: KLayout LVS run failed" >&2
    tail -30 "$WORK/lvs.log" >&2
    exit 1
fi

if grep -q "TR10_LVS PASS" "$WORK/lvs.log"; then
    echo "KLayout LVS: PASS"
    exit 0
fi

echo "KLayout LVS: FAIL" >&2
grep -E "PORT MISMATCH|Netlist|mismatch|MISMATCH|TR10_LVS" "$WORK/lvs.log" >&2 || tail -30 "$WORK/lvs.log" >&2
exit 1
