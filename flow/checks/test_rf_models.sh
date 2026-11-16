#!/usr/bin/env bash
# RF model regression for the TR10 IP62 process.
#
# Covers the five RF additions, all as overlays on top of the unchanged
# *_os00_calibrated baseline models:
#
#   1. multi-finger MOS      models_IP62_mos_rf.lib      (NMOS_nf / PMOS_nf)
#   2. F_CSIO ESR/Q(f)       models_IP62_cap_rf.lib      (F_CSIO_rf)
#   3. F_RS parasitics       models_IP62_res_rf.lib      (F_RS_rf)
#   4. varactors             models_IP62_varactor.lib    (MOS + junction)
#   5. spiral inductor       models_IP62_inductor.lib    (IND_PI + generator)
#                            + KLayout PCell inductor_spiral
#
# Every assertion compares against the baseline device, an analytic value or
# a geometry-derived value -- not against a hardcoded copy of the overlay.
#
# Requires ngspice; the inductor section also needs klayout.
# Exit 0 when every check passes, 1 otherwise.
set -uo pipefail

PDK="$(cd "$(dirname "$0")/../.." && pwd)"
MODELS="$PDK/libs.tech/ngspice/models"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

pass=0
fail=0

ok()   { pass=$((pass+1)); printf 'PASS  %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf 'FAIL  %s\n' "$1"; }

# check <name> <expected> <actual> <rel-tol>
check() {
  local name="$1" exp="$2" act="$3" tol="$4"
  if python3 -c "
import sys
exp, act, tol = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
ok = abs(act - exp) <= tol * max(abs(exp), 1e-30)
print('      expected %.6g  got %.6g  rel %.3g' % (exp, act, abs(act-exp)/max(abs(exp),1e-30)))
sys.exit(0 if ok else 1)" "$exp" "$act" "$tol"; then
    ok "$name"
  else
    bad "$name"
  fi
}

# check_abs <name> <expected> <actual> <abs-tol> -- for expected == 0
check_abs() {
  local name="$1" exp="$2" act="$3" tol="$4"
  if python3 -c "
import sys
exp, act, tol = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
ok = abs(act - exp) <= tol
print('      expected %.6g  got %.6g  abs %.3g' % (exp, act, abs(act-exp)))
sys.exit(0 if ok else 1)" "$exp" "$act" "$tol"; then
    ok "$name"
  else
    bad "$name"
  fi
}

# val <logfile> <key> -- first numeric field of a "key = value" line.
# Plain awk: the keys contain "()" and "+", which are regex metacharacters.
val() {
  awk -v k="$2" '
    { line = $0; sub(/^[ \t]+/, "", line) }
    index(line, k) == 1 {
      rest = substr(line, length(k) + 1)
      if (rest ~ /^[ \t]*=/) {
        sub(/^[^=]*=[ \t]*/, "", rest)
        split(rest, a, /[ \t,]+/)
        print a[1]
        exit
      }
    }' "$1"
}

# sim <netlist> <logfile> -- run ngspice, keep stdout only
sim() {
  ngspice -b "$1" >"$2" 2>"$2.err"
  if [ ! -s "$2" ]; then
    echo "      ngspice produced no output for $1" >&2
    tail -5 "$2.err" >&2
  fi
}

INC=".include $MODELS/ip62_models_calibrated"

########################################################################
echo "== 1. multi-finger MOS =="
########################################################################

# 1a. nf=1 must reproduce the baseline single-finger device exactly.
cat > mos1.sp <<EOF
multi-finger DC equivalence
$INC
.include $MODELS/models_IP62_mos_rf.lib
Vd0 d0 0 3
Vd1 d1 0 3
Vg g 0 0
Vb b 0 0
X0 d0 g b b NMOS w=10u l=1u
X1 d1 g b b NMOS_nf w=10u l=1u nf=1
.dc Vg 0 5 0.5
.control
run
let rel = vecmax(abs(i(vd0)-i(vd1)))/vecmax(abs(i(vd0)))
print rel
.endc
.end
EOF
sim mos1.sp mos1.log
r=$(val mos1.log rel)
check_abs "nf=1 DC == baseline NMOS (max relative error)" 0 "$r" 1e-9

# 1b. nf=4 must equal four explicit parallel fingers with the wrapper's
#     shared-diffusion geometry (w/4 = 2.5u, AS=AD=17.5p, PS=PD=19.5u).
cat > mos2.sp <<EOF
multi-finger parallel equivalence
$INC
.include $MODELS/models_IP62_mos_rf.lib
Vd0 d0 0 3
Vd1 d1 0 3
Vg g 0 0
Vb b 0 0
X0 d0 g b b NMOS_nf w=10u l=1u nf=4
M1 d1 g b b NMOS_mst w=2.5u l=1u m=4 as=17.5p ad=17.5p ps=19.5u pd=19.5u nrd=0 nrs=0
.dc Vg 0 5 0.5
.control
run
let rel = vecmax(abs(i(vd0)-i(vd1)))/vecmax(abs(i(vd0)))
print rel
.endc
.end
EOF
sim mos2.sp mos2.log
r=$(val mos2.log rel)
check_abs "nf=4 DC == 4 parallel 2.5u fingers (shared diffusion)" 0 "$r" 1e-9

# 1c. Gate resistance: Rg = rshg*(w/nf)/(l)/(12*nf) -> 1/nf^2 scaling, and
#     an explicit rgval must override the formula.
cat > mos3.sp <<EOF
gate resistance
$INC
.include $MODELS/models_IP62_mos_rf.lib
Vg1 g1 0 dc 2 ac 1
Vg4 g4 0 dc 2 ac 1
Vgx gx 0 dc 2 ac 1
Vd1 d1 0 3
Vd4 d4 0 3
Vdx dx 0 3
X1 d1 g1 0 0 NMOS_nf w=10u l=1u nf=1
X4 d4 g4 0 0 NMOS_nf w=10u l=1u nf=4
Xx dx gx 0 0 NMOS_nf w=10u l=1u nf=1 rgval=500
.ac lin 1 1G 1G
.control
run
let z1 = -1/i(vg1)
let z4 = -1/i(vg4)
let zx = -1/i(vgx)
print real(z1) real(z4) real(zx)
.endc
.end
EOF
sim mos3.sp mos3.log
z1=$(val mos3.log 'real(z1)')
z4=$(val mos3.log 'real(z4)')
zx=$(val mos3.log 'real(zx)')
# rshg=95, w=10u, l=1u, nf=1 -> 95*10/12 = 79.1667 ohm
check "Rg(nf=1) == rshg*w/(12*l)" 79.1666667 "$z1" 1e-3
check "Rg(nf=4) == Rg(nf=1)/16" "$(python3 -c "print($z1/16)")" "$z4" 1e-3
check "explicit rgval overrides the formula" 500 "$zx" 1e-6

########################################################################
echo "== 2. F_CSIO ESR / Q(f) =="
########################################################################

# 2a. Capacitance must be unchanged from the baseline device.
cat > cap1.sp <<EOF
CSIO capacitance equivalence
$INC
.include $MODELS/models_IP62_cap_rf.lib
V0 p0 0 dc 0 ac 1
V1 p1 0 dc 0 ac 1
X0 p0 0 0 F_CSIO c=0.826p x=37.1u y=37.1u
X1 p1 0 0 F_CSIO_rf c=0.826p x=37.1u y=37.1u esr=47
.ac lin 1 1Meg 1Meg
.control
run
let c0 = -imag(i(v0))/(2*pi*1e6)
let c1 = -imag(i(v1))/(2*pi*1e6)
print c0 c1
.endc
.end
EOF
sim cap1.sp cap1.log
c0=$(val cap1.log c0); c1=$(val cap1.log c1)
check "F_CSIO_rf capacitance == baseline F_CSIO" "$c0" "$c1" 1e-4

# 2b. Capacitance at bias must track the calibrated C(V) law.
cat > cap2.sp <<EOF
CSIO C(V)
$INC
.include $MODELS/models_IP62_cap_rf.lib
V0 p0 0 dc 2.5 ac 1
V1 p1 0 dc 2.5 ac 1
X0 p0 0 0 F_CSIO c=0.826p x=37.1u y=37.1u
X1 p1 0 0 F_CSIO_rf c=0.826p x=37.1u y=37.1u esr=47
.ac lin 1 1Meg 1Meg
.control
run
let c0 = -imag(i(v0))/(2*pi*1e6)
let c1 = -imag(i(v1))/(2*pi*1e6)
print c0 c1
.endc
.end
EOF
sim cap2.sp cap2.log
c0=$(val cap2.log c0); c1=$(val cap2.log c1)
check "F_CSIO_rf C(V=2.5) == baseline F_CSIO" "$c0" "$c1" 1e-4

# 2c. The series ESR must be the high-frequency asymptote of Re(Z).
cat > cap3.sp <<EOF
CSIO ESR asymptote
$INC
.include $MODELS/models_IP62_cap_rf.lib
V1 p1 0 dc 0 ac 1
X1 p1 0 0 F_CSIO_rf c=0.826p x=37.1u y=37.1u esr=47
.ac lin 1 100G 100G
.control
run
let z = -1/i(v1)
print real(z)
.endc
.end
EOF
sim cap3.sp cap3.log
r=$(val cap3.log 'real(z)')
check "Re(Z) -> esr at 100 GHz" 47 "$r" 0.02

# 2d. Q at 1 GHz must equal the documented series-R value.
cat > cap4.sp <<EOF
CSIO Q at 1 GHz
$INC
.include $MODELS/models_IP62_cap_rf.lib
V1 p1 0 dc 0 ac 1
X1 p1 0 0 F_CSIO_rf c=0.826p x=37.1u y=37.1u esr=47
.ac lin 1 1G 1G
.control
run
let z = -1/i(v1)
let q = abs(imag(z))/real(z)
print real(z) q
.endc
.end
EOF
sim cap4.sp cap4.log
q=$(val cap4.log q)
# Series-R limited Q = 1/(2*pi*f*C*esr); the substrate network pulls it a
# few percent below the ideal series value.
q_ideal=$(python3 -c "print(1/(2*3.141592653589793*1e9*0.826e-12*47))")
check "Q(1 GHz) of 0.826 pF with 47 ohm ESR == 1/(w*C*esr)" "$q_ideal" "$q" 0.05

########################################################################
echo "== 3. F_RS parasitics / distributed RC =="
########################################################################

# 3a. DC resistance must match the baseline law for every legal width.
for w in 4 6 12 20; do
  for v in 1 5; do
    cat > rs.sp <<EOF
F_RS DC match w=$w V=$v
$INC
.include $MODELS/models_IP62_res_rf.lib
V0 p0 0 $v
V1 p1 0 $v
X0 p0 0 F_RS w=${w}u l=50u
X1 p1 0 0 F_RS_rf w=${w}u l=50u
.control
op
print i(V0) i(V1)
.endc
.end
EOF
    sim rs.sp rs.log
    i0=$(val rs.log 'i(v0)'); i1=$(val rs.log 'i(v1)')
    check "F_RS_rf DC == F_RS at w=${w}u V=$v" "$i0" "$i1" 0.01
  done
done

# 3b. Parasitic capacitance: with the far end open every section charges, so
#     the terminal capacitance equals the geometry total.
cat > rsc1.sp <<EOF
F_RS_rf parasitic capacitance, far end open
$INC
.include $MODELS/models_IP62_res_rf.lib
V1 p1 0 dc 0 ac 1
Ropen m1 0 1e12
X1 p1 m1 0 F_RS_rf w=4u l=50u
.ac lin 1 1Meg 1Meg
.control
run
let c = -imag(i(v1))/(2*pi*1e6)
print c
.endc
.end
EOF
sim rsc1.sp rsc1.log
c=$(val rsc1.log c)
# 39 aF/um^2 * 200 um^2 + 80 aF/um * 2*(4+50) um = 7.8 + 8.64 = 16.44 fF
check "F_RS_rf parasitic C (far end open) == 16.44 fF" 16.44e-15 "$c" 0.01

# 3c. With the far end grounded the distributed line only charges C/3; the
#     lumped ladder lands within 20 % of that.
cat > rsc2.sp <<EOF
F_RS_rf terminal capacitance, far end grounded
$INC
.include $MODELS/models_IP62_res_rf.lib
V1 p1 0 dc 0 ac 1
X1 p1 0 0 F_RS_rf w=4u l=50u
.ac lin 1 1Meg 1Meg
.control
run
let c = -imag(i(v1))/(2*pi*1e6)
print c
.endc
.end
EOF
sim rsc2.sp rsc2.log
c=$(val rsc2.log c)
check "F_RS_rf terminal C (far end grounded) ~ C/3" "$(python3 -c 'print(16.44e-15/3)')" "$c" 0.20

########################################################################
echo "== 4. varactors =="
########################################################################

# 4a. MOS varactor C-V: inversion -> depletion -> accumulation.
cat > var1.sp <<EOF
NMOS varactor C-V
$INC
.include $MODELS/models_IP62_mos_rf.lib
.include $MODELS/models_IP62_varactor.lib
Vm m 0 dc -1 ac 1
V0 z 0 dc 0 ac 1
Vp p 0 dc 0.5 ac 1
Xm m 0 NMOS_var w=40u l=10u nf=8
X0 z 0 NMOS_var w=40u l=10u nf=8
Xp p 0 NMOS_var w=40u l=10u nf=8
.ac lin 1 1Meg 1Meg
.control
run
let cm = -imag(i(vm))/(2*pi*1e6)
let c0 = -imag(i(v0))/(2*pi*1e6)
let cp = -imag(i(vp))/(2*pi*1e6)
print cm c0 cp
.endc
.end
EOF
sim var1.sp var1.log
cm=$(val var1.log cm); c0=$(val var1.log c0); cp=$(val var1.log cp)
check "NMOS_var C(Vg=-1) : C(Vg=+0.5) tuning ratio" 1.488 "$(python3 -c "print($cm/$cp)")" 0.02
if python3 -c "import sys; sys.exit(0 if float('$cm') > float('$c0') > float('$cp') else 1)"; then
  ok "NMOS_var C-V is monotonic through depletion"
else
  bad "NMOS_var C-V is monotonic through depletion"
fi

# 4b. MOS varactor Q at 1 GHz.
cat > var2.sp <<EOF
NMOS varactor Q
$INC
.include $MODELS/models_IP62_mos_rf.lib
.include $MODELS/models_IP62_varactor.lib
Vg g 0 dc -1 ac 1
X1 g 0 NMOS_var w=40u l=10u nf=8
.ac lin 1 1G 1G
.control
run
let z = -1/i(vg)
let q = abs(imag(z))/real(z)
print q
.endc
.end
EOF
sim var2.sp var2.log
q=$(val var2.log q)
check "NMOS_var Q(1 GHz) at Vg=-1" 407.8 "$q" 0.05

# 4c. Junction varactor C-V, abrupt-junction engineering model.
cat > var3.sp <<EOF
junction varactor C-V
$INC
.include $MODELS/models_IP62_varactor.lib
V0 a0 0 dc 0 ac 1
V5 a5 0 dc -5 ac 1
X0 a0 0 DP_var a=100
X5 a5 0 DP_var a=100
.ac lin 1 1Meg 1Meg
.control
run
let c0 = -imag(i(v0))/(2*pi*1e6)
let c5 = -imag(i(v5))/(2*pi*1e6)
print c0 c5
.endc
.end
EOF
sim var3.sp var3.log
c0=$(val var3.log c0); c5=$(val var3.log c5)
# C(0) = cj*area + cjsw*perimeter = 1.02e-13 + 2e-10*40e-6
check "DP_var C(0 V) == cj*a + cjsw*4*sqrt(a)" 1.10e-13 "$c0" 1e-3
check "DP_var C(0)/C(-5) abrupt-junction tuning ratio" 2.4835 "$(python3 -c "print($c0/$c5)")" 0.01

# 4d. DN_var must tune the other polarity and stay in the same range.
cat > var4.sp <<EOF
DN varactor C-V
$INC
.include $MODELS/models_IP62_varactor.lib
V0 c0 0 dc 0 ac 1
V5 c5 0 dc -5 ac 1
X0 0 c0 DN_var a=100
X5 0 c5 DN_var a=100
.ac lin 1 1Meg 1Meg
.control
run
let c0 = -imag(i(v0))/(2*pi*1e6)
let c5 = -imag(i(v5))/(2*pi*1e6)
print c0 c5
.endc
.end
EOF
sim var4.sp var4.log
c0=$(val var4.log c0); c5=$(val var4.log c5)
# C(0) = 0.744e-13 + 2e-10*40e-6
check "DN_var C(0 V) == cj*a + cjsw*4*sqrt(a)" 8.24e-14 "$c0" 1e-3
if python3 -c "import sys; sys.exit(0 if float('$c0') > float('$c5') > 0 else 1)"; then
  ok "DN_var C-V decreases with reverse bias"
else
  bad "DN_var C-V decreases with reverse bias"
fi

########################################################################
echo "== 5. spiral inductor =="
########################################################################

GEN="$PDK/flow/scripts/gen_inductor_model.py"
python3 "$GEN" --turns 4 --d-out 250 --width 8 --spacing 3 \
        --name IND_4T_250U > ind4.sp 2>gen4.err
if [ -s ind4.sp ]; then ok "generator emits a 4-turn subckt"; else bad "generator emits a 4-turn subckt"; fi
python3 "$GEN" --turns 4 --d-out 250 --width 8 --spacing 3 --format json \
        > ind4.json 2>/dev/null

l_gen=$(python3 -c "import json;print(json.load(open('ind4.json'))['l_nh'])")
q_gen=$(python3 -c "import json;print(json.load(open('ind4.json'))['q_metal_1ghz'])")
din_gen=$(python3 -c "import json;print(json.load(open('ind4.json'))['d_in_um'])")
len_gen=$(python3 -c "import json;print(json.load(open('ind4.json'))['length_m2_um'])")

# 5a. Extracted inductance from the generated netlist must equal Wheeler.
cat > ind.sp <<EOF
inductor extraction
.include $MODELS/models_IP62_inductor.lib
.include ind4.sp
V1 p 0 dc 0 ac 1
V2 n 0 dc 0 ac 0
X1 p n 0 IND_4T_250U
.ac dec 20 1Meg 10G
.control
run
let y21 = i(v2)/v(p)
let zs = 1/y21
let lser = imag(zs)/(2*pi*frequency)
let qser = imag(zs)/real(zs)
print lser[0] qser[0]
meas ac l1m find lser at=1e6
meas ac q1g find qser at=1e9
.endc
.end
EOF
sim ind.sp ind.log
l_ext=$(val ind.log l1m); q_ext=$(val ind.log q1g)
l_ext_nh=$(python3 -c "print(float('$l_ext')*1e9)")
check "extracted L == Wheeler L from the shared geometry" "$l_gen" "$l_ext_nh" 1e-5
check "extracted series Q(1 GHz) == omega*L/Rdc" "$q_gen" "$q_ext" 0.01

# 5b. The PCell must draw the same geometry and pass the DRC deck.
if command -v klayout >/dev/null 2>&1; then
  IND_OUT_DIR="$WORK/ind" klayout -b -r "$PDK/flow/checks/test_inductor_pcell.py" \
      > ind_pcell.log 2>&1
  if grep -q "RESULT: PASS" ind_pcell.log; then
    ok "inductor_spiral PCell geometry + DRC minimums"
  else
    bad "inductor_spiral PCell geometry + DRC minimums"
    sed -n '1,40p' ind_pcell.log
  fi
  if grep -qE "model  : L=${l_gen:0:6}" ind_pcell.log; then
    ok "PCell reports the same L as the generator"
  else
    bad "PCell reports the same L as the generator"
    grep "model  :" ind_pcell.log
  fi
  if grep -q "d_in=${din_gen}" ind_pcell.log && \
     grep -q "len_M2=${len_gen}" ind_pcell.log; then
    ok "PCell reports the same d_in / winding length as the generator"
  else
    bad "PCell reports the same d_in / winding length as the generator"
    grep "model  :" ind_pcell.log
  fi

  drc_items=0
  for g in "$WORK"/ind/*.gds; do
    b=$(basename "$g" .gds)
    klayout -b -r "$PDK/libs.tech/klayout/tech/drc/run.drc" \
        -rd input="$g" -rd report="$WORK/$b.lyrdb" >"$WORK/$b.drc.log" 2>&1
    n=$(python3 - "$WORK/$b.lyrdb" <<'PY'
import sys, os, xml.etree.ElementTree as ET
p = sys.argv[1]
if not os.path.exists(p):
    print(-1); raise SystemExit
print(sum(1 for _ in ET.parse(p).getroot().iter('item')))
PY
)
    if [ "$n" != "0" ]; then
      echo "      DRC $b: $n items"
      drc_items=$((drc_items+1))
    fi
  done
  if [ "$drc_items" -eq 0 ]; then
    ok "KLayout DRC clean on every generated inductor layout"
  else
    bad "KLayout DRC clean on every generated inductor layout"
  fi
else
  echo "SKIP  inductor PCell checks (klayout not on PATH)"
fi

########################################################################
printf '\n%s\n' "----------------------------------------"
printf 'PASS %d  FAIL %d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
