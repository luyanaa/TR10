#!/usr/bin/env bash
# Run one example through LibreLane and assert KLayout LVS on the result.
#
# Usage: run_librelane_lvs.sh <example-name> <top-cell> [<run-tag>]
#
# Expects librelane + klayout on PATH (the IIC-OSIC tools container in CI).
# PDK_ROOT/PDK default to the parent of this repository and TR10.
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "usage: $0 <example-name> <top-cell> [run-tag]" >&2
    exit 2
fi

PDK_REPO="$(cd "$(dirname "$0")/../.." && pwd)"
DESIGN="$1"
TOP="$2"
TAG="${3:-ci}"
DESIGN_DIR="$PDK_REPO/examples/$DESIGN"

export PDK_ROOT="${PDK_ROOT:-$(cd "$PDK_REPO/.." && pwd)}"
export PDK="${PDK:-TR10}"

[[ -f "$DESIGN_DIR/config.json" ]] || { echo "ERROR: no $DESIGN_DIR/config.json" >&2; exit 2; }
command -v librelane >/dev/null || { echo "ERROR: librelane not on PATH" >&2; exit 3; }
command -v klayout >/dev/null || { echo "ERROR: klayout not on PATH" >&2; exit 3; }

echo "== LibreLane: $DESIGN (tag $TAG)"
cd "$DESIGN_DIR"
librelane --pdk-root "$PDK_ROOT" --pdk "$PDK" --manual-pdk --run-tag "$TAG" config.json

RUN_DIR="$DESIGN_DIR/runs/$TAG"
echo "== KLayout LVS assertion"
bash "$PDK_REPO/flow/checks/test_klayout_lvs.sh" "$RUN_DIR" "$TOP"
