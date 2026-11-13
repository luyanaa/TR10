# c4004_cmp — upstream C4004 core reproduced end-to-end on TR10_cmp_sc

Reproduction of the Intel 4004 core published as
[`jun1okamura/TR-1um_C4004`](https://github.com/jun1okamura/TR-1um_C4004)
(pinned at `db826b1`) through LibreLane / OpenROAD on this PDK's compact
59.4 um standard-cell library (`libs.ref/TR10_cmp_sc`) and the SRAM128 hard
macro (`libs.ref/TR10_SRAM128`).

The point of the exercise is a *same-design* PPA comparison: the netlist,
cell placement, row pitch, die size, pinout and power-grid topology are
taken from the upstream sign-off, so the only free variable is the
implementation of the 24 standard-cell masters on TR10.  Nothing is
re-synthesised, re-placed by RePlAce, or clock-tree-synthesised — the
upstream hand placement already contains its own useful-skew clock tree.

## What is reproduced, and what is not

| element | upstream | here |
|---|---|---|
| netlist | `openroad/c4004_core_syn.v` | same file, `SYNTH_ELABORATE_ONLY` |
| cell count | 637 std + `SRAM128` = 638 | same (`num_cells_by_type` matches) |
| placement | 11 N rows, 145.8 um pitch, hand-optimised | `placements.tcl`, generated from the upstream DEF |
| TAP2 | 44 fixed instances | created by `manual_place.tcl` |
| FILL | 129 (`FILL3`/`FILL2`) at upstream coordinates | same (`post_dpl.tcl`, `RUN_FILL_INSERTION=false`) |
| die | 1840 x 1840 um | same |
| pins | 19, `METAL1`/`METAL2` | `src/c4004_pins.def` via `FP_DEF_TEMPLATE` |
| blockages | 14 | `ROUTING_OBSTRUCTIONS` |
| power grid | 22 M1 row rails + 8 M2 straps + SRAM rails | `post_pdn.tcl` |
| clock tree | inside the netlist | `RUN_CTS=false` keeps it |
| resizing/buffering | none | all resizers/repair off |

### Signoff scope

KLayout DRC (`libs.tech/klayout/tech/drc/run.drc`) and OpenROAD detailed
routing DRC are the signoff checks for this design, and both are clean:
OpenROAD reports `route__drc_errors 0` (iteration 34 of 40), and KLayout's
deck finds **0 rule violations**.  The deck's one remaining finding is the
`Warning: missing guardring CO` advisory (body-contact density inside the
imported SRAM128 guard ring), which cannot be fixed without editing the
upstream macro; `ERROR_ON_KLAYOUT_DRC` is therefore `false` for this example
and the metric is reported as `klayout__drc_error__count 1`.  The 24
standard-cell masters themselves are DRC clean (see the cell-level table in
`examples/tr1um_fifo4_cmp/README.md`).

Top-level LVS is **not** run, and this is a tool-contract limitation rather
than a known open defect:

- `flow/checks/test_klayout_lvs.sh` runs the PDK deck against *one* CDL
  (`libs.ref/<lib>/cdl/<lib>.cdl`).  The C4004 core needs that CDL **plus**
  `libs.ref/TR10_SRAM128/cdl/SRAM128.cdl`.
- `lvs_contract/build_core_lvs_contract.py` does not model a macro: the
  layout-vs-Verilog population check requires every extracted cell to be in
  the single Liberty (`--macro-contract` only appends to the CDL map, and the
  Liberty/population/physical-child checks still reject `SRAM128`), the pin
  parser only handles scalar nets (the macro uses `DIN[0]`..`DO[3]`), and it
  requires every CDL `X` child to exist as a physical cell.
- The macro itself cannot be compared hierarchically either: the GDS cells
  are named `SRAM_PDEC`, `BIT_32`, `SRAM_DEC`, ... while the CDL subcircuits
  are `PDEC`, `BIT_CELL`, `DEC`, ..., so `align` pairs nothing.

The 24 standard-cell masters are verified individually (KLayout DRC + LVS,
see `examples/tr1um_fifo4_cmp/README.md` cell-level table), and SRAM128 is
used as an unchanged upstream hard macro.  Extending the LVS contract to
blackbox macros is tracked as separate work; it is not needed for the PPA,
IR-drop or CTS comparison this example targets.

## Files

| file | role |
|---|---|
| `config.json` | LibreLane configuration (macro, obstructions, PDN, SDC, step switches) |
| `src/c4004_core_syn.v` | upstream gate-level netlist (verbatim) |
| `src/SRAM128_bb.v` | blackbox port contract for Yosys elaboration |
| `src/c4004_pins.def` | DIEAREA + 19 pins (template for `FP_DEF_TEMPLATE`) |
| `placements.tcl` | generated `$C4004_ROWS` / `$C4004_PLACE` (do not hand-edit) |
| `manual_place.tcl` | GPL hook: rebuild 11 rows, place 811 objects, `FIRM`, global connections |
| `pdn_c4004.tcl` | `pdngen` topology (11 M1 row pairs + 4 M2 column pairs) |
| `post_dpl.tcl` | re-insert the 129 upstream fillers after DPL deletes them |
| `post_pdn.tcl` | rebuild the upstream PDN geometry after `pdngen` |
| `constraints.sdc` | 35.088 ns clock, 0.5 ns uncertainty, 2 ns I/O, 1 pF load |
| `vsrc_vdd.loc`, `vsrc_gnd.loc` | IR-drop voltage sources (strict CSV, no comments) |
| `run.sh` | three-stage driver (place -> guide -> route/signoff) |

Regenerate the derived placement files with

```bash
python3 ../../flow/scripts/gen_c4004_placement.py
```

and the macro views with

```bash
python3 ../../flow/scripts/build_sram128_views.py   # LEF/LIB/SPICE/GDS
```

## How to run

```bash
cd examples/c4004_cmp
./run.sh t1
```

`run.sh` bind-mounts four patched LibreLane scripts (`gpl.tcl`, `dpl.tcl`,
`drt.tcl`, `pdn.tcl`) over the container copies — without them the flow runs
stock global placement (no `manual_place.tcl` hook), stock detailed
placement (which deletes the fillers and does not run `post_dpl.tcl`) and
stock PDN (no `post_pdn.tcl` hook); PSM then fails with `PSM-0038/0039/0069`.

The final stage also passes `--skip Magic.WriteLEF --skip
Odb.CheckDesignAntennaProperties --skip Magic.SpiceExtraction`.  magic cannot
load the upstream SRAM128 views at all: its GDS reader rejects the `235/0`
outlines and the `AREF` arrays, and its LEF parser rejects the `POLYGON` pin
shapes, so `Magic.WriteLEF` and `Magic.SpiceExtraction` abort with `Error
while reading cell` / `Missing Y value` (lines LibreLane treats as fatal), and
the antenna lint that consumes the LEF has nothing to read.  None of the three
contributes to the sign-off evidence here — KLayout writes the GDS and runs
the DRC, OpenROAD RCX extracts the parasitics — so they are skipped by
design, not worked around.

Resuming is *not* a rewind: `librelane --from <step>` loads the newest
state snapshot in `runs/<tag>`, so asking for `--from
OpenROAD.DetailedRouting` on a tag that already routed resumes from the
routed ODB and only re-anneals the leftover violations.  To exercise a
changed DRT setting from scratch, run with a fresh tag (or re-run `--to
OpenROAD.DetailedPlacement` first).  This is how the `DRT_OPT_ITERS` 16 ->
40 comparison was made: a fresh tag starts DRT at 313 violations (337 after
the first anneal step), a resumed one starts at whatever the last run left.

Three stages, because TritonRoute needs the upstream route-guide trick:

1. `--to OpenROAD.DetailedPlacement` — netlist to placed DEF.
2. `flow/scripts/tr1um_route_guide.py` — global route with the M1-pin cell
   LEF (`TR10_cmp_sc_grt.lef`), then inflate every guide rectangle by
   81 um (one routing channel).
3. `--from OpenROAD.DetailedRouting` — patched `drt.tcl` consumes
   `expanded.guide`, then RCX / STA / IR-drop / GDS / KLayout.

The guide is a close match for the upstream artefact: 3478 M1 + 1399 M2
rectangles here versus 3496 + 1405 in
`openroad/route_expanded.guide`, with the same 653 signal nets.

## Constraints

The upstream publishes no OpenROAD STA report; its performance numbers come
from a post-layout ngspice run at 28.50 MHz with 1 pF per output.  The SDC
uses the same operating point so the two are comparable:

```
create_clock -period 35.088 -name clk [get_ports clk]      ;# 28.50 MHz
set_clock_uncertainty 0.500 [get_clocks clk]
set_input_delay  -clock clk 2.000 [all_inputs]
set_output_delay -clock clk 2.000 [all_outputs]
set_load 1000.0 [all_outputs]                              ;# 1 pF (1 ff unit)
```

`set_input_delay` has to be applied to `[all_inputs]` directly: this SDC
interpreter has no `remove_from_collection`, and applying it to the clock
port only produces the harmless `STA-0441` warning.

## Implementation notes (things that cost a debug cycle)

- **Macro placement.** LibreLane's `MACROS[*].instances` places the macro
  before PDN (`Odb.ManualMacroPlacement`); `PDN_MACRO_CONNECTIONS` alone is
  not enough and PDN aborts with `PDN-0235 Design has unplaced macros`.
  `EXTRA_LEFS` is still required so the early OpenROAD steps see the master.
- **`SRAM128` GDS origin.** The upstream LEF says
  `FOREIGN SRAM128 82.1 90.1` and the GDS really is drawn at -82.1/-90.1 um.
  LibreLane merges macro GDS by cell name only, i.e. without applying
  `FOREIGN`, so `flow/scripts/build_sram128_gds.py` shifts the view to the
  LEF origin and `build_sram128_views.py` drops the `FOREIGN` statement.
  It also renames the `VSS` labels to `GND`.
- **LEF ordering.** OpenROAD rejects `MANUFACTURINGGRID` before `UNITS`
  (`LEFPARS-1505`); the view builder reorders them.
- **Row pitch.** `initialize_floorplan` snaps rows to the site/core grid and
  cannot produce the 145.8 um pitch, so `manual_place.tcl` destroys the
  generated rows and creates 11 rows of 340 sites at 145.8 um.
- **`FIXED` is not a legal status** in this OpenROAD SWIG binding.  Instances
  and b-pins are set to `FIRM`, which is also what `check_power_grid`
  requires for terminals (`PSM-0025` otherwise).
- **IR-drop `.loc` files are raw CSV.** The parser does not skip comments;
  a `#` header line aborts the step with the terse `irdrop.tcl, 51 stod`.
- **PDN vias must be the TAP2 ones, not `pdngen`'s.**  `add_pdn_connect`
  fills every rail/strap crossing with a V1 array on a 2.6 um pitch.  On TR10
  that is illegal twice: the deck wants V1 spacing >= 1.5 um (`V1.S1`), and
  the 3.4 um row rails carry the TAP2 substrate contacts in their middle, so
  a rail-centred V1 overlaps CO (`V1.CO`) — 132 violations in total.  The
  upstream GDS paints no V1 at those crossings at all; the connection is the
  V1 that the TAP2 cell carries (local `(2.0..3.4, 3.9..5.3)` for GND,
  `(7.4..8.8, 54.1..55.5)` for VDD, exactly 1.0 um clear of the CO).
  `post_pdn.tcl` therefore deletes every `pdngen` shape and re-adds one V1 per
  net per crossing at the TAP2 position: it merges with the cell's own via, is
  DRC clean, and still gives `check_power_grid` a connected network (PSM sees
  no cell internals).
- **DRT iterations.** The upstream run uses `-droute_end_iter 40`.  At the
  LibreLane default of 16 the violation tail is still descending
  (331 -> 96 -> 35 -> 19 -> 17), so `DRT_OPT_ITERS` is 40 here.

## Results

Run `runs/t4` (full three-stage flow, fresh tag, `DRT_OPT_ITERS=40`).  "Upstream"
is `jun1okamura/TR-1um_C4004` at `db826b1`: physical numbers from its routed
DEF/GDS, performance from its post-layout ngspice run.

### Physical

| metric | upstream | here | delta |
|---|---|---|---|
| die | 1840 x 1840 um | same (3,385,600 um²) | – |
| core | – | 3,271,750 um² | – |
| instances | 638 + 129 FILL | 811 (637 std + 44 TAP2 + 129 FILL + SRAM128) | same |
| placed instance area | – | 1,391,370 um² (std 1,057,550 / macro 216,428 / fill 117,398 / tap 28,227) | – |
| utilization | – | 38.94 % (stdcell 34.61 %) | – |
| wirelength | 409,187 um | 405,828 um | -0.82 % |
| vias (1-cut) | 2,900 | 2,912 | +12 |
| detailed-routing DRC | 0 | 0 (iter 34/40) | same |
| KLayout DRC | not published | 0 rule violations, 1 guard-ring advisory | – |
| power-grid violations | – | 0 | – |

The reproduction is faithful to the point that the differences are rounding:
the DEF has the same 811 components at the same coordinates (`post_dpl.tcl`
re-inserts the 129 fillers, `design__instance__displacement__total 0`), and
the global-route guide is 3478 M1 + 1399 M2 rectangles against the upstream
3496 + 1405 for the same 653 signal nets.  The 12 extra vias are the
difference between the two routers' via counts.

### Timing, power, IR drop

| metric | upstream (ngspice) | here (OpenROAD STA, `nom_typ_5p0V_25C`) |
|---|---|---|
| clock | 28.50 MHz (35.088 ns) | 35.088 ns constraint, `set_clock_uncertainty 0.5` |
| setup WNS / TNS | meets 28.50 MHz | **-1048.75 ns** / -22,176 ns |
| setup violating endpoints | – | 81 (67 reg-to-reg) |
| hold WNS / TNS | – | -18.22 ns / -18.22 ns, 1 endpoint |
| clock skew (setup / hold) | – | 42.10 ns / 41.10 ns |
| max-slew / max-cap violations | – | 1780 / 433 |
| power | 53.33 mW | 237.57 mW (all switching; leakage 0 in this Liberty) |
| IR drop VDD | – | worst 85.1 mV (1.70 %), average 53.7 mV |
| IR drop GND | – | worst 84.5 mV (1.69 %), average 53.8 mV |
| PSM connectivity | – | `PSM-0040` all shapes connected on both nets |

IR drop is measured with the upstream-style two-terminal source files
(`vsrc_vdd.loc`, `vsrc_gnd.loc`, two 5.0 V / 0.0 V sources at the pad
corners) on the STA activity of the 237.6 mW netlist, so it is a grid-quality
number, not a vector-dependent signoff drop.

### Why the STA and ngspice numbers are not comparable

The upstream publishes no OpenROAD report, so the only honest statement is
that *this* flow does not close 35.088 ns on this layout, and the extracted
parasitics say why:

- RCX extracts 653 nets, 1,678 pF total, max 20.9 pF, median 1.19 pF.  The
  clock tree is the worst case: `clk_root` carries 14.1 pF into 8 loads and
  `clk_buf_r4` 10.9 pF into 7 (1.6-1.8 pF per CK pin), and each `BUF_X2`
  stage costs 21-25 ns at that load.  The worst setup skew is 42.1 ns
  (54.25 ns latency at `_1090_/CK` against -12.65 ns at `u_ff_sync/CK`), so
  the clock network alone is over budget before any logic delay.
- The critical path (`_1090_/CK -> Q -> _0588_ -> _0659_ -> _0917_ ->
  _0918_ -> _1056_ -> u_ff_dhiz/D`) accumulates 1088.09 ns.  Its first stage
  alone (`_1090_/Q`, 18.2 pF across 14 fanout) takes 177 ns.
- No resizer, buffer or CTS is allowed, so the drive strengths are exactly
  the upstream ones and nothing compensates the extracted load.
- The upstream 28.50 MHz / 53.33 mW come from an ngspice run of their own
  extracted netlist, i.e. a different RC model, a different (ideal or
  hand-balanced) clock definition and no SDC uncertainty.  The two numbers
  answer different questions; the OpenROAD one is what this PDK's RCX sees.

The PPA that is directly comparable is therefore the physical one (area,
wirelength, via count, DRC) plus the power-grid quality, which is the reason
the upstream design was rebuilt at all: on identical cells and identical
placement, the TR10_cmp_sc implementation routes to the same length and
connects both supplies through a mesh that drops <2 % at the pad.
