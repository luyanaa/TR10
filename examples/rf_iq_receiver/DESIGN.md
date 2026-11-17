# TR10 experimental direct-conversion I/Q receiver

Engineering example, not a product. It exists to exercise the TR10 RF models
and to show a complete AM / SSB / FM signal chain built from PDK devices.

## Architecture

```
RF 50 ohm
  -> RX_LNA      grounded-source + ideal LC tank + source follower, AGC 0..20 dB
  -> balun       ideal 1:1, 25 ohm per side
  -> RX_MIXER    4-phase 25% duty passive NMOS switches
  -> RX_TIA_I/Q  shunt-feedback NMOS, programmable Rf/Cf
  -> RX_AM       I/Q half-wave rectifier + sum + 4.5 kHz LPF
  -> RX_FM       RC differentiator + two Gilbert multipliers (+ RX_FM_LPF)
  -> RX_SSB      RC polyphase + differential summing pair
  -> audio
```

Pass 1 uses an ideal 4-phase LO so the mixer/TIA/demodulator chain can be
verified before the VCO/PLL is added. Pass 2 replaces it with the
transistor-level VCO (divide-by-2 and PLL are the remaining work).

## Locked parameters

| Block | Parameter | Value |
| --- | --- | --- |
| Global | supply / temperature | 5.0 V, 27 C, typical |
| | band points | 0.1 / 1 / 10 / 100 MHz, optional 500 MHz |
| | modes | AM (m=0.5), SSB (USB/LSB), FM (+-75 kHz wide / +-2.5 kHz narrow) |
| | passives | ideal L/C, tank Q=20 (configurable) |
| LNA | device | `NMOS_nf` 200u/1u, nf=10, Id=2 mA, gm ~ 6.4 mS |
| | tank | f_c, Q=20, L=15.9u*1e6/fc, R_p=2 kohm, 19.9 dB at 1 MHz |
| | AGC | continuous 0..20 dB by gate bias 0.77..1.35 V (60 uA..2 mA) |
| | buffer | source follower 200u/1u, 4 mA, Zout ~ 100 ohm |
| VCO | topology | cross-coupled NMOS 200u/1u nf=4, tail 1 mA |
| | tank | 2*f_lo, Q=5, L=15.9 uH per half (31.8 uH diff), C=386 pF per half |
| | tuning | two NMOS_var 2400u/1u nf=16, 0..1 V control (C-V saturates above 1 V) |
| | measured | 2.000 MHz free running at vtune=0.5 V, 1.25 Vpp differential |
| Mixer | topology | 4-phase passive NMOS 200u/1u, Ron ~ 25 ohm |
| TIA | topology | shunt-feedback NMOS 200u/1u nf=10, Iload=2 mA |
| | settings | AM 10k/3.5nF (4.5k); SSB 22k/3.0nF (2.4k); FM wide 22k/80pF (90k); FM narrow 22k/1.16nF (6.25k) |
| AM | demod | I/Q half-wave rectifier + sum, 1.55 V divider reference, 4.5 kHz LPF |
| FM | demod | RC differentiator 10k/50p (0.5 us) + two Gilbert cores, 4.7k loads |
| SSB | demod | RC polyphase 10k/5.3n (3 kHz) + differential pair, 10k loads |
| Audio | load | high impedance, AC coupled, target 0.1..1 Vpp |

The FM TIA corner is 90 kHz because the I/Q baseband is complex: +-75 kHz
deviation plus 15 kHz audio occupies +-90 kHz. The 180 kHz figure is the RF
channel bandwidth, not the baseband corner. The 22k/80pF setting gives the
same 90 kHz corner as 4.7k/375pF with 4.7x more transimpedance, which the
FM demodulator needs.

### Why the TIA is not an op-amp

`RX_OPAMP` (two-stage Miller) has a ~172 mV input offset. With the 25 ohm
switch resistance that drove ~7 mA through the feedback network and railed
the output. The shunt-feedback NMOS stage has no differential-pair offset:
its input sits at the device Vgs (~1.35 V), and the balun/mixer common mode
must be set to the same value. A production receiver would add a CMFB servo.

### Why the LNA AGC is gate bias

A single-ended common-source stage cannot put its source on an ideal current
sink: the source node floats at AC, Vgs stays constant and gm collapses.
AGC therefore varies the gate bias, not a source-degeneration current.

### FM wide needs a wide LNA tank

With the default Q=20 tank the LNA bandwidth is 54 kHz. An FM signal with
+-75 kHz deviation occupies 180 kHz, so the tank turns the FM into AM: the
TIA envelope collapsed to zero at the deviation peaks. The FM testbench uses
`RX_LNA q=5` (200 kHz tank). A product would switch the tank Q or use a
separate wideband front end per mode.

### FM demod and the 2*f_lo image

A single-ended 4-phase passive mixer leaves the upconverted image at 2*f_lo
on each TIA output (about 20 mV for a 1 mV RF input). The Gilbert product of
that image with itself would bury the audio, so `RX_FM_LPF` (two poles at
~300 kHz, one per channel) sits between the TIA and the demodulator. A
shared filter node would short I to Q and cancel the cross product.

## Interface contract

All blocks use `vdd=5`, `vss=0`, analog common mode `vcm=2.5 V`.

| Signal | Level / impedance |
| --- | --- |
| RF input | 50 ohm source, 1 mV amplitude nominal |
| LNA output | single-ended, 2.65 V bias, ~10 V/V (19.9 dB), Zout ~ 100 ohm |
| Balun output | differential, 1.354 V CM (TIA input bias), 25 ohm per side |
| LO | 4 phases 0/90/180/270, 25% duty, 0/5 V |
| Mixer output | virtual ground at ~1.35 V (TIA input) |
| TIA output | ~1.55 V DC + audio, Rf * I_mixer |
| FM demod input | ~100 mV I/Q, differential | 
| Audio | high impedance, AC coupled |

## Measured results (1 MHz, 1 mV RF)

| Test | Result |
| --- | --- |
| LNA | 19.91 dB, 54.4 kHz loaded BW, AGC 0.47..9.90 V/V |
| mixer+TIA | 2.56/2.50 mV at 3 kHz for AM m=0.5, 6 kHz/3 kHz = 0.7 % |
| AM demod | 381 mV from a 25 mV envelope, THD(2,3) = 0.83 % |
| full AM chain | 260 mV at 3 kHz, THD(2,3) = 0.53 % |
| SSB demod | 231 mV selected, 51.3 dB rejection at fc |
| SSB sweep | rejection 6 dB at 1 kHz, 14 dB at 2 kHz (single-pole polyphase) |
| FM demod | 48 mV at 3 kHz for 100 mV I/Q at 75 kHz deviation, THD 3.9 % |
| full FM chain | ~1 mV at 10 kHz; limited by the mixer I/Q gain mismatch |
| VCO | 2.000 MHz at vtune=0.5 V, 1.25 Vpp differential |
| LO divider | divide-by-2 confirmed, 4 phases 26.0/26.4/27.0/26.9 % |

The FM chain's small audio and 2f residue come from the mixer I/Q gain
mismatch (I=8.0 mV vs Q=11.1 mV in the AM test). The Gilbert cross product
cancels the 2f terms only when I and Q match, so a production receiver needs
I/Q gain/phase calibration (or a polyphase filter) ahead of the FM demod.

## PDK / simulator notes

* Include `libs.tech/ngspice/models/ip62_models_rf`.
* `NMOS_nf` / `PMOS_nf` are subcircuits with pin order `(d g s b)`: use
  `X... NMOS_nf ...`. The transmission-gate clock and signal pins are easy
  to swap because of this order.
* Set `rgval=1` on every analog MOS. `rgval=0` makes ngspice clamp the
  internal gate resistor to 1e-12 ohm and the DC operating point fails.
* Use `w=... l=... nf=...`; `nf` splits the width into fingers.
* The first line of a SPICE file is the title.
* Ideal tank: parallel R_p = Q*omega*L across the LC; series R_s = omega*L/Q
  for a series tank.
* A capacitor/differentiator into a MOS gate needs a DC path to the bias
  node; the bias divider must be bypassed or its impedance shifts the filter
  corner (a 2.1 kohm divider pulled the SSB high-pass from 45 deg to 38 deg).
* The 1 uF coupling caps have a 0.1 s time constant with 100 kohm, but the
  DC operating point already sets their voltage, so the 1 ms transients do
  not show a settling tail.


## Layout: RX_TIA (DRC / LVS / PEX)

`layout/` contains a physical implementation of the TIA block in the TR10
drawing layers, generated by KLayout python (`gen_tia.py`) and signed off
with the PDK's own decks:

```
gen_tia.py      -> rx_tia.gds   (one NMOS, W=200u L=1u as 10 fingers of 20u)
klayout run.drc -> 0 violations
klayout run.lvs -> TR10_LVS PASS against rx_tia.strict.cir
magic PEX       -> pex/rx_tia.spice (10 fingers + node capacitances)
run_signoff.sh  -> the whole chain (checks/test_layout.py)
```

Geometry notes: the device is a single-strip multi-finger NMOS (one AN strip
of height 20 um per finger with 1 um gates on a 4 um pitch); the DRC limits a
single finger to 60 um, so the 200 u device needs 10 fingers, and the LVS
combiner sums them back to W = 200 u.  S/D contacts sit centred in the 3 um
segments (1.0 um from each gate) and within 1.8 um of the active edge; the
P-well backgate tie (AP + CO, VSS) clears the floating-p-well ERC.

PEX-driven iteration: the first extraction showed the node capacitance
dominated by the 30x30 um pads (areacap metal1 = 35 aF/um^2 gives ~31 fF per
pad).  Shrinking them to 16x16 um cut every net capacitance by 38-42 %:

| net | PEX1 | PEX2 |
| --- | --- | --- |
| IN  | 65.45 fF | 39.10 fF |
| OUT | 74.25 fF | 46.21 fF |
| VSS | 76.28 fF | 53.29 fF |

For the 4.57 kHz TIA the effect is electrically invisible (40 fF at 100 MHz
is 24 kohm against a 150 ohm input impedance); the same node structure is
what the RF blocks reuse, where it does matter.  Two caveats are recorded in
the sources: the PDK's Magic tech is streamout-only by design (device
connectivity extraction is not complete), and the layout check (`checks/
test_layout.py`) runs the full signoff chain separately from the circuit
regression.

## Layout: all receiver blocks (DRC / LVS / PEX)

Every block of the AM chain plus the VCO is laid out in the TR10 drawing
layers, generated by KLayout python, and signed off with the PDK decks:

```
gen_modules.py  -> rx_{lna,mixer,ssb,fm,vco,amdemod}.gds + .strict.cir
gen_tia.py      -> rx_tia.gds
run.drc         -> 0 violations per module (7/7)
run.lvs         -> TR10_LVS PASS per module (7/7)
magic PEX       -> pex/rx_<mod>.spice (devices + node capacitances)
run_signoff.sh  -> the whole chain (checks/test_layout.py)
```

`rxlib.py` is the device library: a single-strip multi-finger MOS (one AN
strip of height Wf, 1 um gates on a 4 um pitch, 3 um S/D segments) plus the
routing primitives.  The device lists in `gen_modules.py` mirror the
pre-layout spice `.lib` files exactly (same W/L/nf and terminal-to-net map),
and the strict LVS contract is emitted from the same list, so layout and
schematic cannot drift.

| module | devices (W/L, nf) | DRC | LVS | PEX |
| --- | --- | --- | --- | --- |
| tia | 1 NMOS 200u/1u nf=10 | 0 | PASS | 10 dev, 13 caps |
| lna | 2 NMOS 200u/1u nf=10 | 0 | PASS | 20 dev, 30 caps |
| mixer | 4 NMOS 200u/1u nf=10 | 0 | PASS | 40 dev, 59 caps |
| ssb | 2 NMOS 100u/1u nf=4 | 0 | PASS | 8 dev, 15 caps |
| fm | 12 NMOS 100u/1u nf=4 | 0 | PASS | 48 dev, 117 caps |
| vco | 2 NMOS 200u/1u nf=4 + 2 varactors 9600u (160 x 60u) | 0 | PASS | 328 dev, 339 caps |
| amdemod | 8 NMOS 100u/1u nf=4 + 4 PMOS 50u/2u nf=4 | 0 | PASS | 48 dev, 109 caps |

Layout rules that drove the geometry (all from the PDK KLayout deck):

- **CO.GG / CO.SM** are extraction-convention rules: every S/D contact must
  be either a 1.0 um-pitch interior contact or an end contact with <=1.8 um
  of active enclosure, and every gate must carry a contact.  The contact
  column is therefore placed with symmetric margins in [1.0, 1.8] um and the
  gate bus carries one CO at its right end (the pattern that passes).
- **GA.CO / ERC_FLOATING_GATE / GC.ANT** clear only when the gate net is
  named: a floating gate is an ERC error unless a top-level label ties it to
  the interface.  Every module labels all of its nets.
- **V1.M1** needs 1.0 um of M1 enclosure and **V1.GA** 1.2 um of poly
  clearance, so V1 is a 1.4x1.4 um cut on a 3.6 um M1 stub, and the first M2
  trunk starts past the widest gate bus.
- **WN.AN / AN.WN / WN.S7**: a PMOS well must enclose its N+ tap by 5 um,
  stay 10 um from neighbouring NMOS active and 12 um from the next well
  island; the PMOS rows are therefore spaced 30 um apart.
- **ERC_FLOATING_PWELL**: the P+ backgate tie must sit above the device row
  and reach the vss trunk without crossing any device M1 strip (a crossing
  shorts every net to vss -- this was the one real connectivity bug found by
  LVS during the work).

Routing: each net gets one vertical M2 trunk at a dedicated x, 6 um apart,
fed by 3.6 um M1 stubs through 1.4 um V1 cuts.  M2 does not interact with
the M1 device strips, so the M1.SW/M1.W1 wide-metal rules never fire.

### Post-layout simulation (hybrid PEX)

Magic's device connectivity extraction is streamout-only in this PDK (the
tech self-describes as such), so the post-layout view is built the same way
as for the TIA: the LVS-verified device netlist plus the extracted node
capacitances on the labelled nets.  `scripts/gen_post_am.py` reads
`layout/pex/rx_<mod>.spice` and emits `spice/post_am.lib` (LNA, mixer, TIA,
AM demod) and `spice/post_vco.lib`; the dangling `a_*#` finger-diffusion
nodes are dropped.

Extracted substrate capacitance on the signal nets:

| module | net | C |
| --- | --- | --- |
| lna | d / out / vdd / g / vss | 73.6 / 54.5 / 42.2 / 29.5 / 62.5 fF |
| mixer | rf_n / rf_p / out_q / out_i | 117.3 / 111.8 / 93.0 / 79.2 fF |
| tia | out / in / vss | 46.2 / 39.1 / 53.3 fF |
| ssb | tail / out_n / q_hp | 71.0 / 26.5 / 22.8 fF |
| fm | out_n / vref2 / t4 / out_p | 173.1 / 166.4 / 161.9 / 161.5 fF |
| amdemod | vss / d4 / vdd / d2 | 208.0 / 200.9 / 163.7 / 145.7 fF |
| vco | out_n / out_p / vtune / tail | 2.67 p / 2.66 p / 619 f / 390 fF |

**End-to-end AM chain, 1 MHz carrier, m=0.5, 3 kHz audio, 1 mV RF in**
(`tb_am_1m.sp` vs `tb_am_1m_post.sp`, last audio period):

| metric | pre-layout | post-layout | delta |
| --- | --- | --- | --- |
| audio at 3 kHz | 260.0 mV | 261.6 mV | +0.60 % |
| THD(2,3) | 0.53 % | 0.66 % | +0.13 pp |
| audio DC | 2.320 V | 2.373 V | +53 mV |
| tia_i max / min | 1.634 / 1.522 V | 1.635 / 1.523 V | +1 mV |
| lna_out at 1 MHz | 4.3 mV | 4.3 mV | 0 |
| rf_in at 1 MHz | 4.3 mV | 4.3 mV | 0 |

The input path (50 ohm source, LNA tank, balun) is unchanged: the extracted
tens of fF sit against a 1 MHz tank of 349 pF and a 25 ohm balun.  The audio
gain moves by 0.6 % and the distortion by 0.13 pp, both from the demodulator's
1.3 pF of extracted node capacitance slowing its 4.5 kHz output pole.

**VCO free running post-layout** (`test_vco.sp` vs `tb_vco_post.sp`,
2-5 us window): 1.9918 MHz -> 1.9855 MHz (-0.32 %), swing 1.119 -> 1.120 Vpp.
The tank carries 2.66 pF of varactor drain/source diffusion against its
349 pF tuning capacitance, which predicts -0.38 % -- the measured shift
matches.  One caveat: the 1 um flow has no deep n-well, so the varactor
bulk is the substrate (vss) rather than the tank node of the abstracted
`NMOS_var` model; the junction capacitance therefore lands on vss in the
extraction instead of on the tank.  The gate/drain assignment does follow
the model (gate = vtune, drain/source = tank).

## Results and regression

```bash
python3 examples/rf_iq_receiver/checks/test_rx.py --full      # 33 checks
python3 examples/rf_iq_receiver/checks/test_layout.py         # 7 modules DRC/LVS/PEX
```

`test_rx.py --full` includes the pre-layout AM chain, the post-layout AM
chain (extracted parasitics) and the post-layout VCO.  `test_layout.py`
regenerates every layout and runs the full signoff chain; it fails on any
DRC violation or LVS mismatch.

## Pass plan

1. **Sketch** (done) - 1 MHz AM end to end with an ideal LO: LNA, passive
   mixer, TIA (AM setting), AM demodulator, transient + FFT.
2. **Structure** (done) - transistor VCO, divide-by-2 / 25 % duty generator,
   FM and SSB demodulators, and the closed PLL loop (see below).
   `RX_LO_GEN` provides a behavioral 25 % duty source for cross-checks.
3. **Layout** (done) - all seven blocks DRC-clean, LVS-clean and PEX'd;
   the AM chain and the VCO are re-simulated with the extracted parasitics.

### PLL: PFD + charge pump + loop filter

`pll.lib` implements a proper two-DFF phase-frequency detector and a
charge pump:

* `DFF_R` is a master-slave latch pair with an asynchronous reset that
  clears *both* latch states (clearing only the slave lets the still-high
  master re-set it).
* `PFD` asserts UP on a REF rising edge and DN on an FB rising edge; the
  reset is `(UP AND DN) OR ~POR`.  The power-on reset is required: without
  it the latches power up set and the PFD settles into the false DN-wide
  state.  A four-inverter reset chain sets a few-ns reset pulse.
* `CP` is a resistor charge pump (10 k source / 7 k sink, about 300 uA at
  the 2.05 V lock point).  An ideal current source in series with the
  switch leaves a floating source node whose ~50 fF must swing between vdd
  and vout on every pulse; that swallows the PFD's few-ns pulses and
  creates a dead zone.  The pump output is also buffered, because the
  asymmetric switch gate capacitance delays the PMOS turn-on and biases the
  effective UP/DN widths.

Loop filter: type-II, C1 = 1 nF, R1 = 50 k, C2 = 100 pF, with
`wn = sqrt(Kphi*Kv/(N*C1)) ~ 7.7 kHz`, `zeta = wn*R1*C1/2 ~ 1.2` and the
zero at 3.2 kHz.  The VCO reaches 2.000 MHz at vtune = 2.05 V (measured
ramp) and the pump is balanced at the same point (rp = 10 k, rn = 7 k);
that alignment is what lets the loop settle instead of hunting against a
clamp.  The tuning node is clamped to 1.7..4.2 V because outside that
window the varactor is in accumulation (Kv -> 0) or the pump runs out of
headroom.

Measured PFD characteristic (`test_pfd.sp`): +90 deg gives UP = 1.283 of
5 V (ideal 1.25), -90 deg gives DN = 1.283, 0 deg gives 0.035 on both
(the reset pulse), and the characteristic wraps outside +-180 deg as
expected.  Frequency steering (`test_pfd_freq.sp`): a 0.995 MHz FB gives
UP = 1.40 / DN = 0.03, a 1.005 MHz FB gives UP = 0.03 / DN = 1.41.

Closed-loop lock (`tb_pll.sp`, 2 ms): the VCO runs at 2*f_ref and the
divide-by-2 output holds phase with the reference.

```
window 50..600 us       fb 550, ref 550   (difference 0 -> no cycle slip)
window 1100..1999 us    fb 899, ref 899   (difference 0 -> no cycle slip)
phase (ref -> fb)       mean 0.50 us, std 0.40 us
vtune                   2.09 V mean, 0.31 V pp ripple
```

The edge counts are the lock evidence: the divider output and the reference
advance by the same number of cycles in each window, so the VCO stays at
exactly 2*f_ref instead of slipping.  The `-1` seen when counting the whole
2 ms window is the window-edge artefact of the first partial period.

The pump balance, the type-II zero and the aligned 2.05 V operating point
are each necessary: removing the zero or moving the pump balance to
2.65 V leaves a +0.7..1.3 kHz residual at a clamp.  The 0.31 V ripple (and
the resulting 0.4 us phase jitter) comes from the 200..300 uA pump pulses
into a 100 pF smoothing cap; a lower pump current or an extra smoothing
pole would reduce it at the cost of a slower pull-in.

* The NMOS varactor C-V saturates above Vgs ~1 V, so the VCO gain is only
  ~23 kHz/V even with 9600u varactors.  The tank trim (ch = 0.8767) puts
  2.000 MHz at vtune = 2.05 V and the clamp keeps the varactor out of the
  accumulation region.  A wider, more linear C-V would raise Kv and shorten
  the pull-in.
* The 0.31 V pump ripple gives a 0.4 us rms phase jitter at lock; a lower
  pump current or an extra smoothing pole would reduce it.
* The divider's 25 % duty is 26-27 % because the clock buffer duty is 44 %
  and the latch delays differ by phase.  A duty-cycle trim or a faster
  latch would tighten it.
3. **Detail** - 0.1 / 1 / 10 / 100 MHz x AM/FM/SSB, AGC sweep, programmable
   TIA bank, optional 500 MHz, docs and regression test.
