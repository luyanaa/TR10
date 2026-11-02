# TR10 Parasitic Extraction Stackup

## Status: engineering defaults, NOT signoff-qualified

`TR10_stackup.xml` feeds `ext2fasthenry.py` (FastHenry field-solver PEX). The
values are engineering placeholders assembled from the routing LEF sheet
resistances; they are internally consistent but are **not** fitted to foundry
process data. Do not use the resulting parasitics for sign-off corners.

## What is calibrated vs. placeholder

| Quantity | Source | Confidence |
|----------|--------|------------|
| M1/M2 conductivity | LEF sheet R (0.05/0.03 Ω/sq) + Cu-like σ | usable |
| M1/M2 thickness | derived from σ and sheet R | usable |
| Dielectric thicknesses (PMD/IMD1) | **placeholder** | replace |
| Substrate conductivity | **placeholder** (10 S/m) | replace |
| Via/contact resistance | **absent** | add |
| MOS junction / well-substrate coupling | **absent** | add |
| RC corners (geometry → R/C spread) | **absent** | add |

## To qualify

Replace each `Thickness`/`Conductivity` marked above with foundry process
data, add via-resistance and junction-parasitic models, then re-run the
Magic↔OpenRCX comparison on a common reference net (e.g. an INV output) and
record the residual in this file. A clean PEX sign-off requires the two
extractors to agree within a documented tolerance on the same layout.

## Cross-check entry point

`flow/signoff/run_magic_pex.sh` produces a Magic PEX netlist. The OpenRCX
path (`RCX_RULESETS`, verified in the P0 round) produces SPEF. Running both
on the same DEF/GDS and diffing the net parasitics is the intended
calibration loop; it has not been closed yet.
