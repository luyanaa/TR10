# RF Models for the TR10 IP62 Process

Engineering first-pass RF extensions. Every device here is an **overlay**: the
OS00-calibrated baseline files are not modified, and the overlay subcircuits
have new names, so existing netlists keep their behaviour.

> **Status: engineering only.** These models are built from the calibrated
> baseline laws plus geometry and sheet-resistance priors. The placeholders
> are listed in [Engineering placeholders](#engineering-placeholders). Do not
> quote Q, ft or fmax from them as measured silicon data.

## Using the manifest

```spice
* first line of a SPICE file is the title, so start the netlist with a comment
.include <pdk>/libs.tech/ngspice/models/ip62_models_rf
```

`ip62_models_rf` includes `ip62_models_calibrated` first, then the five
overlays:

| File | Devices |
| --- | --- |
| `models_IP62_mos_rf.lib` | `NMOS_nf`, `PMOS_nf` |
| `models_IP62_cap_rf.lib` | `F_CSIO_rf` |
| `models_IP62_res_rf.lib` | `F_RS_rf` |
| `models_IP62_varactor.lib` | `NMOS_var`, `PMOS_var`, `DP_var`, `DN_var` |
| `models_IP62_inductor.lib` | `IND_PI` template |

## 1. Multi-finger MOS (`NMOS_nf` / `PMOS_nf`)

```spice
X1 d g s b NMOS_nf w=10u l=1u nf=4
X2 d g s b PMOS_nf w=20u l=1u nf=4 rshg=12
```

The wrapper splits `w` into `nf` fingers of `w/nf` (`m=nf` on the BSIM3 core),
computes the shared-diffusion junction geometry from `sd` (default 2.8 um):

```
AS = AD = (w/nf) * sd * (nf+1)/2
PS = PD = 2*(sd/2 + w/nf) * (nf+1)/2
```

and adds a series gate resistance in front of the internal BSIM3 gate, because
this BSIM3 deck has no `rgate`/`rgatemod`:

```
Rgate = rshg * (w/nf/l) / (12*nf)
```

`rgval` overrides the formula (use it when you have measured gate resistance);
`rgval=-1` means "use the formula". `cjsw_ext` (fF/um of total finger
perimeter) adds the sidewall junction capacitance that BSIM3 does not carry in
this deck; default 0 keeps the baseline behaviour.

Verified (`flow/checks/test_rf_models.sh`):

| Check | Result |
| --- | --- |
| `nf=1` DC vs baseline `NMOS` | max abs error 3.5e-16 A |
| `nf=4` DC vs four explicit 2.5u fingers with shared diffusion | exact (0) |
| `Rgate` at w=10u, l=1u, nf=1 | 79.1667 ohm = rshg*w/(12*l) |
| `Rgate` at nf=4 | 4.9479 ohm = 1/16 of nf=1 |
| `rgval=500` | 500 ohm |

Note: `nf=4` of a 10 um device is not identical to one 10 um device with
`m=1`, because `wint=6.6e-7` makes each 2.5 um finger behave differently from
a single wide device. That is physical, not a wrapper bug.

## 2. F_CSIO with plate ESR and Q(f) (`F_CSIO_rf`)

```spice
XC1 plus minus sub F_CSIO_rf c=0.6p x=37.1u y=37.1u
XC2 plus minus sub F_CSIO_rf c=6p x=100u y=100u esr=20
```

The calibrated top-plate C(V)/C(T) law and the calibrated bottom-plate law are
kept verbatim; the overlay adds

* a single series plate resistance `esr` (default 47 ohm) between the bottom
  plate and `minus`,
* a lossy bottom-plate path to `sub` (`rsub`, default 1 kOhm),
* an optional explicit substrate capacitance (`csub`, default 0).

```
Q(f) = 1 / (2*pi*f*C*esr)
```

This is the series-R limited Q. Dielectric loss (tan-delta) is **not**
modelled because the PDK has no measured value.

The default `esr` is a geometry estimate, not measured: for a plate contacted
on one edge, `R = Rsh*L/(3*W)`, so a square plate has `R = Rsh/3` independent
of size. `47 ohm = 32 ohm` (poly top plate, 95 ohm/sq / 3) `+ 15 ohm`
(n-well/diffusion bottom plate, 45 ohm/sq / 3). A square plate therefore has a
size-independent ESR and `Q` scales as `1/C`: small capacitors are the high-Q
ones, large bypass capacitors are not.

A 3-section lumped RC ladder was evaluated and **rejected as the primary
model**: it gives `14/9 * esr` at low frequency and `esr` at high frequency, so
it cannot represent one physical plate resistance. The series model is valid
up to the distributed roll-off `f ~ 1/(2*pi*R*C)`; above that it is optimistic
about Q.

Verified: capacitance equals baseline `F_CSIO` at 0 V (8.5078e-13 F) and at
2.5 V (8.53524e-13 F), relative error 1.2e-7; `Re(Z) -> 47 ohm` at 100 GHz;
`Q(1 GHz)` for 0.826 pF = 3.98 vs the analytic 4.0996 (the substrate network
pulls it ~3 % down).

**LVS constraint:** the well plate is tied to VDD by
`connect_global(WN,"VDD")`, so the `sub` terminal is VDD in layout. Do not use
`F_CSIO_rf` as a floating signal capacitor without relaxing that global.

## 3. F_RS parasitics and distributed RC (`F_RS_rf`)

```spice
XR1 plus minus sub F_RS_rf w=4u l=50u
```

The calibrated `R(V)`/`R(T)` law is split into a 3-resistor / 2-capacitor
ladder:

```
plus --[R/3]-- n1 --[R/3]-- n2 --[R/3]-- minus
                 |             |
                C/2           C/2
                 |             |
                sub           sub
```

DC total resistance is preserved. Each section sees its own local voltage, so
the `R(V)` term is slightly more physical than applying the total voltage to
one resistor. The parasitic capacitance comes from the Magic tech file
(`areacap poly 39 aF/um^2`, `perimc poly 80 aF/um`):

```
csub = 0.039 fF/um^2 * w*l + 0.08 fF/um * 2*(w+l)
```

Verified:

| Check | Result |
| --- | --- |
| DC vs baseline `F_RS`, w = 4/6/12/20 um, V = 1/5 V | max relative error 0.32 % |
| Terminal C, far end open | 16.44 fF = `C_total` exactly |
| Terminal C, far end grounded | 4.567 fF = 0.28 * `C_total` |

The continuous-line value for the grounded case is `C_total/3 = 0.333`;
the 17 % gap is the lumping error of a 2-capacitor ladder and it errs on the
low side (the model is optimistic about how much the parasitic capacitance
loads a driven resistor). Add sections if that matters.

A diffusion resistor is deliberately **not** added: the `res_diff` PCell draws
an AR strip and LVS extracts it as `F_RR`, while a diffusion strip without a
gate extracts as a diode. That is a layout/LVS question, not a model question.

## 4. Varactors

### MOS type (recommended; uses the existing BSIM3 C-V)

```spice
XV1 gate 0     NMOS_var w=40u l=1u nf=8
XV2 gate 0 vdd PMOS_var w=40u l=1u nf=8
```

* `NMOS_var plus minus` — drain/source/body tied to `minus`; body is the
  p-substrate (VSS), so no isolation is needed and LVS is clean.
* `PMOS_var plus minus bw` — drain/source tied to `minus`; the n-well body is
  the separate `bw` terminal, tie it to VDD. It is exposed because
  `connect_global(WN,"VDD")` fixes the well potential in layout.

Both are multi-finger to reduce gate resistance and reuse `NMOS_nf`/`PMOS_nf`.
The C-V is the BSIM3 `capmod=2` result; no new fitting is claimed. Expect a
practical `Cmax/Cmin` of 2-3, not the ideal 7-9. Keep `|Vgs| <= 5 V`.

Verified: `C(-1 V)/C(+0.5 V) = 1.488`, `Q(1 GHz)` at `Vg=-1` = 407.8.

### Junction type (abrupt-junction first pass)

```spice
XD1 anode 0     DP_var a=100
XD2 0     cathode DN_var a=100
```

The baseline DP/DN models carry only `is/rs/cj/cjsw/bv` — no grading
coefficient and no built-in potential — and their `cj` values (4.79e-17,
2.76e-17 F/m^2) are not physically usable, so the C(V) shape is undefined.
These wrappers add the missing terms with an **engineering abrupt-junction
assumption**:

| Parameter | Value | Note |
| --- | --- | --- |
| `mj` | 0.5 | abrupt junction |
| `pb` | 0.9 V | built-in potential |
| `cj` (DP) | 1.02e-3 F/m^2 | 1.02 fF/um^2, from the baseline MOS junction |
| `cj` (DN) | 0.744e-3 F/m^2 | 0.744 fF/um^2, same source |
| `cjsw` | 2.0e-10 F/m | 0.2 fF/um |
| area | `a` in um^2 | perimeter is the equivalent square, `4*sqrt(a)` |

`rs` is the series resistance of that equivalent square (33.71 ohm DP,
47.59 ohm DN) and is applied as an external `Rser`, not as the diode's `rs`
(see [ngspice notes](#ngspice-notes)).

Verified: `DP_var C(0 V) = 1.10e-13 F` (= `cj*a + cjsw*4*sqrt(a)`),
`C(0)/C(-5 V) = 2.485`; `DN_var C(0 V) = 8.24e-14 F`, monotonically
decreasing with reverse bias.

`DN_var` is n+ in p-sub. In this PDK the substrate is the global VSS, so
`DN_var`'s cathode (`plus`) is the substrate: it is a VSS-referenced device
and cannot float.

Replace `mj`/`pb`/`cj` with measured C-V data before using either junction
varactor in a tuned tank.

## 5. Spiral inductor

There is no inductor in the baseline PDK. The implementation is split so the
drawn cell and the SPICE model cannot drift apart:

```
libs.tech/klayout/tech/python/cells/inductor_geom.py   pya-free geometry + Wheeler
libs.tech/klayout/tech/python/cells/inductor.py        inductor_spiral PCell
flow/scripts/gen_inductor_model.py                     geometry -> SPICE subckt
libs.tech/ngspice/models/models_IP62_inductor.lib      IND_PI template
```

```bash
python3 flow/scripts/gen_inductor_model.py --turns 4 --d-out 250 \
        --width 8 --spacing 3 --name IND_4T_250U > ind4.sp
```

`--format json` prints `d_in`, winding length and area for cross-checking
against the layout. The PCell (`inductor_spiral`) draws the M2 spiral, the M1
underpass and two 1.4 x 1.4 V1 cuts; it coerces `width >= 3.4 um` (a V1 needs
1.0 um of M2 on each side) and `spacing >= 2.0 um` (M2.S1), and snaps to the
0.05 um grid.

**Metal preset.** The stackup file labels the conductor "Aluminum" but carries
58 MS/m, which is copper. The process is aluminium, so the generator default is
`--metal al` (35 MS/m thin film; bulk Al is 37.7 MS/m). `--metal cu` reproduces
the old 58 MS/m numbers. M2 is 0.5747 um and M1 0.3448 um thick, giving
`Rsh_M2 = 0.0497` and `Rsh_M1 = 0.0829` ohm/sq for Al.

| Device | L (nH) | Rdc (ohm) | Q_metal @1 GHz | Loaded Q @1 GHz (50 ohm) |
| --- | --- | --- | --- | --- |
| `IND_4T_250U` (4 turns, 250 um) | 6.38734 | 24.109 | 1.665 | 0.388 |
| `IND_2T_150U` (2 turns, 150 um) | 1.1015 | 9.579 | 0.722 | -0.005 |

`Q_metal = omega*L/Rdc` is the series-branch upper bound; the loaded column is
what a 50 ohm port-2 termination sees, including the lossy substrate network.
`Rdc` includes 2 ohm of via resistance (one inner, one outer cut); the
metal-only part is 22.109 / 13.342 ohm and scales exactly as 58/35 between the
Cu and Al presets.

L is Wheeler (`2.34*mu0*n^2*d_avg/(1+2.75*rho)`) with `d_avg`/`rho` taken from
the *drawn* inner hole, so it matches the layout rather than a textbook
approximation of it. The extracted series L from the generated netlist equals
the generator value to 1e-5.

### When is Q positive? (Al)

`Q = Im(Zin)/Re(Zin)` for the one-port, so **Q > 0 exactly when the input is
inductive**. The sign is not set by `omega*L/Rdc`; it is set by which branch
dominates `Zin`: the series `Rdc + jωL` winding, the shunt plate capacitance
`c_ox` to the substrate, and the lossy `rsub`/`csub` substrate network. The
4-turn and 2-turn parts bracket the two regimes:

| Device | Port 2 | Q > 0 interval (Al, 1 MHz–100 GHz) | Q(0.1 G) | Q(1 G) | Q(10 G) |
| --- | --- | --- | --- | --- | --- |
| 4T | open | none (Q < 0 across the band) | -4.436 | -0.550 | -0.035 |
| 4T | 50 ohm | f < 8.65 GHz | 0.003 | 0.388 | -0.317 |
| 4T | short | f < 8.73 GHz | 0.154 | 1.361 | -0.347 |
| 2T | open | 21.82 – 29.04 GHz | -15.061 | -1.649 | -1.334 |
| 2T | 50 ohm | 1.07 – 20.67 GHz | -0.007 | -0.005 | 0.582 |
| 2T | short | f < 21.20 GHz | 0.070 | 0.696 | 2.744 |

Reading the table:

* The **4T with a 50 ohm or shorted port 2 is the usable configuration**: Q is
  positive from DC up to the loaded self-resonance at about 8.7 GHz, peaking at
  Q = 1.98 near 2.4 GHz (shorted). Above that the input turns capacitive and Q
  goes negative.
* **Do not leave the 4T port 2 open.** Both `c_ox` plates then sit in series
  with the winding and the input is capacitive over the whole 1 MHz–100 GHz
  sweep, so Q never becomes positive and there is no unloaded SRF to quote.
* The **2T is too small to be an inductor at low frequency with a 50 ohm
  load**: its 0.75 pF per-side plate capacitance makes the input capacitive
  below 1.07 GHz (Q(1 G) is -0.005). It only has a narrow open-port inductive
  window, 21.8–29.0 GHz, and a shorted-port window below 21.2 GHz. The 0.72
  metal Q at 1 GHz is not reached in a 50 ohm system.
* **Al vs Cu barely moves the boundary.** The 4T 50 ohm zero crossing is
  8.65 GHz for Al and 8.69 GHz for Cu: at these geometries the sign is set by
  the reactances, not by the series resistance. Al lowers Q inside the window
  (1.665 vs 2.616 metal Q at 1 GHz), it does not move where Q changes sign.

These windows are **model-dependent, not qualified**. `TR10_stackup.xml` is a
placeholder: dielectric thickness, substrate conductivity (10 S/m) and via
resistance are not foundry data, and `Rdc` is DC-only (no skin or proximity
effect). Re-extract the substrate network before treating 8.65 GHz as a
specification.

Reproduce with:

```bash
python3 flow/scripts/rf_metrics.py          # fT, fMAX, Q windows
python3 flow/scripts/rf_metrics.py --json   # same numbers, machine-readable
```

## 6. f_T and f_MAX

Both are extracted from two AC runs per bias point on the generated netlists
(no hand calculation): the gate is driven with the drain AC-grounded, then the
drain is driven with the gate AC-grounded, which gives all four y parameters.

* **f_T**: frequency where `|h21| = |y21/y11|` falls to 1 (output AC-shorted).
* **f_MAX**: frequency where Mason's unilateral gain
  `U = |y21-y12|^2 / (4*(Re(y11)*Re(y22) - Re(y12*y21)))` falls to 1.

Bias: `w=100u`, `l=1u` (Lmin), `nf=10` so `Rg = 7.92 ohm` from `rshg=95`,
`Vds = 5 V` (NMOS) / `-5 V` (PMOS), 27 C.

| Device | f_T peak | f_MAX peak (Rg = 7.92 ohm) | f_MAX at the same bias, Rg = 0.1 ohm |
| --- | --- | --- | --- |
| NMOS | 2.67 GHz @ Vg = 4.5 V | 4.46 GHz @ Vg = 3.5 V | 5.28 GHz |
| PMOS | 1.19 GHz @ Vg = 0.5 V | 2.13 GHz @ Vg = 1.5 V | 2.31 GHz |

f_T is set by `gm/(2*pi*Cgg)` and is **independent of Rg** (0.00 % drift from
0.1 to 792 ohm). f_MAX is not: at NMOS `Vg=4 V`, `Vds=5 V`,

| Rg (ohm) | 0.1 | 1 | 5 | 7.9 | 20 | 50 | 100 | 792 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| f_MAX (GHz) | 5.05 | 4.89 | 4.44 | 4.20 | 3.50 | 2.71 | 2.17 | 1.02 |

so the gate resistance — here the placeholder `rshg=95` — is the dominant
f_MAX limiter. The same signature shows up as a function of finger count
(`w=100u` total, so `Rg` falls as `1/nf^2`):

| nf | 1 | 2 | 4 | 10 | 20 |
| --- | --- | --- | --- | --- | --- |
| Rg (ohm) | 791.7 | 197.9 | 49.5 | 7.9 | 2.0 |
| NMOS f_MAX (GHz) | 0.99 | 1.72 | 2.74 | 4.27 | 4.89 |
| PMOS f_MAX (GHz) | 0.53 | 0.88 | 1.37 | 1.87 | 2.08 |

f_T stays within 2.47–2.80 GHz (NMOS) and 1.10–1.25 GHz (PMOS) across that
table, i.e. the finger count buys f_MAX, not f_T. Note `f_MAX > f_T` is
possible for a low-Rg finger and is not a bug.

**Caveat.** These are small-signal estimates from the uncalibrated BSIM3
baseline, with no measured ft/fmax data behind them. The f_MAX column inherits
the `rshg=95` placeholder; replace it with a measured gate-poly sheet
resistance before quoting f_MAX.

## Engineering placeholders

| Parameter | Where | Value | Replace with |
| --- | --- | --- | --- |
| `rshg` (gate poly) | `NMOS_nf`/`PMOS_nf` | 95 ohm/sq | measured gate-poly Rs |
| `esr` (plate) | `F_CSIO_rf` | 47 ohm | measured ESR |
| `rsub` (cap) | `F_CSIO_rf` | 1 kOhm | substrate extraction |
| `rsub`, `csub` (inductor) | `IND_PI` | 500 ohm, 0.05 pF | substrate extraction |
| substrate conductivity | stackup | 10 S/m | foundry stackup |
| metal conductivity | `inductor_geom.py` | `al` = 35 MS/m (thin film); `cu` = 58 MS/m | foundry resistivity |
| M1/M2 sheet R, V1 R | `inductor_geom.py` | Al 0.0829 / 0.0497 ohm/sq; 1 ohm/cut | foundry data |
| `mj`, `pb` (junction varactors) | `models_IP62_varactor.lib` | 0.5, 0.9 V | measured C-V |

## LVS constraints

* `connect_global(WN,"VDD")` ties every n-well to VDD. The CSIO well plate
  (`sub` on `F_CSIO_rf`) and the PMOS varactor body (`bw`) are therefore
  VDD-referenced.
* `NMOS_var` and `DN_var` bodies are the p-substrate (VSS).

## ngspice notes

* **Diode AC bug (ngspice 44.2).** With `rs > 0` and a large `cj`, the
  operating-point `cd` is correct but the AC current collapses (~1e-23 A).
  The junction models therefore set `rs=0` and put the series resistance in an
  explicit `Rser`. Do not "fix" that back to `rs=`.
* The first line of a SPICE file is the title; a `.include` or `.model` on
  line 1 is silently ignored.
* Subcircuit instance parameters cannot contain `/`; compute the division
  inside the subckt (this is why the wrappers use `wf='w/nf'`).
* `c` is a reserved constant in ngspice expressions; use another name for a
  capacitance vector.
* `max()` takes exactly two arguments; use `vecmax()` for vector reduction.

## Verification

```bash
bash flow/checks/test_rf_models.sh        # 33 assertions, all five items
python3 flow/checks/test_rf_metrics.py    # 17 assertions, fT/fMAX/Q sign
bash flow/checks/test_inductor_pcell.py   # needs klayout -b -r
bash flow/checks/run_all.sh test_rf_models.sh test_rf_metrics.py
```

`test_rf_models.sh` compares against the baseline device, an analytic value or
a geometry-derived value — not against a hardcoded copy of the overlay. The
inductor section also runs the KLayout DRC deck
(`libs.tech/klayout/tech/drc/run.drc`) on each generated layout and requires
zero items. `test_rf_metrics.py` asserts the physics rather than frozen
numbers: f_T is independent of Rg while f_MAX falls with it, the Al/Cu
metal-only Rdc ratio is exactly 58/35, and the Q sign crossings land in the
windows above.

Not covered in this round: noise analysis (flicker/thermal noise of the RF
devices), dielectric loss, inductor skin/proximity effect, and any measured
de-embedding data.
