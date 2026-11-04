#!/usr/bin/env bash
# KLayout LVS regression on real TR-1um use-case artifacts.
#
# The fixtures under fixtures/tr1um_lvs are finished connected-power GDS
# layouts plus their generated strict SPICE contracts, taken from the TR-1um
# flow designs (alu8, fifo4, irqctrl).  They exercise the full PDK KLayout
# LVS deck on real multi-hundred-instance cores, independently of whether
# the LibreLane RTL flow can place/route them.
#
# Each fixture must produce the deck's "TR10_LVS PASS" verdict.  KLayout
# resolves relative -rd paths against the input GDS directory, so every path
# handed to the deck is absolute.
#
# Requires klayout on PATH.  Exit 0 on all-pass, 1 otherwise.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PDK="$(cd "$HERE/../.." && pwd)"
FIXTURES="$HERE/fixtures/tr1um_lvs"
RUNSET="$PDK/libs.tech/klayout/tech/lvs/run.lvs"

[[ -d "$FIXTURES" ]] || { echo "ERROR: missing fixtures dir $FIXTURES" >&2; exit 2; }
command -v klayout >/dev/null || { echo "ERROR: klayout not on PATH" >&2; exit 2; }

WORK="$(realpath "$(mktemp -d)")"
trap 'rm -rf "$WORK"' EXIT

fail=0
for gds in "$FIXTURES"/*.gds; do
    [[ -f "$gds" ]] || continue
    top="$(basename "$gds" .gds)"
    circuit="$FIXTURES/$top.strict.cir"
    if [[ ! -f "$circuit" ]]; then
        echo "MISSING: $circuit"; fail=1; continue
    fi
    echo "--- $top"
    if ! klayout -b -zz -r "$RUNSET" \
            -rd "input=$gds" -rd "top_cell=$top" \
            -rd "circuit=$circuit" \
            -rd "report=$WORK/$top.lvsdb" \
            -rd "extracted=$WORK/$top.extracted" \
            >"$WORK/$top.log" 2>&1; then
        echo "FAIL $top: LVS deck error" >&2
        tail -20 "$WORK/$top.log" >&2
        fail=1
        continue
    fi
    if grep -q "TR10_LVS PASS" "$WORK/$top.log"; then
        echo "PASS $top"
    else
        echo "FAIL $top: no TR10_LVS PASS verdict" >&2
        grep -E "PORT MISMATCH|mismatch|MISMATCH|TR10_LVS" "$WORK/$top.log" >&2 || tail -20 "$WORK/$top.log" >&2
        fail=1
    fi
done

if [[ $fail -eq 0 ]]; then
    echo "TR-1um KLayout LVS fixtures: all pass"
else
    echo "TR-1um KLayout LVS fixtures: FAILURES" >&2
fi
exit "$fail"
