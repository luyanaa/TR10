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

## Results and regression

```bash
python3 examples/rf_iq_receiver/scripts/run_cases.py          # 18 checks
python3 examples/rf_iq_receiver/scripts/run_cases.py --full   # + full AM chain
python3 examples/rf_iq_receiver/checks/test_rx.py
```

## Pass plan

1. **Sketch** (done) - 1 MHz AM end to end with an ideal LO: LNA, passive
   mixer, TIA (AM setting), AM demodulator, transient + FFT.
2. **Structure** (in progress) - transistor VCO, divide-by-2 / 25 % duty
   generator, FM and SSB demodulators done; the PLL closing remains open.
   `RX_LO_GEN` provides a behavioral 25 % duty source for cross-checks.

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
* `CP` is a resistor-based charge pump (10 k / 13.8 k, about 200 uA at
  2.9 V).  An ideal current source in series with the switch leaves a
  floating source node whose ~50 fF must swing between vdd and vout on
  every pulse; that swallows the PFD's few-ns pulses and creates a dead
  zone (measured as a 1 V limit cycle).  Resistors have no such node.

Measured PFD characteristic (`test_pfd.sp`): +90 deg gives UP = 1.283 of
5 V (ideal 1.25), -90 deg gives DN = 1.283, 0 deg gives 0.035 on both
(the reset pulse), and the characteristic wraps outside +-180 deg as
expected.  Frequency steering (`test_pfd_freq.sp`): a 0.995 MHz FB gives
UP = 1.40 / DN = 0.03, a 1.005 MHz FB gives UP = 0.03 / DN = 1.41.

The closed loop (`tb_pll.sp`) closes the 2 MHz VCO through the divide-by-2
onto the 1 MHz reference.  The VCO tuning was widened 4x (9600u varactors,
Kv = -23 kHz/V measured over 2.0-4.5 V), the tank trimmed with ch = 0.8767
and the charge pump balanced at 2.65 V (10k/11.3k).  The filter is a type-I
integrator (C1 = 2.2 nF, C2 = 22 pF, wn ~ 5 kHz); the tuning node is
clamped to 2.0..4.2 V because outside that window the varactor is in
accumulation (Kv -> 0) or the pump runs out of headroom.

Measured acquisition from an arbitrary starting phase: the frequency error
falls from 8.5 kHz (0.85 %) to 0.75 kHz (0.075 %) in 250 us; the tuning
voltage then sits on the 2.0 V clamp with a 1 mV ripple at the 0.75 kHz
residual.  Pulling the last 0.75 kHz in needs several beat periods
(1.3 ms each), i.e. several ms of transient, which is beyond the
affordable simulation time.  Every block is verified on its own, and the
remaining work is the VCO tuning range (a varactor with a wider, more
linear C-V would raise Kv and shorten the pull-in in proportion).
* The NMOS varactor C-V saturates above Vgs ~1 V and moves only ~0.15 % of
  the tank capacitance over the useful 0..1 V range.  The tank trim
  (ch factor 0.9529) centres the free-running VCO near 2.0015 MHz at
  vtune = 2.5 V, which leaves only a few kHz of correction range; a larger
  varactor is needed for a real capture range.
* The divider's 25 % duty is 26-27 % because the clock buffer duty is 44 %
  and the latch delays differ by phase.  A duty-cycle trim or a faster
  latch would tighten it.
3. **Detail** - 0.1 / 1 / 10 / 100 MHz x AM/FM/SSB, AGC sweep, programmable
   TIA bank, optional 500 MHz, docs and regression test.
