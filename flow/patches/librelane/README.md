# LibreLane / OpenROAD patches for TR10

## `librelane/gpl.tcl` — global-placement stability

**Symptom.** LibreLane global placement fails on multi-cell designs with:

```
[ERROR GPL-0305] RePlAce diverged during gradient descent calculation,
resulting in an invalid step length (Inf or NaN).
```

The overflow stalls around 0.94, the density penalty grows without bound
(~1e-18 -> 1e29) and the step eventually becomes NaN.  The 3-cell `inv`
smoke does not trigger it; 27-, 101- and multi-hundred-instance designs do.

**Root cause.** OpenROAD GPL's *pin-density adjustment* is unstable with
TR10's geometry (75.6 um-tall cells on a 0.1 um site).  It inflates the
effective cell area (e.g. 407,914 -> 426,673 um^2, +4.6%) with a per-bin
pin-density term, and the optimizer cannot drive the resulting overflow
below the target, so the penalty diverges.

Verified by elimination: die size (up to 1600x1200, 23.7% utilization),
target density (0.05 / 0.1 / 0.3 / 0.4 / 0.6 / default 0.8), routability
mode, timing-driven mode, `-skip_initial_place`, `-min_phi_coef`/
`-max_phi_coef` 0.95/1.05 and wider bins (`-bin_grid_count` 64..512) all
still diverge.

**Workaround.** `global_placement -disable_pin_density_adjust` converges
("Global placement finished at iteration 293/603" on the FIFO fixture).
LibreLane 3.1.0.dev3 does not expose this flag as a configuration variable,
so this directory carries a patched copy of its `gpl.tcl` with one added
line (marked with a TR10 comment).  The regression is pinned by
`flow/checks/test_gpl_stability.sh`, which runs the pre-placement FIFO ODB
both without the flag (must still diverge) and with it (must converge).

**Applying it.** Bind-mount the patched script over the container's copy:

```bash
docker run --rm \
  -v /grid/TR-1um_stdcell:/grid/TR-1um_stdcell \
  -v $PWD/flow/patches/librelane/gpl.tcl:/usr/local/lib/python3.12/dist-packages/librelane/scripts/openroad/gpl.tcl:ro \
  ... hpretl/iic-osic-tools:latest --skip bash -lc '...'
```

The GitHub workflow does exactly that (`.github/workflows/pdk-regression.yml`).

**Version pinning.** The patch is a copy of the script shipped with
LibreLane 3.1.0.dev3 in the IIC-OSIC tools image
`hpretl/iic-osic-tools@sha256:306585de35d198e70ea58950f77147c86f56c698726a19afea9f1c83009557be`.
When the image (and thus LibreLane's script) is bumped, regenerate the patch
from the new `gpl.tcl` and keep only the marked `-disable_pin_density_adjust`
line.  The regression check will report if the workaround becomes obsolete.

**Upstream.** The instability is in OpenROAD's pin-density adjustment for
these cell aspect ratios; the clean long-term fix is an upstream change (or
a LibreLane config knob for `-disable_pin_density_adjust`).

## Same file: deterministic manual placement hook

`gpl.tcl` additionally sources `$DESIGN_DIR/manual_place.tcl` when the design
provides one, then writes the views and exits the step.  This mirrors the
TR-1um flow's override (`flow/librelane_override/librelane/scripts/openroad/
gpl.tcl`) and is what makes the 75.6 um-cell designs placeable without
RePlAce spreading cells into the illegal well-spacing band.  See
`examples/tr1um_fifo4/manual_place.tcl` and that design's README.

The same hook is reused by the 59.4 um compact-cell library
(`libs.ref/TR10_cmp_sc`): `examples/inv_cmp/manual_place.tcl` places cells
on every other N row (118.8 um pitch) — the row pitch below which the
cells' WN halos violate DRC — and is the flow's working smoke test for
`TR10_cmp_sc` integration.

## `librelane/cts.tcl` and `rsz_timing_postcts.tcl` — post-CTS PG reconnect

**Symptom.**  CTS and the post-CTS resizer create new clock/hold buffers
after `Odb.SetPowerConnections` has run.  The pre-PDN per-instance
`global_connect` rules do not match those new instance names, so their
VDD/GND pins stay floating.  PSM then reports unconnected CTS buffers and
IR-drop/check_power_grid connectivity fails.

**Workaround.**  Both scripts now source
`openroad/common/set_power_nets.tcl` and call `set_global_connections`
after the new cells are created (after CTS legalization in `cts.tcl`, and
after post-CTS hold repair/legalization in `rsz_timing_postcts.tcl`).
This adds generic `.*`/VDD/GND global connections, so the new cells are on
the power grid before the views are written.  The exact added blocks are
marked with a `TR10:` comment in the two files.

These are copies of the LibreLane 3.1.0.dev3 scripts, like `gpl.tcl`; bind
them over the installed copies when running the flow.

## TR10_cmp_sc notes (59.4 um cell library)

`libs.tech/librelane/TR10_cmp_sc/` carries the compact library's flow
config.  Non-obvious constraints discovered while integrating it:

- **PDN: M1 followpins + M2 straps at the TAP2 columns**
  (`pdn_cmp_sc.tcl`).  `add_pdn_stripe -followpins` emits a boundary rail
  at every row start, which lands on the cells' M1 PG bands.  Six
  full-height M2 stripes are added at the TAP2 columns
  (GND 229.5/445.5/661.5 um, VDD 234.9/450.9/666.9 um), and
  `add_pdn_connect` adds the M1M2 vias.  `-pins M2` turns the M2 straps
  into VDD/GND block terminals; without them PSM fails with `PSM-0025` and
  IR-drop aborts with `PSM-0069`.  A die-margin M1 ring still shorts to
  the edge IO pins; no ring is used.
- **N-only rows for PDN continuity.**  FS rows mirror the TAP2 M2 PG
  straps, so the VDD and GND strap columns swap between N and FS rows and
  a straight M2 strap cannot stay on one net.  `manual_place.tcl` deletes
  the FS rows and inserts fixed TAP2 at x = 226.8/442.8/658.8 um on every
  remaining N row; all placed cells (including CTS/hold buffers) are then
  R0 and the M2 straps stay inside TAP2 or empty rows.  See
  `flow/experiments/pdn_cts/README.md`.
- **Routing uses the upstream two-LEF + expanded-guide trick** — see
  `examples/tr1um_fifo4_cmp/README.md`.  `drt.tcl` (this patch directory)
  additionally calls `read_guides $DESIGN_DIR/expanded.guide` when a design
  ships that file, so TritonRoute consumes the M1-pin-LEF global guides
  produced by `flow/scripts/tr1um_route_guide.py` instead of the M2-only
  guides that an ODB `global_route` leaves.
  The upstream C4004 run needs `-droute_end_iter 40`
  (`DRT_OPT_ITERS`): at the LibreLane default of 16 the tail is still
  descending (331 -> 96 -> 35 -> 19 -> **17** violations) and only the
  longer annealing pass reaches 0.

## `librelane/dpl.tcl` — post-DPL hook

**Need.** `scripts/openroad/common/dpl.tcl` starts with `remove_fillers`, so
any filler a design placed itself is deleted before legalisation.  That is
normally correct (fillers are not logic), but `examples/c4004_cmp` replays
the upstream C4004 layout, where 129 `FILL3`/`FILL2` cells are part of the
physical intent: consecutive logic cells sit 16.2 um apart in places and the
filler is what merges the two N-well islands (without it the gap is 3.6 um
and fails `WN.S1` < 4.0 and `WN.S7` < 12.0).

**Workaround.** The patched `dpl.tcl` sources `$DESIGN_DIR/post_dpl.tcl`
after `detailed_placement` and *before* the final `check_placement`, so the
re-inserted cells are validated and written into the views.  The hook in
`examples/c4004_cmp` replays the filler instances from the same generated
`placements.tcl` the GPL hook uses, marks them `FIRM`, and re-runs
`set_global_connections` so they join the VDD/GND nets.  A design without
`post_dpl.tcl` is unaffected.

**Version pinning.** Copy of the script shipped with LibreLane 3.1.0.dev3 in
the pinned IIC-OSIC tools image; only the marked `TR10:` block before
`check_placement` is added.

## `librelane/pdn.tcl` — post-PDN geometry hook

**Need.** `examples/c4004_cmp` reproduces the upstream C4004 power grid,
which cannot be expressed with `pdngen` alone: the row rails must extend to
x = 1818.8 um (past the row-grid core area, which `initialize_floorplan`
snaps to 1836 um), the M2 straps must stop at the SRAM and at the north bus,
and eight additional M1 rails must connect SRAM128.  Faking it with extra
`add_pdn_stripe` calls collides with the generated straps.

**Workaround.** The patched `pdn.tcl` sources `$DESIGN_DIR/post_pdn.tcl`
right after `pdngen` succeeds and *before* `write_views` and
`check_power_grid`, so the custom geometry is written into the views and is
part of the PSM grid check.  A design without `post_pdn.tcl` is unaffected.

`examples/c4004_cmp/post_pdn.tcl` uses the hook to delete every pdngen shape
(straps **and** vias), rebuild 22 row rails, 8 M2 straps, 8 SRAM M1 rails
and the north VDD M1 bus, add 100 V1 vias and rebuild the VDD/GND block
terminals as `FIRM` b-pins.  The vias are regenerated because pdngen's
`add_pdn_connect` arrays violate the TR10 V1 rules (1.4 um vias on a 2.6 um
pitch: `V1.S1` needs 1.5 um spacing) and, at the TAP2 columns, land on the
tap's substrate contacts (`V1.CO`); see the design README.  Two OpenROAD
binding details matter:

- `dbInst`/`dbBPin` `setPlacementStatus` accepts
  `NONE/UNPLACED/PLACED/FIRM/COVER/LOCKED` but **not** `FIXED`
  (`ValueError Unknown placement status`).
- `check_power_grid` only counts `dbBPin` terminals whose placement status
  is `FIRM`; otherwise PSM aborts with `PSM-0025 ... does not contain any
  terminals`.

**Version pinning.** Like the other files here, `pdn.tcl` is a copy of the
script in the pinned IIC-OSIC tools image; only the marked
`TR10:` block after the `pdngen` error handler is added.  `drt.tcl` was
refreshed against the same image: the current upstream script has no
`set_thread_count` call (`OPENROAD_THREADS`/`-threads` is handled by the
step) and still has the `DRT_DISABLE_AUTO_TAPER` block, so a patch copied
from an older LibreLane must not reintroduce either difference.

**IR-drop voltage-source files are parsed strictly.** `-vsrc` files are
read as raw CSV lines (`x, y, size, voltage`); the parser does not skip
comments, so a leading `#` header aborts the step with the terse OpenROAD
error `irdrop.tcl, 51 stod`.  Keep `.loc` files comment-free and document
their meaning in the design README instead.
