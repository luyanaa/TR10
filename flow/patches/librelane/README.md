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

## TR10_cmp_sc notes (59.4 um cell library)

`libs.tech/librelane/TR10_cmp_sc/` carries the compact library's flow
config.  Non-obvious constraints discovered while integrating it:

- **PDN is followpins-only** (`pdn_cmp_sc.tcl`).  `add_pdn_stripe
  -followpins` emits a boundary rail at every row start, which lands on the
  cells' M1 PG bands.  Any explicit `dbSBox` rail that touches a same-net
  followpin stripe makes `pdngen` report an empty grid (`PDN-0233`), and a
  die-margin strap shorts to the edge IO pins — both were removed.
- **Routing uses the upstream two-LEF + expanded-guide trick** — see
  `examples/tr1um_fifo4_cmp/README.md`.  `drt.tcl` (this patch directory)
  additionally calls `read_guides $DESIGN_DIR/expanded.guide` when a design
  ships that file, so TritonRoute consumes the M1-pin-LEF global guides
  produced by `flow/scripts/tr1um_route_guide.py` instead of the M2-only
  guides that an ODB `global_route` leaves.
