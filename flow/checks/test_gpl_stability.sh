#!/usr/bin/env bash
# Global-placement stability regression for the TR10 cell geometry.
#
# Root cause (found 2026-11-05): OpenROAD GPL's pin-density adjustment makes
# RePlAce diverge on TR10's 75.6 um-tall standard cells.  Overflow stalls near
# 0.94, the density penalty grows without bound (1e-18 -> 1e29) and the
# Nesterov step length eventually becomes NaN (GPL-0305).  Density die size,
# routability mode, timing-driven mode and min/max phi coefficients do NOT
# help; `-disable_pin_density_adjust` converges.
#
# This check uses a pre-placement ODB captured from a real 101-instance
# design (tr1um_fifo4) and runs global_placement twice:
#   * without the flag -> the deck must still reproduce the divergence
#     (negative control: if it stops diverging, OpenROAD changed and the
#     workaround should be re-evaluated);
#   * with the flag    -> placement must finish.
#
# Requires openroad on PATH.  Exit 0 if both expectations hold, 1 otherwise.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ODB="$HERE/fixtures/tr1um_gpl/tr1um_fifo4.pre_gpl.odb"
[[ -f "$ODB" ]] || { echo "ERROR: missing fixture $ODB" >&2; exit 2; }
command -v openroad >/dev/null || { echo "ERROR: openroad not on PATH" >&2; exit 2; }

WORK="$(realpath "$(mktemp -d)")"
trap 'rm -rf "$WORK"' EXIT
cp "$ODB" "$WORK/design.odb"

# Global placement density/options mirror the LibreLane step (the default
# target density for this design is ~0.8; 0.6 reproduces the instability).
run_gpl() {  # <log> <extra-args>
    local log="$1" extra="$2"
    cat > "$WORK/gpl.tcl" <<EOF
read_db $WORK/design.odb
global_placement -density 0.6 -skip_io -pad_right 1 -pad_left 1 -init_wirelength_coef 0.25 $extra
puts "GPL_CHECK_DONE"
EOF
    # Copy the ODB per run: global_placement mutates the database.
    cp "$ODB" "$WORK/design.odb"
    timeout 240 openroad -no_init -exit "$WORK/gpl.tcl" >"$log" 2>&1 || true
}

fail=0

echo "--- negative control: pin-density adjustment enabled (expect divergence)"
run_gpl "$WORK/without.log" ""
if grep -q "GPL-0305" "$WORK/without.log"; then
    echo "OK: divergence reproduced without the workaround"
else
    echo "FAIL: GPL no longer diverges without -disable_pin_density_adjust" >&2
    echo "      OpenROAD behaviour changed; re-evaluate the workaround." >&2
    tail -5 "$WORK/without.log" >&2
    fail=1
fi

echo "--- workaround: -disable_pin_density_adjust (expect convergence)"
run_gpl "$WORK/with.log" "-disable_pin_density_adjust"
if grep -q "Global placement finished" "$WORK/with.log" && ! grep -q "GPL-0305" "$WORK/with.log"; then
    echo "OK: placement converges with -disable_pin_density_adjust"
else
    echo "FAIL: placement still diverges with -disable_pin_density_adjust" >&2
    tail -20 "$WORK/with.log" >&2
    fail=1
fi

if [[ $fail -eq 0 ]]; then
    echo "GPL stability regression: PASS"
else
    echo "GPL stability regression: FAIL" >&2
fi
exit "$fail"
