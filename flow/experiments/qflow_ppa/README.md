# qflow (GrayWolf + qrouter) vs LibreLane/OpenROAD on TR10_cmp_sc

Same RTL (`tr1um_fifo4_cmp`), two independent place-and-route flows:

* qflow 1.4.104 / GrayWolf 2.2 / qrouter 1.4.90.T
* LibreLane + OpenROAD 26Q3 (the existing `examples/tr1um_fifo4_cmp` flow)

The TR10_cmp_sc cells are 59.4 um tall, have M2 signal pins and a full-cell
M1/V1 obstruction.  The qflow port required a project-local technology,
qflow-specific LEF/Liberty views, Yosys 0.70, a row-spacing post-process and
a 5.4 um qrouter grid.

## Result

The qflow flow now completes **140/140 nets, "No failed routes"**:

| stage | qflow |
|---|---|
| synthesis | Yosys 0.70, 110 mapped cells (23 DFF, 22 MUX2, 14 INV_X1, ...); no DFF2/TIEHI |
| placement | GrayWolf 7 rows at 59.4 um, then `rowspace.py` to 237.6 um pitch |
| routing | qrouter 5.4 um grid, qflow LEF, final **0 failed nets** |

OpenROAD reference: **DRT 0 / KLayout DRC 0 / LVS PASS**.

### PPA

| metric | qflow | OpenROAD | qflow / OpenROAD |
|---|---|---|---|
| mapped cells | 110 (23 DFF, 22 MUX2) | 87 (20 EDFF, DFF2, DFF, MUXTG2, ...) + 42 TAP2 | — |
| placed cell area | 202,079 um^2 | 224,211 um^2 | 0.901 |
| die area | 502.2 x 1501.2 = **753,903 um^2** | 760 x 1570 = **1,193,200 um^2** | **0.632** |
| utilization | **26.8 %** | **19.77 %** | 1.36x |
| route completion | **140/140, no failed** | DRT **0** | — |
| timing slack @ 5 us | **4974.67 ps** (placement estimate) | **4751.78 ps** (post-route) | +222.9 ps |
| power | **26.1 uW** (placement estimate, switching) | **194.1 uW** (post-route) | 0.134 |
| DRC / LVS | not run (qflow route only) | **0 / PASS** | — |

Interpretation:

* **Area:** qflow's die is 0.63x and its utilization 1.36x the OpenROAD
  result.  qflow has no TAP2 well taps; adding the 42 TAP2 cells used by the
  OpenROAD flow costs 26.9k um^2, which brings qflow's placed area to about
  228.9k um^2 (~1.02x OpenROAD) and would also require die space.  The
  remaining die-area advantage comes from the 7-row, 237.6 um-pitch
  placement and qflow's narrower cell mapping.
* **Timing:** both flows meet the 5 us clock (WNS 0).  qflow's 4974.67 ps
  slack is an OpenROAD `estimate_parasitics -placement` result, while the
  OpenROAD 4751.78 ps is post-route; the +222.9 ps is not a clean router-only
  delta.
* **Power:** qflow's 26.1 uW is an OpenROAD placement-level
  `report_power` on the qflow netlist; it has no extracted wire/clock-tree/PDN
  power, and qflow's `vlogFanout` cell sizing is bypassed.  The OpenROAD
  194.1 uW is post-route/SPEF.  The 7.4x difference is therefore **not an
  apples-to-apples power PPA**; it is reported as a cell-level estimate.

qflow's **same RTL is synthesized to a different gate netlist** (DFF/MUX2 vs
EDFF/DFF2), so this is a flow-level PPA, not a pure router comparison.

## What the full port required

1. **Yosys 0.70.**  The system Yosys 0.52 segfaults on the TR10 Liberty;
   `scripts/setup_qflow_bin.sh` builds a bindir with the Nix Yosys 0.70.
2. **qflow Liberty without DFF2.**  The Liberty DFF2 has single D/Q/QB pins
   while the LEF DFF2 is the dual D0/Q0/D1/Q1 macro; qflow `vlog2Cel` cannot
   place it.  `scripts/build_qflow_liberty.py` removes DFF2; qflow maps DFF.
3. **No empty antenna option.**  `postproc_options="-anchors"` with an empty
   `antennacell` produced a bare `-a` and `vlog2Verilog` segfaulted; set
   `postproc_options=""`.
4. **vlogFanout workaround.**  qflow 1.4's `vlogFanout` renames `NOR3` to a
   3-pin `NOR2`; `scripts/vlogFanout` keeps the Yosys mapped netlist
   unchanged (no drive-strength sizing).
5. **qflow LEF/TLEF.**  `TR10_cmp_sc_qflow.lef` removes the duplicate
   TIEHI/TIELO OBS shapes; `TR10_tech_qflow.tlef` is the 5.4 um routing grid.
6. **Row spacing.**  GrayWolf 1.4 cannot express the TR10 237.6 um row pitch
   (`rowSep`/`numrows` produced a 577.8 x 138380 um die).  `scripts/rowspace.py`
   shifts the GrayWolf rows, updates DIEAREA/TRACKS, moves top pins, and
   strips qflow SPECIALNETS for qrouter.
7. **qrouter.**  5.4 um grid with the qflow LEF routes 140/140 after the
   row/track/pin fix.

## Reproduce

```bash
cd flow/experiments/qflow_ppa
bash scripts/setup_qflow_bin.sh /tmp/qflow_bin

# project: source/tr1um_fifo4_cmp.v, tech/tr10cmp (this directory),
# synthesis/tr1um_fifo4_cmp.rtlnopwr.v from the qflow-mapped netlist.
cd /tmp/qflow_project
echo 'set bindir=/tmp/qflow_bin' > project_vars.sh
qflow -T tr10cmp -p "$PWD" synth tr1um_fifo4_cmp
qflow -T tr10cmp -p "$PWD" place tr1um_fifo4_cmp

python3 /grid/TR-1um_stdcell/flow/pdk_root/TR10/flow/experiments/qflow_ppa/scripts/rowspace.py \
  --def layout/tr1um_fifo4_cmp.def --out layout/tr1um_fifo4_cmp_spaced.def \
  --strip-specialnets

# qrouter with the qflow LEF and 5.4 um grid
qrouter -nog -e 10 -s layout/route.cfg
```

The exact qflow route DEF, placed DEF, mapped/rtl netlists, synthesis/place
logs, qrouter route log and the OpenROAD placement PPA log are in `results/`.

## Caveats

* qflow DRC/LVS were not run; the qflow route is a **signal-routed netlist**,
  not a signoff result.  qflow SPECIALNETS/PDN were stripped for qrouter.
* qflow's netlist lacks TAP2 well taps; adding them changes area/die.
* qflow `vlogFanout` sizing is bypassed; qflow power/timing use the unsized
  mapped netlist.
* qflow timing/power are **placement estimates** from OpenROAD
  (`estimate_parasitics -placement` / `report_power`), not extracted
  post-route values.
* OpenROAD remains the only DRC/LVS signoff PPA point.

## Files

```
tech/tr10cmp/tr10cmp.sh              qflow technology script
tech/tr10cmp/tr10cmp.par             GrayWolf M1/M2 rules
tech/tr10cmp/TR10_cmp_sc_qflow.lef   qflow cell LEF (TIEHI/TIELO OBS removed)
tech/tr10cmp/TR10_tech_qflow.tlef    5.4 um routing grid
tech/tr10cmp/TR10_cmp_sc_qflow.lib   Liberty without DFF2
scripts/setup_qflow_bin.sh           Yosys 0.70 + vlogFanout wrapper bindir
scripts/build_qflow_liberty.py       DFF2 removal
scripts/vlogFanout                    no-resize workaround
scripts/rowspace.py                  237.6 um row shifter/track/pin fix
results/qflow_route.def              final qflow route (140/140)
results/qflow_place_spaced.def       post-rowspace placed DEF
results/qflow_synth_mapped.v         qflow/Yosys mapped netlist
results/qflow_rtl.v                  qflow netlist with explicit power
results/qflow_route.log              final "No failed routes" log
results/qflow_openroad_ppa.log       placement timing/power estimate
results/qflow_ppa.json               PPA numbers
```
