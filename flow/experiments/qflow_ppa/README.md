# qflow (GrayWolf + qrouter) vs LibreLane/OpenROAD on TR10_cmp_sc

Experiment: route the **same mapped design** with two independent place-and-route
flows and compare PPA.

* qflow 1.4.104: GrayWolf 2.2 placement + qrouter 1.4.90.T detailed routing.
* LibreLane + OpenROAD: the existing `examples/tr1um_fifo4_cmp` flow (OpenROAD
  global/detailed routing, KLayout DRC, KLayout LVS).

Reference for the qflow technology layout: the sky130 qflow template
`fossi-foundation/open-pdks/sky130/qflow/{sky130.sh,sky130.par,sky130osu.sh}`.
The TR10 technology script and `.par` here are the adapted versions.

## What was compared

The mapped netlist is the LibreLane output:

```
examples/tr1um_fifo4_cmp/runs/tgmux/06-yosys-synthesis/tr1um_fifo4_cmp.nl.v
```

It contains 87 cells (20 EDFF, 1 DFF2, 1 DFF, 1 MUXTG2, 1 TIEHI, 63
combinational cells), with all power pins stripped.  Both flows use exactly
these cells and this connectivity.

qflow's own synthesis could not be used: the locally installed Yosys 0.52
segfaults on the TR10 Liberty:

```
read_liberty -lib libs.ref/TR10_cmp_sc/lib/TR10_cmp_sc__typ_5p0V_25C.lib
Segmentation fault
```

Feeding the LibreLane mapped netlist to qflow isolates the **placement and
routing** comparison, which is the question here.

## qflow setup

qflow finds a project-local technology directory `tech/tr10cmp`:

```
tech/tr10cmp/tr10cmp.sh             # LEF/TLEF/Liberty/GDS/SPICE + cell roles
tech/tr10cmp/tr10cmp.par            # GrayWolf layer/via rules and row parameters
tech/tr10cmp/TR10_cmp_sc_qflow.lef  # qflow cell LEF (TIEHI/TIELO duplicate OBS removed)
tech/tr10cmp/TR10_tech_qflow.tlef   # qflow tech LEF, 5.4 um routing grid
tech/tr10cmp/TR10_tech_qflow_2um.tlef  # 2.0 um grid experiment
```

`tr10cmp.sh` uses absolute paths into this PDK for Liberty/GDS/SPICE and the
qflow-specific LEF/TLEF in this directory.  The key technology values are
from `TR10_tech.tlef`:

| layer | direction | width | space | pitch |
|---|---|---|---|---|
| M1 | horizontal | 1.8 | 1.4 | 5.4 |
| M2 | vertical | 3.4 | 2.0 | 5.4 |
| V1 | cut | 1.4 | 1.5 | — |

The TR10 cells are 59.4 um tall and use a 5.4 um site.  Signal pins are M2;
the signoff LEF has a full-cell M1/V1 obstruction.

### qflow-specific LEF / routing-grid port

The first qflow attempt used the signoff LEF and the 5.4 um routing grid.  The
TIEHI/TIELO macros contain an `OBS` shape identical to their M1 signal pin;
qrouter therefore reports `edff_tie/HI ... has no tap points`.  The port adds a
qflow cell LEF with those duplicate OBS shapes removed, plus qflow-specific
tech LEFs for grid experiments.

Measured router results on the same 87-cell netlist / OpenROAD placement:

| qflow router configuration | failed nets |
|---|---|
| 5.4 um grid, signoff LEF | 9 / 118 |
| 5.4 um grid, qflow LEF (TIEHI OBS removed) | 9 / 118 |
| 2.0 / 1.0 / 0.1 um grid | qrouter did not finish in 20 min (grid explosion) |

The remaining failures include `edff_rstb_tie` (TIEHI HI is an M1 pin that
touches the VDD rail), `clk` (multi-row clock collisions), and several
`rd_ptr`/`wr_ptr`/`_*` nets.  A complete port still needs a TIEHI cell with a
separate M2 signal pad + V1, a clock-tree/NDR step, and a native GrayWolf
row/channel model.  `results/qflow_port_status.txt` records the exact state.

The qflow project was created with:

```bash
mkdir -p qflow/fifo/{source,synthesis,layout,log}
cp tr1um_fifo4_cmp.nl.v qflow/fifo/synthesis/tr1um_fifo4_cmp.rtlnopwr.v
cd qflow/fifo
qflow -T tr10cmp -p "$PWD" place tr1um_fifo4_cmp
qflow -T tr10cmp -p "$PWD" route tr1um_fifo4_cmp
```

## Results

### 1. qflow native flow

GrayWolf placed the 87 cells in 7 rows at 59.4 um pitch, i.e. rows abut with
**no routing channel**:

```
DIEAREA ( -10800 -10800 ) ( 496800 421200 )   # 507.6 x 432.0 um
93 components: 87 mapped cells + 5 FILL1 + 1 TIEHI
mapped-cell area = 196626 um^2
placement density = 89.7 % (196626 / 219283)
```

qrouter did not finish the design:

| run | failed nets |
|---|---|
| first  | **43 / 118** |
| rerun  | **51 / 118** |

Failures include `clk`, `edff_rstb_tie`, `data_out[*]`, `_032_`, and several
`mem*` nets.  There is no trustworthy `*_route.def` for signoff.

### 2. qflow with row spacing / qrouter on a routable placement

Adding row spacing by qflow's `.par` knobs did not produce a usable result:

* `rowSep 178.2` → die 3369.6 x 5362.2 um (row/tile warnings, unusable);
* `rowSep 59.4` → die 3369.6 x 1830.6 um; qrouter still **56 / 118** failed;
* post-shifting the native components to a 237.6 um row pitch and stripping
  the OpenROAD `SPECIALNETS` before qrouter: **109 / 118 routed, 9 failed**
  (`edff_tie/HI`, `clk`, and a few `_*` nets have no tap points).  This is a
  partial route only.

So even when qrouter is given the **same OpenROAD placement**, it cannot
finish the TR10 netlist.  The remaining failures are pin/tap handling, not
only congestion.

### 3. OpenROAD / LibreLane (reference)

Same netlist, existing `runs/tgmux` flow:

| metric | value |
|---|---|
| die | 760 x 1570 um = **1,193,200 um^2** |
| stdcell area incl. 42 TAP2 | **224,211 um^2** |
| utilization | **19.77 %** |
| DRT | **0** |
| KLayout DRC | **0** |
| KLayout LVS | **PASS** |
| power (typ, default activity) | **194.1 uW** |
| setup WNS / TNS | **0 / 0** |
| setup slack | 4751.78 (5 us clock) |
| hold WNS / TNS | **0 / 0** |

The OpenROAD die is 5.44x larger than the qflow placement die, and the
utilization is 4.6x lower, but the design is actually routed and signed off.

## PPA analysis

| metric | qflow native | qflow qrouter on OpenROAD placement | OpenROAD |
|---|---|---|---|
| mapped-cell area | 196,626 um^2 | 196,626 um^2 | 196,626 um^2 |
| die area | 219,283 um^2 | 1,193,200 um^2 | 1,193,200 um^2 |
| placement density | 89.7 % | 19.8 % | 19.8 % |
| routed nets | 75/118 (43 failed) | 109/118 (9 failed) | **118/118** |
| post-route timing | invalid | invalid | WNS 0, TNS 0 |
| post-route power | invalid | invalid | 194.1 uW |
| DRC / LVS | not run (unrouted) | not run (unrouted) | **0 / PASS** |

**The qflow PPA numbers are not realizable.**  The native GrayWolf placement
looks 5.4x smaller and 4.5x denser than the OpenROAD result, but it leaves 43
of 118 nets unrouted.  The area advantage is an artifact of abutting 59.4 um
tall cells with no M1/M2 channel.  The OpenROAD 237.6 um row pitch is the
cost of making the TR10 cell architecture routable; its 19.8 % utilization is
the only complete PPA point in this experiment.

### Why qflow fails here

1. **Cell architecture.**  TR10_cmp_sc cells are 59.4 um tall with a
   full-cell M1/V1 obstruction and M2-only signal pins.  GrayWolf's
   row-abutting placement leaves no M1/M2 channel; qrouter cannot access the
   pin band.  OpenROAD uses a 237.6 um row pitch (178.2 um channel).
2. **qflow row model.**  The native `.par` `rowSep`/`row_to_tile_spacing`
   knobs do not produce the TR10 channel/pitch correctly; attempts either
   explode the die or leave the qrouter failures.
3. **Pins/taps.**  qrouter on the OpenROAD placement still fails on
   `edff_tie/HI` and `clk` with “no tap points”.  qflow's LEF/pin/tap model
   does not handle the TR10 TIEHI and M2 clock pin distribution as-is.
4. **Synthesis.**  qflow's Yosys cannot read the TR10 Liberty (segfault), so
   a native qflow synthesis PPA is not available without a qflow/Yosys fix.

## Reproduce

```bash
cd flow/experiments/qflow_ppa
# qflow project (tech + netlist)
mkdir -p /tmp/qflow_tr10/fifo/{source,synthesis,layout,log}
cp -r tech/tr10cmp /tmp/qflow_tr10/fifo/tech/
cp /path/to/tr1um_fifo4_cmp.nl.v \
   /tmp/qflow_tr10/fifo/synthesis/tr1um_fifo4_cmp.rtlnopwr.v
cd /tmp/qflow_tr10/fifo
qflow -T tr10cmp -p "$PWD" place tr1um_fifo4_cmp
qflow -T tr10cmp -p "$PWD" route tr1um_fifo4_cmp
```

The raw placement DEF, route logs, qrouter-on-OpenROAD-placement log, and
the OpenROAD metrics are in `results/`.

## Recommendation

* Use the LibreLane/OpenROAD result as the TR10_cmp_sc PPA baseline.
* This port provides the qflow tech script, `.par`, qflow LEF and
  routing-grid experiments, but it is **not a complete route**: qflow still
  fails 9/118 nets at the best 5.4 um configuration.  The remaining work is
  a TIEHI cell with a separate M2 signal pad, clock-tree/NDR support, and a
  native GrayWolf row/channel model.
* Until that is done, qflow's smaller area/density numbers are not PPA
  evidence because the design is not routed; OpenROAD remains the only
  complete PPA point.
