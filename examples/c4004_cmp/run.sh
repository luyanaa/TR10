#!/usr/bin/env bash
# C4004 core reproduction: upstream netlist + upstream hand placement through
# LibreLane / OpenROAD on TR10_cmp_sc.
#
# Three passes, because TritonRoute needs the upstream M1-pin global-route
# guides (see flow/scripts/tr1um_route_guide.py):
#
#   1. `--to OpenROAD.DetailedPlacement`  netlist -> placed DEF
#   2. generate expanded.guide from that DEF with the M1-pin cell LEF
#   3. `--from OpenROAD.DetailedRouting`  route -> GDS/DRC/STA/IR-drop
#
# Usage: ./run.sh [run-tag]
set -euo pipefail

DESIGN_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DESIGN_DIR/../.." && pwd)"
PDK_ROOT="$(cd "$REPO/.." && pwd)"
TAG="${1:-c4004}"

IMAGE=hpretl/iic-osic-tools@sha256:306585de35d198e70ea58950f77147c86f56c698726a19afea9f1c83009557be
LL_SCRIPTS=/usr/local/lib/python3.12/dist-packages/librelane/scripts/openroad

docker_run() {
    docker run --rm \
        -v "$PDK_ROOT:$PDK_ROOT" \
        -v "$REPO/flow/patches/librelane/gpl.tcl:$LL_SCRIPTS/gpl.tcl:ro" \
        -v "$REPO/flow/patches/librelane/drt.tcl:$LL_SCRIPTS/drt.tcl:ro" \
        -v "$REPO/flow/patches/librelane/pdn.tcl:$LL_SCRIPTS/pdn.tcl:ro" \
        -v "$REPO/flow/patches/librelane/dpl.tcl:$LL_SCRIPTS/dpl.tcl:ro" \
        -w "$DESIGN_DIR" \
        -e PDK_ROOT="$PDK_ROOT" -e PDK=TR10 \
        -e USER_ID="$(id -u)" -e GROUP_ID="$(id -g)" \
        "$IMAGE" --skip bash -lc "$1"
}

# `librelane --from <step>` resumes from the newest state snapshot in
# runs/$TAG instead of rewinding, so a stale tag would silently skip the
# placement this script just produced.  Require a fresh tag.
if [[ -e "$DESIGN_DIR/runs/$TAG" ]]; then
    echo "ERROR: $DESIGN_DIR/runs/$TAG already exists; use a new tag" >&2
    exit 1
fi

LIBRELANE="librelane --pdk-root $PDK_ROOT --pdk TR10 --manual-pdk --run-tag $TAG config.json"

# magic cannot read the upstream SRAM128 views (235/0 outlines and AREF arrays
# abort its GDS reader, and its LEF parser rejects the POLYGON pin shapes).  The
# three magic steps that would touch the design are therefore skipped:
#
#   Magic.WriteLEF                 - abort on the macro, output unused
#   Odb.CheckDesignAntennaProperties - consumes that LEF
#   Magic.SpiceExtraction          - abort on the macro, output only feeds LVS
#
# KLayout writes the sign-off GDS and runs the sign-off DRC, and the parasitics
# come from OpenROAD RCX, so nothing in the report depends on the skipped steps.
SKIP_MAGIC="--skip Magic.WriteLEF --skip Odb.CheckDesignAntennaProperties --skip Magic.SpiceExtraction"

# The upstream design does not meet 35.088 ns under TR10's extracted parasitics
# (see the Results section of README.md); reporting that number is the point of
# the exercise, and no resizer is allowed to change the netlist.  The two timing
# checkers have no `ERROR_ON_*` variable (unlike the DRC ones), so their only
# possible outcome is a deferred error and a non-zero exit; skip them so
# `run.sh` completes.  The STA metrics are still reported and collected.
SKIP_TIMING="--skip Checker.SetupViolations --skip Checker.HoldViolations"

echo "== [1/3] LibreLane: netlist -> detailed placement (tag $TAG)"
docker_run "$LIBRELANE --to OpenROAD.DetailedPlacement"

DPL_DEF="$(find "$DESIGN_DIR/runs/$TAG" -maxdepth 2 \
    -path '*-openroad-detailedplacement/c4004_core.def' -print -quit)"
[[ -n "$DPL_DEF" ]] || { echo "ERROR: no placed DEF under runs/$TAG" >&2; exit 1; }

echo "== [2/3] global-route guide from $DPL_DEF"
docker_run "python3 $REPO/flow/scripts/tr1um_route_guide.py \
    --def $DPL_DEF \
    --out $DESIGN_DIR/expanded.guide \
    --extra-lef $REPO/libs.ref/TR10_SRAM128/lef/SRAM128.lef \
    --die 1840x1840 --pad-um 81"

echo "== [3/3] LibreLane: detailed routing -> signoff (tag $TAG)"
docker_run "$LIBRELANE $SKIP_MAGIC $SKIP_TIMING --from OpenROAD.DetailedRouting"

echo "== done: $DESIGN_DIR/runs/$TAG/final"
