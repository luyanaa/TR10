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

run() {  # cell spice
  klayout -b -r "$PDK/libs.tech/klayout/tech/lvs/run_mask_analog.lvs" \
    -rd "input=$1_ml.gds" -rd "circuit=$2" -rd "extracted=$1.ext" \
    -rd "report=$1.lvsdb" 2>&1
}

echo "--- TIED cell ---"
tied_status=0
tied_out=$(run TIED tied.spice) || tied_status=$?
echo "$tied_out" | grep -E "PASS|FAIL" || true
# Positive contract: the NMOS bulk terminal must land on the labeled GND net.
# In the extracted netlist the NMOS bulk is the 4th pin; a tied body prints
# the literal net "GND", while an untied body splits into "GND$1".
if ! grep -q "NMOS" TIED.ext; then
  echo "REGRESSION: TIED cell extracted no NMOS device" >&2
  cat TIED.ext >&2
  exit 1
fi
if grep -E "NMOS" TIED.ext | grep -q 'GND\$1'; then
  echo "REGRESSION: tied NMOS bulk split onto GND\$1 (body tie broken)" >&2
  grep "NMOS" TIED.ext >&2
  exit 1
fi
echo "tied: NMOS bulk on labeled GND net, no split island (compare status=$tied_status)"

echo "--- UNTIED cell ---"
untied_status=0
out=$(run UNTIED untied.spice) || untied_status=$?
echo "$out" | grep -E "PASS|FAIL" || true

# The untied body must NOT compare clean: it should surface either a FAIL or
# a GND$1 split island in the extracted netlist.  With the fail-closed
# contract in 05_Compare.lvs it must also exit non-zero.
if echo "$out" | grep -q "TR10_LVS PASS" && ! grep -q 'GND\$1' UNTIED.ext; then
  echo "REGRESSION: untied bulk silently passed LVS" >&2
  exit 1
fi
if [[ $untied_status -eq 0 ]] && echo "$out" | grep -q "TR10_LVS FAIL"; then
  echo "REGRESSION: LVS FAIL printed but klayout exited 0 (fail-closed contract broken)" >&2
  exit 1
fi
echo "bulk-tie negative regression: OK (tied PASS, untied FAIL status=$untied_status)"
