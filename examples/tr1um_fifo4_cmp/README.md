# tr1um_fifo4_cmp — TR10_cmp_sc multi-row A/B target

A/B comparison design for the 59.4 um compact cell library against
`examples/tr1um_fifo4` (TR10_fd_sc).  The same FIFO netlist is synthesized
to `TR10_cmp_sc` cells and placed on a subset of the N rows
(`manual_place.tcl`, currently every other N row → 237.6 um pitch, 7 used
rows inside the 1000×1600 um die).

## Status: **0 DRC** (DRT + KLayout sign-off), KLayout LVS PASS

Final run `runs/opt700b` (96 signal cells, 7 used rows, **700×1570 µm** die,
0-gap placement, 3.4 µm I/O pins):

| check | report | result |
|---|---|---|
| detailed routing | `34-openroad-detailedrouting/tr1um_fifo4_cmp.drc` | **0** (empty file) |
| KLayout DRC | `*-klayout-drc/reports/drc.klayout.json` | **0** |
| KLayout LVS | `flow/checks/test_klayout_lvs.sh` | **PASS** |
| instance area | `final/metrics.json` | 212,664 µm² (fd_sc 406,388 → **52.3 %**) |
| die area | `final/metrics.json` | 1,099,000 µm² (fd_sc 2,880,000 → **38.2 %**) |
| utilization | `final/metrics.json` | **20.4 %** (fd_sc 14.74 %) |
| routed wirelength | `final/metrics.json` | 64,818 µm (fd_sc 148,690 → **−56 %**) |

Three independent causes were removed in this order:

1. **I/O pin length (69 → 34).**  LibreLane's `io_place.py` derives a pin's
   length from the routing layer's LEF `AREA`; OpenDB stores that area in
   dbu² but the script multiplies by `DATABASE MICRONS²` again.  With
   `AREA 9.0` on M2 every north pin became a 6.8 × 1,323,529 µm M2 bar,
   leaving 0.3 µm to the neighbouring tracks *across the whole die*.  All
   69 residual violations were on those bars.
   `TR10_cmp_sc/config.tcl` now sets `IO_PIN_V_LENGTH`/`IO_PIN_H_LENGTH`
   to 6.8 µm (the value `TR10_fd_sc` gets because its M2 has no `AREA`).
2. **Unidirectional routing (34 → 0 DRT).**  Pinning M1 and M2 to their
   preferred directions makes TritonRoute assign the **same M1 track to
   two different nets** and it cannot jog out of the conflict.  The 34
   violations were 13 unique same-track shorts (plus via pads), all with
   two nets' M1 wires at the same y and overlapping x.  Deleting
   `unidirectional_layers.txt` lets both layers jog: **26 start → 0 at
   iteration 5**.  The DRT report is empty.
3. **N-well bridges (6 → 0 KLayout DRC).**  The cells draw their N-well
   with a 6.3 µm halo per side because the library is designed for
   abutting placement.  A 10.8 µm via gap still merges the wells
   (2 × 6.3 > 10.8), but the placement lands three cells 16.2/21.6 µm
   before a fixed TAP.  Those gaps leave separate wells 3.6/9.0 µm apart,
   failing `WN.S1` (< 4), `WN.S7` (< 12) and `WN.AN` (< 10).  The legal
   bands are gap ≤ 12.6 µm (merge) or ≥ 24.6 µm (12.0 + 2 × 6.3).
   `flow/scripts/add_well_bridges.py` inserts a normal N-well rectangle
   (140/0) in each forbidden gap, merging the wells exactly as abutting
   placement would.  KLayout DRC went **6 → 0**, LVS stays **PASS**.

The TAP M2 experiment (`TAP_SOURCE_M2`: source-LEF stub pins + middle
obstruction) was measured at 56 DRC with 14 VDD/GND conflicts versus 34
with 2, so it remains **off by default**; the GDS really is a full-height
M2 power bar.

### Layout optimization study (measured)

**1. The 10.8 µm via gap is not required with free-direction routing.**
The limit came from the *unidirectional* router: V1 pads could only land in
the horizontal cell gaps.  With both layers free, TritonRoute drops V1 in
the 178.2 µm channels instead.  `TR10_GAP_UM=0` abutts the cells and DRT
still reaches **0**.  Abutting also merges the cell wells, so most of the
well-bridge work disappears.

**2. Row pitch.**  237.6 µm is the practical minimum:

| pitch | channel | result |
|---|---|---|
| 118.8 µm (`TR10_PITCH_EVERY=1`) | 59.4 µm | 186 → 116+ DRT, fails |
| 178.2 µm (`TR10_ROW_STEP=3`, N/MX rows) | 118.8 µm | 2 DRT + 12 KLayout, fails |
| 237.6 µm (`PITCH_EVERY=2`) | 178.2 µm | 0 DRT, works |

`TR10_ROW_STEP` places cells on every Nth *physical* row, including the
flipped **MX** rows (cells get the row's R0/MX orientation).  The 178.2 µm
variant is the tightest pitch the row structure allows, but its 118.8 µm
channel cannot reliably hold two signal tracks plus the 3.4 µm via pads, so
it is not used.

**3. Die shrink + I/O pin width.**

* The 0-gap placement compacts the rows: the 96 cells span x 10.8..669.6
  at the 700 µm width.
* North I/O pins were 2× M2 width (6.8 µm), leaving 0.3 µm to the adjacent
  track.  At 1× (3.4 µm) the gap is the normal 2.0 µm
  (`IO_PIN_V_THICKNESS_MULT: 1` in `config.json`).
* die 1000×1600 → **700×1570**: DRT **0**, KLayout DRC **0** (4 well
  bridges), LVS **PASS**.

| metric | 1000×1600 (`final0`) | 700×1570 (`opt700b`) | Δ |
|---|---|---|---|
| die area | 1,600,000 µm² | 1,099,000 µm² | **−31.3 %** |
| utilization | 14.68 % | **20.4 %** | +39 % relative |
| routed wirelength | 79,173 µm | 64,818 µm | **−18.1 %** |
| instance area | 221,645 µm² | 212,664 µm² | −4 % (fewer TAPs) |

**4. ABC area-first (measured, not adopted).**

| strategy | synthesis cell area | placed instance area | routed WL |
|---|---|---|---|
| `AREA 0` (default) | 185,719.5 µm² | 212,664 µm² | 64,818 µm |
| `AREA 3` (ORFS area script) | 195,342.6 (+5.2 %) | — | — |
| `AREA 0` + `SYNTH_ABC_AREA_USE_NF` (`&nf -R 1000`) | **183,794.9 (−1.0 %)** | 222,287 (+4.5 %) | 67,423 (+4.0 %) |

The `NF` mapper shrinks the synthesis netlist by 1 % but remaps it to 107
cells instead of 96; the extra buffers make the *placed* area and wirelength
worse, so the flag is documented but left `false`.  `SYNTH_STRATEGY` can be
switched per run.

**5. What is left (cell-library work, quantified).**

* **EDFF / DFF2.**  DFF 23 + MUX2 20 dominate.  The *existing* `EDFFRB` is
  97.2 µm = DFF 64.8 + MUX2 32.4, so mapping it saves only the 10.8 µm gap
  and one M2 net — with 0-gap placement that is ~0 width.  A new
  **EDFF without reset at 75.6 µm**, or a **DFF2 dual at ~97.2 µm vs
  2 × 64.8**, would save ~31.6 / ~32.4 µm per instance.  20 EDFF + 11 DFF2
  ⇒ ~1,000 µm of row width (**~27 %** of the 3,732 µm total cell width).
  This needs new GDS/LEF/Liberty/SPICE views.
* **Transmission-gate MUX2.**  10.8–16.2 µm vs 32.4 µm × 20 instances
  ⇒ 320–420 µm of row width (**~9–11 %**).
* **PDN relaxation.**  `PDN_VPITCH` 120 → 300 frees 2–3 M2 tracks per
  strap.  DRC is already 0, so this is margin — but it is the most likely
  way to make the 178.2 µm pitch route and would then save another ~17 %
  of height.
* `RUN_CTS: false` and all post-PnR repair/antenna insertion are already
  off.  The cmp library has **no X4/X8/X16** cells (only X1/X2), so there
  is nothing to drop there.  An ABC area-first synthesis pass is the
  remaining few-percent lever on the combinational area.

### Sparse-V1-hole LEF experiment (negative, measured)

The last remaining hypothesis was that opening V1 landing holes inside the
cells would relieve pin access.  `build_cmp_sc_lib.py` has a `PIN_HOLES`
mode that emits `TR10_cmp_sc_v1hole.lef`: the full-cell M1/V1 `OBS` minus a
pad-sized hole at every signal pin, with the cell's real M1 pad declared as
a second port on the pin.

GDS facts that make the holes exact: all 126 signal pin rects are fully
covered by real M1, and every pin centre has a 1.4 × 1.4 V1.

Why it cannot help: M1 is 1.8 wide with 1.4 spacing, so a wire centreline
must be ≥ 2.3 µm from real M1 and a 3.4 × 3.4 V1 pad ≥ 3.1 µm.  The pin
band is only 3.4 µm tall, leaving 0.8 µm to the metal above/below — no
legal M1 track exists inside it.  An eroded-free-space analysis over all
37 cells finds **0** locations where a 3.4 × 3.4 pad fits.

| LEF | start | iter 5 | iter 12 | final (iter 16) |
|---|---|---|---|---|
| `TR10_cmp_sc.lef` (baseline) | 64 | 56 | 34 | **34** |
| `TR10_cmp_sc_v1hole.lef` | 88 | 66 | 36 | **36** |

Both runs use the same placement, guide and seeds.  Neither run has a
single M1 marker in the pin band (y 27..32).  A 3-iteration probe that
dumps the routed DEF confirms the mechanism: of **591 routed
`M1M2_V1` via instances, only 2 (0.3 %) land inside a logic-cell
footprint** — both exactly on a pin centre.  The holes are usable but
irrelevant: the router reaches every other pin from the M2 side (the pin
band is directly open to the 178 µm channels between rows), so opening M1
landing pads saves nothing and the extra M1 geometry only perturbs the
channel routes.  The residual floor is **not** cell pin access: it is M1
channel shorts near the TAP column plus the TAP M2 shorts above.

## Previous status: 69 DRC with the long-I/O-pin bug

Detailed routing on the compact cell set is unblocked by reproducing the
upstream TR-1um C4004 OpenROAD flow (`jun1okamura/TR-1um_C4004`,
`openroad/`).  Five pieces work together:

- **Two cell LEFs.**  `TR10_cmp_sc_grt.lef` keeps every signal pin on
  **M1** so `global_route` allocates real M1 guide regions across the rows;
  the detail-route `TR10_cmp_sc.lef` keeps the same pins on **M2** plus a
  full-cell M1/V1 OBS so TritonRoute never enters the cell interior.  Both
  are emitted by `flow/scripts/build_cmp_sc_lib.py`.
- **Expanded guides.**  `flow/scripts/tr1um_route_guide.py` runs
  `global_route` on the placed DEF with the M1-pin LEF, then inflates every
  guide rectangle by 81 um (one channel) — the upstream `run_grt.tcl` +
  `make_expanded_guide.py` equivalent.
- **Guide injection.**  the patched `scripts/openroad/drt.tcl` calls
  `read_guides $DESIGN_DIR/expanded.guide` when present, replacing the
  M2-only guides that an ODB-driven `global_route` would leave behind.
- **RePlAce seed.**  `manual_place.tcl` first runs
  `global_placement -disable_pin_density_adjust` (the documented TR10
  RePlAce workaround) and uses each cell's seed (x, y) only to pick its
  row band and its order inside that row, before snapping everything onto
  legal all-R0 N rows with a 2-site (10.8 um) via-access gap per cell.
  This is what turns the M2 congestion from a ~400-violation stall into a
  converging tail.
- **Unidirectional routing.**  `unidirectional_layers.txt` (`M1 M2`) is
  picked up by the `drt.tcl` patch and calls
  `detailed_route_set_unidirectional_layer` for each listed layer — the
  upstream `run_drt.tcl` flag.  It roughly halves the starting violation
  count (195 → 111 at iteration 0).

### Measured results (96 cells, 8 threads)

| config | rows × pitch | gap | uni-dir | best (iter) | end-of-run |
|---|---|---|---|---|---|
| `final` | 7 × 237.6 µm | 10.8 µm | yes | **69 (iter 16)** | **69 DRC** ✅ |
| `wide`  | 5 × 356.4 µm | 5.4 µm | no  | 89 (iter 40) | 89 DRC |
| `uni8`  | 5 × 356.4 µm | 5.4 µm | yes | 79 (iter ~10) | 226 (degraded after ~iter 33) |
| `gap2`  | 7 × 237.6 µm | 10.8 µm | yes | 69 (iter ~11) | 103 (same late degradation) |

`final` is the shipped configuration (`config.json`): 7 rows at 237.6 µm
on the 1000×1600 µm die, `DRT_OPT_ITERS: 16`.  It converges to **69 M2
pin-access violations** and stops at the bottom of the curve — every
longer run measured re-tears the converged nets and ends higher.

All configs plateau at a residual set of **pin-access conflicts**: ~90%
of the residual violations sit within ±40 µm of a cell row's M2 pin band.
Because every cmp_sc cell carries a full-cell M1/V1 OBS, the only legal
V1 landing site is the gap *between* cells, so pin access — not channel
capacity — is the limit.  The ~30-iteration tail that TritonRoute spends
ripping up and re-routing actually walks *away* from the best solution
(see `uni8`: 79 at iter 10 → 226 at iter 60), so for this geometry the
useful budget is ≈12–16 iterations.

### What didn't move the floor (dead ends, measured)

These were all tried against the same 7×237.6/10.8-gap placement and
converged to the same ~69 floor, confirming it is a **structural
pin-access limit of the cell LEF**, not a routing-parameter problem:

- **`or_seed` sweep** (7/13/42/99/123/777 + a 4-seed ×30-iter run): every
  seed produced a *bit-identical* violation trajectory
  (100→137→120→111→…→69→107→90).  TritonRoute is deterministic here; the
  seed is ignored.
- **Wider row pitch** `356.4 µm / 5 rows` (`TR10_PITCH_EVERY=3`): *worse*,
  141 DRC — fewer rows ⇒ more cells/row ⇒ tighter gaps.
- **Deeper die + more rows** (`1000×1800`, 8×237.6, `TR10_GAP_UM=21.6`):
  ~80–103 DRC — the bigger inter-cell gap does not translate into usable
  V1 landing area.
- **Sparse-OBS cell LEF** (`TR10_cmp_sc_sparse.lef`, real M1 obstruction
  polygons instead of the full-cell block): *degraded* to ~182–206,
  because interior M1 metal turns into extra blockers without opening a
  clean V1 landing column.  Abandoned; `TR10_cmp_sc_sparse.lef` and the
  `FULL_OBS` flag are kept in the generator for reference but unused.
- **Per-net NDR** (`create_ndr`/`assign_ndr` on `clk`, `data_in[1]`): DRT
  aborts with `DRT-0218 Guide is not connected to design` — the expanded
  guides are not NDR-aware.  Abandoned.
- **FILL-cell row padding** (`$block addInst` in `manual_place.tcl`):
  OpenROAD 26Q3 `odb::dbBlock` does not expose `addInst`; the call fails.
  Reverted.

The floor is therefore accepted at **69 DRC**.  Reaching lower would need
a cell-LEF change that opens a legal V1 landing column *inside* the
footprint at the M2 pin band (e.g. sparse V1 holes aligned to the pin
x-positions) — a real layout/LEF redesign, out of scope for this A/B.

Two gotchas cost us a debugging cycle — keep them in mind:

- **`--from` resumes need the routing range.**  `set_routing_layers`
  normally runs inside `grt.tcl`/`gpl.tcl`; if you resume the flow with
  `--from OpenROAD.DetailedRouting` (skipping GlobalRouting) the ODB has
  no signal routing range and `read_guides` rejects the M1 boxes with
  `DRT-0155 … allowed routing range [M2,M2]`.  The patched `drt.tcl`
  sources `set_routing_layers.tcl` before `read_guides`, so both the
  full flow and a `--from` resume work.
- **`DRT_SAVE_SNAPSHOTS` + resume.**  With `DRT_SAVE_SNAPSHOTS: true` the
  step saves `drt_iter*.odb`; resuming *into* a snapshot with
  `detailed_route` reroutes fine, but a `read_db` of a mid-iteration ODB
  can hit `DRT-0206 checkConnectivity` on the partially-ripped nets —
  resume from a `detailedplacement` ODB instead.

## Provenance and license

`TR10_cmp_sc` is derived from **jun1okamura/TR-1um_C4004**
(<https://github.com/jun1okamura/TR-1um_C4004>; the same cells are also
published as `TR-1um_Async_I2C`), licensed under Apache-2.0:

```
Copyright 2025 OpenSUSI ( https://www.opensusi.org/ )
Copyright 2025 ISHI-KAI ( https://ishi-kai.org/ )
Copyright 2025 TOKAI RIKA CO., LTD
```

- `libs.ref/TR10_cmp_sc/LICENSE` — the full Apache-2.0 text as distributed
  upstream.
- `libs.ref/TR10_cmp_sc/NOTICE` — attribution and the list of modifications
  made for this PDK.
- `libs.ref/TR10_cmp_sc/TR10_cmp_sc_manifest.json` — SHA-256 of every
  distributed view (including LICENSE and NOTICE).

## How to run the reproduction

```bash
cd examples/tr1um_fifo4_cmp
export PDK_ROOT=/grid/TR-1um_stdcell/flow/pdk_root PDK=TR10
export PYTHONPATH=<dir containing patched librelane>
OPENROAD=/nix/store/...-openroad-26Q3/bin/openroad

# 1. run the flow through detailed placement (writes the placed DEF).
#    TR10_GAP_UM=0 is the 0-gap placement; omit it (default 10.8) to trade
#    area for the older via-gap style.
TR10_GAP_UM=0 librelane --pdk-root $PDK_ROOT --pdk TR10 --manual-pdk \
          --run-tag tag --to OpenROAD.DetailedPlacement config.json

# 2. build the expanded guide from the M1-pin LEF
python3 ../../flow/scripts/tr1um_route_guide.py \
    --def runs/tag/33-openroad-detailedplacement/tr1um_fifo4_cmp.def \
    --out expanded.guide --openroad $OPENROAD --die 700x1570

# 3. resume; patched drt.tcl reads expanded.guide via read_guides.
#    DRT reaches 0; the flow stops at KLayout DRC with the WN gaps.
librelane --pdk-root $PDK_ROOT --pdk TR10 --manual-pdk \
          --run-tag tag --from OpenROAD.DetailedRouting config.json

# 4. merge the N-well islands in the forbidden 12.6..24.6 um gaps
#    (same-row and N row -> MX row below).
#    (KLayout does not forward -- args, so the paths go through env vars.)
WELLBRIDGE_GDS=runs/tag/46-klayout-streamout/tr1um_fifo4_cmp.gds \
WELLBRIDGE_DEF=runs/tag/33-openroad-detailedplacement/tr1um_fifo4_cmp.def \
WELLBRIDGE_OUT=runs/tag/46-klayout-streamout/tr1um_fifo4_cmp.gds \
    klayout -b -r ../../flow/scripts/add_well_bridges.py

# 5. continue from KLayout DRC: 0 errors, flow completes
librelane --pdk-root $PDK_ROOT --pdk TR10 --manual-pdk \
          --run-tag tag --from KLayout.DRC config.json

# 6. KLayout LVS assertion
bash ../../flow/checks/test_klayout_lvs.sh runs/tag tr1um_fifo4_cmp TR10_cmp_sc
```

`inv_cmp` (single inverter, single used row) still passes end to end and
is the CI smoke for the `TR10_cmp_sc` views.

## Note on the earlier "0 % M1" diagnosis

An earlier writeup claimed M1 was unusable because the cells draw
full-height M1.  That was wrong about the *mechanism*: the real blocker
was that `global_route` against the M2-pin LEF produced almost no M1 guide
boxes, so detail routing had no M1 corridor.  Switching the GRT view to
M1 pins (this directory's `expanded.guide` flow) is what restores M1 —
the same conclusion the upstream author reached, not a cell-layout change.
