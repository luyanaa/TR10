# TR10_cmp_sc PDN + CTS experiment

This is the second PDN/CTS pass on `examples/tr1um_fifo4_cmp`.  The first
pass (`runs/cts`, commit `f135a87`) produced a working CTS tree but a
followpin-only PDN with no power terminals, so `GeneratePDN` failed with
`PSM-0025` and IR-drop aborted with `PSM-0069`.  This pass adds the missing
M2 straps and block power pins, removes the N/FS row polarity hazard, and
enables post-CTS / post-GRT hold repair.

## Final result (run tag `pdncts8`)

| item | result |
|---|---|
| PDN power-grid violations | **0** (VDD 0, GND 0) |
| PDN connectivity | `PSM-0040 All shapes on net VDD/GND are connected` |
| detailed routing | **DRT 0** |
| IR drop VDD | **avg 0.224 mV, worst 0.381 mV** (0.01 % of 5.0 V) |
| IR drop GND | **avg 0.224 mV, worst 0.383 mV** (0.01 %) |
| total power | 0.562 mW (post-route) |
| setup WNS | **4562.38 ps**, 0 setup violations |
| hold WNS | **-8.72 ps**, 14 hold violations, TNS -57.41 ps |
| clock skew (post-route) | 8.45 ns setup / 4.45 ns hold |
| instance area / utilization | 237,362 um^2 / 20.93 % |
| TAP2 cells | 39 (13 N rows x 3 fixed columns) |

The remaining 14 hold paths are **input-to-register** paths
(`data_in[*]`/`pop` -> DFF); register-to-register hold is clean.  They are
caused by the large clock insertion delay (~19 ns) versus the 2 ns
`set_input_delay` in `constraints.sdc`, not by the PDN.

## Why the N/FS row mix had to change

The compact 59.4 um cells mirror both their M1 PG bands and their TAP2 M2
PG straps in FS rows.  TAP2's M2 straps are at x+1.0..4.4 (GND) and
x+6.4..9.8 (VDD) for an N row, but the two nets **swap columns** in an FS
row.  A straight full-height M2 strap therefore alternates between VDD and
GND at every N/FS boundary and cannot provide vertical continuity; the
previous followpin-only grid was a stack of isolated horizontal rails.

`examples/tr1um_fifo4_cmp/manual_place.tcl` now:

1. deletes all FS rows, leaving the 13 N rows (0, 118.8, ... 1425.6 um);
2. inserts TAP2 at x = 226.8, 442.8 and 658.8 um on every remaining N row,
   all R0/FIRM, before the deterministic packer (tap insertion is disabled
   with `RUN_TAP_ENDCAP_INSERTION=false`);
3. gives the new TAP2 instances their VDD/GND connections and then packs
   the standard cells on every second N row (237.6 um pitch).

Every placed instance (standard cell, TAP2, CTS buffer, hold buffer) is
now on an N row, so the TAP2 M2 straps stay at fixed columns and the PDN
M2 stripes are always inside a TAP2 cell or an empty FS row.

## PDN topology

`libs.tech/librelane/TR10_cmp_sc/pdn_cmp_sc.tcl`:

* M1 followpin rails at every row boundary, width 3.4 um (`-followpins`).
* Six full-height M2 stripes at the TAP2 columns:
  * GND: x = 229.5, 445.5, 661.5 um (centres)
  * VDD: x = 234.9, 450.9, 666.9 um (centres)
* `add_pdn_connect -layers {M1 M2}` adds M1M2_V1 vias at same-net
  crossings; the TAP2 cell also provides its internal M1<->M2 connection.
* `define_pdn_grid ... -pins M2` turns the M2 stripes into VDD/GND block
  terminals (`PINS 15` includes `VDD`/`GND`, `SPECIAL`, `USE POWER/GROUND`).

The PDN generation log and the (empty) grid-error reports are in
`results/pdncts8/`.  The M2 special-net and power-pin geometry is in
`results/pdncts8/pdn_specialnets.txt` and `pdn_pins.txt`.

## CTS and hold repair

`results/pdncts8/cts.rpt`:

```
Total number of Clock Roots: 1.
Total number of Buffers Inserted: 3.
Total number of Clock Subnets: 3.
Total number of Sinks: 23.
Cells used: BUF_X2: 3
Dummys used: INV_X2: 1
```

CTS log: path depth 2, average sink wire length **1832.36 um**, clock
buffer area 2886.84 um^2, clock inverter area 641.52 um^2.

The tree is still a shallow 2-level H-tree.  OpenROAD's sink clustering
is skipped for fewer than 200 sinks (`min_clustering_sinks_ = 200`), so
`CTS_SINK_CLUSTERING_SIZE=4` has no effect for this 23-sink design.  The
long clock wires give a post-route skew of 8.45 ns setup / 4.45 ns hold;
setup still has 4562 ps of margin at a 5000 ps clock.

Hold repair is enabled with:

```json
"RUN_POST_CTS_RESIZER_TIMING": true,
"RUN_POST_GRT_RESIZER_TIMING": true,
"PL_RESIZER_HOLD_SLACK_MARGIN": 2.0
```

The post-CTS resizer inserts 7 `DEL1` buffers and reaches a pre-route hold
WNS of +2.087 ns.  The post-GRT resizer reports no remaining hold
violations.  After SPEF extraction the I/O hold paths are -8.72 ps; a
5 ns margin was tested and inserts 17 buffers, but DPL cannot legalize
them on the sparse N rows, so 2 ns is the practical limit.

## IR-drop source model

`VSRC_LOC_FILES` (in `examples/tr1um_fifo4_cmp/config.json`) points to
`vsrc_vdd.loc` / `vsrc_gnd.loc`: three 3.4 x 3.4 um source points per net
at the top of each M2 strap (y = 1540 um).  The block power pins from
`-pins M2` satisfy `check_power_grid`; the vsrc points are the actual IR
sources, so the result is a distributed block-level source model, not a
package/C4 bump model.  With 6 straps and ~0.56 mW, the drop is very
small; a full-chip PDN would need pad/bump sources and would show a larger
drop.

## Run recipe

```bash
cd examples/tr1um_fifo4_cmp
export PDK_ROOT=/grid/TR-1um_stdcell/flow/pdk_root PDK=TR10
export TR10_GAP_UM=0 PYTHONPATH=/tmp/opencode/lrov

# 1. floorplan, PDN, placement, CTS, post-CTS and post-GRT resizers
librelane --pdk-root "$PDK_ROOT" --pdk TR10 --manual-pdk \
  --run-tag pdncts8 --to OpenROAD.ResizerTimingPostGRT config.json

# 2. expanded guide from the post-GRT placement DEF
python3 ../../flow/scripts/tr1um_route_guide.py \
  --def runs/pdncts8/40-openroad-resizertimingpostgrt/tr1um_fifo4_cmp.def \
  --out expanded.guide \
  --openroad /nix/store/6qbn5zjnnnyna6md4rsmiqw4y26y8556-openroad-26Q3/bin/openroad \
  --die 760x1570

# 3. detailed routing, RCX, post-route STA, IR drop
librelane --pdk-root "$PDK_ROOT" --pdk TR10 --manual-pdk \
  --run-tag pdncts8 --from OpenROAD.DetailedRouting \
  --to OpenROAD.IRDropReport config.json
```

`flow/patches/librelane/cts.tcl` and `rsz_timing_postcts.tcl` add the
post-CTS/post-resizer `set_global_connections` call so newly created clock
and hold buffers get VDD/GND pins before IR-drop.

## Previous attempt

The first attempt (`runs/cts`, commit `f135a87`) is kept as the failure
baseline: followpin-only PDN, no terminals, `PSM-0025` / `PSM-0069`, no
IR number, CTS 2.014 ns setup skew / -2.001 ns hold skew, post-route hold
-14.97 ps / 19 violations.  Its report and logs are in the repository
history; this README supersedes its conclusions.

## Caveats / next steps

* The PDN depends on all placed cells being on N rows.  If future work
  needs the FS rows for area, add a symmetric TAP2 (or an FS-specific tap
  variant) so the M2 PG columns do not swap.
* Post-route I/O hold is -8.72 ps on 14 paths.  Options: increase
  `set_input_delay` to reflect the real launch clock, enlarge the N-row
  placement capacity for more delay buffers, or add a dedicated input
  delay cell.
* The clock tree is a 2-level H-tree with 3 BUF_X2.  Reducing the 8.45 ns
  skew needs a deeper clock tree (a CTS implementation/configuration that
  clusters below 200 sinks) or a stronger clock buffer library.
* IR drop uses three ideal source points per net at the top of the M2
  straps; this is a block-level estimate, not a full-chip package model.

## Evidence

```
results/pdncts8/cts.rpt                    CTS report
results/pdncts8/resizer_postcts.log        post-CTS hold repair (7 DEL1)
results/pdncts8/resizer_postgrt.log        post-GRT hold check
results/pdncts8/detailedrouting.log        final DRT 0
results/pdncts8/generatepdn.log            PSM-0040 connected, no PSM-0025
results/pdncts8/VDD-grid-errors.rpt        empty
results/pdncts8/GND-grid-errors.rpt        empty
results/pdncts8/postroute_sta_summary.rpt  setup/hold after SPEF
results/pdncts8/irdrop.rpt                 VDD/GND IR numbers
results/pdncts8/metrics.json               final metrics
results/pdncts8/pdn_specialnets.txt        M1 followpins + M2 straps + vias
results/pdncts8/pdn_pins.txt               VDD/GND block pins
```
