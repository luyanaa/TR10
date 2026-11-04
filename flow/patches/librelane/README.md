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
