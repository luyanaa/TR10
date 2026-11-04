#!/usr/bin/env bash
# Canonical analog PEX path for TR10:
#   Magic extract all/ext2spice for devices and capacitance
#   FastHenry deck generation (and optional solver execution) for conductor R/L/M
set -euo pipefail

FLOW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$FLOW_ROOT/.." && pwd)"
PDK_ROOT="${PDK_ROOT:-$(cd "$REPO_ROOT/.." && pwd)}"
PDK="${PDK:-TR10}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

PEX_GDS="${PEX_GDS:-}"
PEX_TOP="${PEX_TOP:-}"
PEX_OUT="${PEX_OUT:-}"
if [[ -z "$PEX_GDS" || -z "$PEX_TOP" || -z "$PEX_OUT" ]]; then
    echo "ERROR: PEX_GDS, PEX_TOP, and PEX_OUT are required" >&2
    exit 2
fi

if [[ "$PEX_GDS" != /* ]]; then PEX_GDS="$PWD/$PEX_GDS"; fi
if [[ "$PEX_OUT" != /* ]]; then PEX_OUT="$PWD/$PEX_OUT"; fi
if [[ ! -f "$PEX_GDS" ]]; then
    echo "ERROR: PEX_GDS does not exist: $PEX_GDS" >&2
    exit 2
fi

PEX_DIR="$(dirname "$PEX_OUT")"
mkdir -p "$PEX_DIR"
PEX_NAME="$(basename "$PEX_OUT")"
if [[ "$PEX_NAME" == *.spice ]]; then
    PEX_BASE="$PEX_DIR/${PEX_NAME%.spice}"
elif [[ "$PEX_NAME" == *.sp ]]; then
    PEX_BASE="$PEX_DIR/${PEX_NAME%.sp}"
else
    PEX_BASE="$PEX_OUT"
fi
PEX_EXT_OUT="${PEX_EXT_OUT:-$PEX_BASE.ext}"
PEX_MANIFEST_OUT="${PEX_MANIFEST_OUT:-$PEX_BASE.pex_manifest.json}"
PEX_LAYOUT_JSON="${PEX_LAYOUT_JSON:-$PEX_BASE.layout.json}"
PEX_FASTHENRY_INP="${PEX_FASTHENRY_INP:-$PEX_BASE.fasthenry.inp}"
PEX_FASTHENRY_LOG="${PEX_FASTHENRY_LOG:-$PEX_BASE.fasthenry.log}"
PEX_MAGIC_LOG="${PEX_MAGIC_LOG:-$PEX_BASE.magic.log}"
PEX_FASTHENRY="${PEX_FASTHENRY:-1}"
PEX_FASTHENRY_RUN="${PEX_FASTHENRY_RUN:-1}"
PEX_FASTHENRY_REQUIRED="${PEX_FASTHENRY_REQUIRED:-0}"

MAGIC_DIR="${MAGIC_DIR:-$PDK_ROOT/$PDK/libs.tech/magic}"
MAGIC_TECH="${MAGIC_TECH:-$MAGIC_DIR/$PDK.tech}"
MAGICRC="${MAGICRC:-$MAGIC_DIR/$PDK.magicrc}"
MAGIC_BIN="${MAGIC_BIN:-$(command -v magic || true)}"
LAYOUT_CONVERTER="$PDK_ROOT/$PDK/libs.tech/parasitics/layout_to_pex_json.py"
FASTHENRY_CONVERTER="$PDK_ROOT/$PDK/libs.tech/parasitics/fasthenry/ext2fasthenry.py"
STACKUP_XML="${PEX_STACKUP:-$PDK_ROOT/$PDK/libs.tech/parasitics/TR10_stackup.xml}"
MANIFEST_SUMMARIZER="$REPO_ROOT/flow/scripts/analysis/summarize_magic_pex.py"

for required in "$MAGIC_TECH" "$MAGICRC" "$LAYOUT_CONVERTER" "$FASTHENRY_CONVERTER" "$STACKUP_XML" "$MANIFEST_SUMMARIZER"; do
    if [[ -z "$required" || ! -e "$required" ]]; then
        echo "ERROR: required Magic/FastHenry PEX input is unavailable: ${required:-<empty>}" >&2
        exit 2
    fi
done

if [[ -z "$MAGIC_BIN" ]]; then
    echo "ERROR: magic is not on PATH; run this command inside the LibreLane nix shell" >&2
    exit 2
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tr10-magic-pex.XXXXXX")"
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT
MAGIC_SCRIPT="$WORK_DIR/magic.tcl"
cat > "$MAGIC_SCRIPT" <<EOF
crashbackups disable
gds read {$PEX_GDS}
load {$PEX_TOP}
extract all
ext2spice cthresh 0 rthresh 0
ext2spice -o {$PEX_OUT}
quit -noprompt
EOF

printf 'Running Magic analog extraction for %s\n' "$PEX_TOP"
set +e
(
    cd "$WORK_DIR"
    "$MAGIC_BIN" -T "$MAGIC_TECH" -dnull -noconsole -rcfile "$MAGICRC" < "$MAGIC_SCRIPT"
) >"$PEX_MAGIC_LOG" 2>&1
MAGIC_STATUS=$?
set -e
if [[ "$MAGIC_STATUS" -ne 0 ]]; then
    echo "ERROR: Magic extraction failed (status $MAGIC_STATUS); see $PEX_MAGIC_LOG" >&2
    exit "$MAGIC_STATUS"
fi
if [[ ! -s "$PEX_OUT" ]]; then
    echo "ERROR: Magic produced no SPICE output: $PEX_OUT" >&2
    exit 1
fi
MAGIC_EXT="$WORK_DIR/$PEX_TOP.ext"
if [[ ! -s "$MAGIC_EXT" ]]; then
    echo "ERROR: Magic produced no extraction database: $MAGIC_EXT" >&2
    exit 1
fi
cp "$MAGIC_EXT" "$PEX_EXT_OUT"

# layout.json must describe the CURRENT GDS.  A stale, pre-existing
# layout.json silently re-uses old geometry with a new SPICE netlist, so
# only reuse it when the caller explicitly opts in via PEX_LAYOUT_JSON_REUSE
# *and* the recorded source matches this GDS+top.  The manifest records the
# GDS sha256 the JSON was generated from; a mismatch forces regeneration.
layout_json_matches() {
    [[ -s "$PEX_LAYOUT_JSON" ]] || return 1
    "$PYTHON_BIN" - "$PEX_LAYOUT_JSON" "$PEX_GDS" "$PEX_TOP" <<'PY'
import hashlib, json, sys
jp, gds, top = sys.argv[1:4]
try:
    meta = json.load(open(jp))
except Exception:
    sys.exit(1)
src = meta.get("source", meta)          # tolerate flat or nested provenance
rec_sha = src.get("gds_sha256") or src.get("source_gds_sha256")
rec_top = src.get("top") or src.get("top_cell")
want_sha = hashlib.sha256(open(gds, "rb").read()).hexdigest()
# If the JSON records no provenance we cannot trust reuse -> regenerate.
sys.exit(0 if (rec_sha == want_sha and (rec_top is None or rec_top == top)) else 1)
PY
}

if [[ -n "${PEX_LAYOUT_JSON_EXTERNAL:-}" ]]; then
    PEX_LAYOUT_JSON="$PEX_LAYOUT_JSON_EXTERNAL"
elif [[ -n "${PEX_DEF:-}" ]]; then
    if [[ "$PEX_DEF" != /* ]]; then PEX_DEF="$PWD/$PEX_DEF"; fi
    "$PYTHON_BIN" "$LAYOUT_CONVERTER" --def "$PEX_DEF" --output "$PEX_LAYOUT_JSON"
elif [[ "${PEX_LAYOUT_JSON_REUSE:-0}" == "1" && -s "${PEX_LAYOUT_JSON:-}" ]] && layout_json_matches; then
    echo "Reusing validated layout.json: $PEX_LAYOUT_JSON"
else
    if [[ -s "${PEX_LAYOUT_JSON:-}" && "${PEX_LAYOUT_JSON_REUSE:-0}" != "1" ]]; then
        echo "NOTE: regenerating layout.json (set PEX_LAYOUT_JSON_REUSE=1 to reuse)" >&2
    fi
    "$PYTHON_BIN" "$LAYOUT_CONVERTER" --gds "$PEX_GDS" --top "$PEX_TOP" --output "$PEX_LAYOUT_JSON"
fi

FASTHENRY_STATUS="disabled"
FASTHENRY_SOLVER=""
if [[ "$PEX_FASTHENRY" != "0" ]]; then
    "$PYTHON_BIN" "$FASTHENRY_CONVERTER" "$PEX_LAYOUT_JSON" "$STACKUP_XML" -o "$PEX_FASTHENRY_INP" \
        --fmin "${PEX_FASTHENRY_FMIN:-1e8}" \
        --fmax "${PEX_FASTHENRY_FMAX:-1e10}" \
        --ndec "${PEX_FASTHENRY_NDEC:-20}" \
        --nwinc "${PEX_FASTHENRY_NWINC:-4}" \
        --nhinc "${PEX_FASTHENRY_NHINC:-2}"
    FASTHENRY_BIN="${PEX_FASTHENRY_BIN:-$(command -v fasthenry || command -v FastHenry || true)}"
    if [[ -n "$FASTHENRY_BIN" && "$PEX_FASTHENRY_RUN" != "0" ]]; then
        FASTHENRY_SOLVER="$FASTHENRY_BIN"
        set +e
        "$FASTHENRY_BIN" "$PEX_FASTHENRY_INP" >"$PEX_FASTHENRY_LOG" 2>&1
        FASTHENRY_STATUS_CODE=$?
        set -e
        if [[ "$FASTHENRY_STATUS_CODE" -eq 0 ]]; then
            FASTHENRY_STATUS="solver_completed"
        else
            FASTHENRY_STATUS="solver_failed"
            if [[ "$PEX_FASTHENRY_REQUIRED" == "1" ]]; then
                echo "ERROR: FastHenry failed (status $FASTHENRY_STATUS_CODE); see $PEX_FASTHENRY_LOG" >&2
                exit "$FASTHENRY_STATUS_CODE"
            fi
            echo "WARNING: FastHenry failed (status $FASTHENRY_STATUS_CODE); deck retained: $PEX_FASTHENRY_INP" >&2
        fi
    elif [[ -n "$FASTHENRY_BIN" ]]; then
        FASTHENRY_SOLVER="$FASTHENRY_BIN"
        FASTHENRY_STATUS="deck_generated_solver_not_run"
    else
        FASTHENRY_STATUS="deck_generated_solver_unavailable"
        if [[ "$PEX_FASTHENRY_REQUIRED" == "1" ]]; then
            echo "ERROR: FastHenry solver is unavailable; deck was generated at $PEX_FASTHENRY_INP" >&2
            exit 1
        fi
        echo "WARNING: FastHenry solver is unavailable; deck retained: $PEX_FASTHENRY_INP" >&2
    fi
fi

MANIFEST_FASTHENRY_ARGS=()
if [[ -n "$FASTHENRY_SOLVER" ]]; then
    MANIFEST_FASTHENRY_ARGS+=(--fast-henry-solver "$FASTHENRY_SOLVER")
fi

"$PYTHON_BIN" "$MANIFEST_SUMMARIZER" \
    --spice "$PEX_OUT" \
    --ext "$PEX_EXT_OUT" \
    --design "$PEX_TOP" \
    --magic-tech "$MAGIC_TECH" \
    --gds "$PEX_GDS" \
    --layout-json "$PEX_LAYOUT_JSON" \
    --fast-henry-status "$FASTHENRY_STATUS" \
    --fast-henry-input "$PEX_FASTHENRY_INP" \
    --fast-henry-log "$PEX_FASTHENRY_LOG" \
    "${MANIFEST_FASTHENRY_ARGS[@]}" \
    --output "$PEX_MANIFEST_OUT"

printf 'Magic PEX: %s\n' "$PEX_OUT"
printf 'Magic extraction database: %s\n' "$PEX_EXT_OUT"
printf 'FastHenry deck: %s (%s)\n' "$PEX_FASTHENRY_INP" "$FASTHENRY_STATUS"
printf 'PEX manifest: %s\n' "$PEX_MANIFEST_OUT"
