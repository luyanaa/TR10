# tr1um_fifo4_cmp — TR10_cmp_sc multi-row A/B target

A/B comparison design for the 59.4 um compact cell library against
`examples/tr1um_fifo4` (TR10_fd_sc).  The same FIFO netlist is synthesized
to `TR10_cmp_sc` cells and placed on a subset of the N rows
(`manual_place.tcl`, currently every other N row → 237.6 um pitch, 7 used
rows inside the 1000×1600 um die).

## Status: **34 DRC** after fixing the I/O-pin length; sparse-V1-hole LEF is negative

Two independent PDK-view bugs were found and fixed after the routing recipe
was stable.  Both are in the generated views, not in the router:

1. **North/south I/O pins were 1,323,529 µm long.**  LibreLane's
   `io_place.py` derives a pin's length from the routing layer's LEF
   `AREA`; OpenDB stores that area in dbu² but the script multiplies by
   `DATABASE MICRONS²` again.  With `AREA 9.0` on M2 every I/O pin became a
   6.8 × 1,323,529 µm M2 bar, leaving 0.3 µm to the neighbouring tracks
   *across the whole die*.  All 69 residual violations were on those bars.
   `TR10_cmp_sc/config.tcl` now sets `IO_PIN_V_LENGTH`/`IO_PIN_H_LENGTH`
   to 6.8 µm (the conventional 2× min width; `TR10_fd_sc` gets the same
   value because its M2 has no `AREA`).  Result: **69 → 34** at the same
   placement and `DRT_OPT_ITERS: 16`.
2. **TAP cells carry a full-height M2 power bar.**  The GDS really is a
   full-height bar (`x 1.0..4.4` / `6.4..9.8`, `y 1.1..58.3`); the source
   LEF splits it into short pin stubs plus a middle `OBS`.  Two signal M2
   wires shorted to VDD at the TAP column.  `TAP_SOURCE_M2` in the
   generator reproduces the source split (stub pins + middle obstruction);
   measured, that variant ends at **56 DRC with 14 VDD/GND conflicts**
   instead of 34 with 2, so it is **off by default**.  The default
   full-height pin is the electrically accurate abstraction; the remaining
   two shorts are a DRT limitation (it routed a signal wire onto a power
   pin), not a missing obstruction.

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
single M1 marker in the pin band (y 27..32), i.e. the router never used a
hole.  The residual floor is **not** cell pin access: it is M1 channel
shorts near the TAP column plus the TAP M2 shorts above.

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

## How to run the reproduction

```bash
cd examples/tr1um_fifo4_cmp
export PDK_ROOT=/grid/TR-1um_stdcell/flow/pdk_root PDK=TR10
export PYTHONPATH=<dir containing patched librelane>
OPENROAD=/nix/store/...-openroad-26Q3/bin/openroad

# 1. run the flow through detailed placement (writes the placed DEF)
librelane --pdk-root $PDK_ROOT --pdk TR10 --manual-pdk \
          --run-tag tag --to OpenROAD.DetailedPlacement config.json

# 2. build the expanded guide from the M1-pin LEF
python3 ../../flow/scripts/tr1um_route_guide.py \
    --def runs/tag/33-openroad-detailedplacement/tr1um_fifo4_cmp.def \
    --out expanded.guide --openroad $OPENROAD --die 1000x1600

# 3. resume; patched drt.tcl reads expanded.guide via read_guides
librelane --pdk-root $PDK_ROOT --pdk TR10 --manual-pdk \
          --run-tag tag --from OpenROAD.DetailedRouting config.json
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
