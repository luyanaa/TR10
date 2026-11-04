#!/usr/bin/env bash
# Bulk/well-tie negative regression for the Mask analog LVS deck.
#
# connect_global(BULK,"GND") forces every NMOS body net onto the GND symbol,
# which can mask a physically missing well tie. This test builds two minimal
# NMOS cells -- one whose body is reachable, one whose only "tie" contact is
# absent -- and proves the LVS result distinguishes them instead of silently
# passing both.
#
# Expected:
#   * TIED   cell extracts body on a labeled net (single GND domain).
#   * UNTIED cell produces a split GND$1 island and FAILs comparison.
#
# Requires klayout on PATH (>=0.29). Exit 0 on success (behaviour confirmed),
# 1 if the untied case unexpectedly passes (regression).
set -euo pipefail

PDK="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

# KLayout python + module path: prefer env overrides, then nix-shell env,
# then the pinned /nix/store paths as a last resort.
KPY="${KPY:-${PYTHON_BIN:-python3}}"
KPP="${KPP:-${KLAYOUT_PYTHONPATH:-/nix/store/xppxb7azjilh33kvgp12830bzwhsq4kq-python3.14-klayout-0.30.12/lib/python3.14/site-packages}}"
if ! PYTHONPATH="$KPP" "$KPY" -c 'import klayout.db' 2>/dev/null; then
  for cand in /nix/store/*python3*/bin/python3; do
    for pp in /nix/store/*klayout*/lib/python*/site-packages; do
      if PYTHONPATH="$pp" "$cand" -c 'import klayout.db' 2>/dev/null; then
        KPY="$cand"; KPP="$pp"; break 2
      fi
    done
  done
fi

# --- build tied / untied NMOS mask GDS through run_mdp ----------------------
PYTHONPATH="$KPP" "$KPY" - "$PDK" <<'PY'
import klayout.db as db, subprocess, sys
pdk = sys.argv[1]

def build(name, tie):
    lay = db.Layout(); lay.dbu = 0.001
    t = lay.create_cell(name)
    def box(l, x1, y1, x2, y2):
        t.shapes(lay.layer(*l)).insert(
            db.Box(int(x1/0.001), int(y1/0.001), int(x2/0.001), int(y2/0.001)))
    # NMOS is drawn as AN (3/2).  The PWELL backgate is AP (3/1): it must be
    # an *opposite-polarity* active so the MDP implant table emits the NM/NSD
    # implants that classify it as AAGN (backgate) and connect it to PWMN.
    # Drawing the tie as AN again produces AADN (a diode) instead, which is
    # not a body tie -- this is the geometry this regression exists to guard.
    box((3, 2), -8, 0, 8, 8)          # NMOS active (AN)
    box((8, 1), -1, -4, 1, 12)        # gate poly
    for x in (-5, 5):                 # S/D contacts
        box((11, 0), x-0.7, 2.5, x+0.7, 5.5)
    box((13, 0), -6, -3, -4, 7)       # source M1 island
    if tie:                           # PWELL backgate contact + M1 strap (AP)
        box((3, 1), 14, 0, 22, 8)
        box((11, 0), 16.5, 3, 19.5, 5)
        box((13, 0), 14, -3, 22, 7)
        box((13, 0), -6, -8, 22, -3)
    lay.write(f"{name}.gds")

for name, tie in (("TIED", True), ("UNTIED", False)):
    build(name, tie)
    subprocess.run(["klayout", "-b", "-r",
                    f"{pdk}/libs.tech/klayout/tech/drc/run_mdp.drc",
                    "-rd", f"input={name}.gds", "-rd", f"output={name}_m.gds"],
                   check=True, capture_output=True)
    # label the source/tie M1 region GND
    lay = db.Layout(); lay.read(f"{name}_m.gds"); top = lay.top_cell()
    for li in lay.layer_indices():
        if lay.get_info(li).layer != 13: continue
        for sh in top.shapes(li):
            c = sh.bbox().center()
            top.shapes(lay.layer(48, 0)).insert(db.Text("GND", db.Trans(c.x, c.y)))
    lay.write(f"{name}_ml.gds")
PY

cat > tied.spice <<'EOF'
.SUBCKT TIED GND
M1 GND n2 n1 GND NMOS W=8u L=2u
.ENDS
EOF
cat > untied.spice <<'EOF'
.SUBCKT UNTIED GND
M1 GND n2 n1 GND NMOS W=8u L=2u
.ENDS
EOF
# Negative schematics driven against the TIED layout.  The layout is
# unchanged; only the reference changes, so a PASS here is impossible for a
# correct comparator.
cat > missing.spice <<'EOF'
.SUBCKT TIED GND
* schematic expects the NMOS the layout provides, plus a second one it
* does not -- a device-count mismatch, not a connectivity one.
M1 GND n2 n1 GND NMOS W=8u L=2u
M2 GND n2 n1 GND NMOS W=8u L=2u
.ENDS
EOF
cat > srcshort.spice <<'EOF'
.SUBCKT TIED GND
* schematic ties source and bulk to the SAME pin (n1 == bulk); the layout
* keeps them on separate regions -> connectivity mismatch.
M1 n1 n2 n1 n1 NMOS W=8u L=2u
.ENDS
EOF

run() {  # cell spice
  klayout -b -r "$PDK/libs.tech/klayout/tech/lvs/run_mask_analog.lvs" \
    -rd "input=$1_ml.gds" -rd "circuit=$2" -rd "extracted=$1.ext" \
    -rd "report=$1.lvsdb" 2>&1
}

# Strict assertion: an LVS run must produce BOTH the expected exit code AND
# the expected verdict line.  A nonzero exit with no TR10_LVS verdict means
# the deck errored before comparing -- that is not a real LVS result.
#   expect <label> <cell> <spice> <exit:zero|nonzero> <verdict:PASS|FAIL>
fail=0
expect() {
  local label="$1" cell="$2" spice="$3" want_exit="$4" want_verdict="$5"
  local status=0 out
  out=$(run "$cell" "$spice") || status=$?
  local verdict=""
  verdict=$(echo "$out" | grep -oE "TR10_LVS (PASS|FAIL)" | head -1 | awk '{print $2}')
  local ok=1 why=""
  if [[ "$want_exit" == zero && $status -ne 0 ]]; then ok=0; why="exit=$status want 0"; fi
  if [[ "$want_exit" == nonzero && $status -eq 0 ]]; then ok=0; why="exit=0 want nonzero"; fi
  if [[ "$verdict" != "$want_verdict" ]]; then ok=0; why="${why:+$why; }verdict='${verdict:-none}' want $want_verdict"; fi
  printf "  %-14s exit=%-8s verdict=%-5s : %s\n" \
    "$label" "$status" "${verdict:-none}" "$([ $ok -eq 1 ] && echo OK || echo "FAIL ($why)")"
  if [ $ok -eq 0 ]; then echo "$out" | tail -8 >&2; fail=1; fi
  return 0
}

echo "--- assertion matrix (layout vs schematic) ---"
# TIED layout + matching schematic           -> clean PASS
expect TIED          TIED   tied.spice    zero    PASS
# UNTIED layout (no body tie) + same schematic -> split island, FAIL
expect UNTIED        UNTIED untied.spice  nonzero FAIL
# TIED layout but schematic asks for a 2nd MOS -> device mismatch, FAIL
expect MISSING_MOS   TIED   missing.spice nonzero FAIL
# TIED layout but schematic shorts src=bulk   -> connectivity mismatch, FAIL
expect SRC_BODY_SHORT TIED  srcshort.spice nonzero FAIL

# Belt-and-suspenders: the tied bulk still must not split onto GND$1.
if grep -E "NMOS" TIED.ext | grep -q 'GND\$1'; then
  echo "REGRESSION: tied NMOS bulk split onto GND\$1 (body tie broken)" >&2
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "bulk-tie regression: all four rows asserted OK"
else
  echo "bulk-tie regression: ASSERTION FAILURE (see above)" >&2
fi
exit "$fail"
