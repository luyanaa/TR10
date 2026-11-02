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

## Cross-check result (measured)

`flow/checks/test_pex_crosscheck.sh` runs both extractors on an identical
27 um x 1.8 um M1 wire (no device). Measured:

| Extractor | Total interconnect cap |
|-----------|------------------------|
| Magic (`ext2spice`, TR10.tech) | 4.581 fF |
| OpenRCX (`TR10.rcx_rules` -> SPEF) | 2.016 fF |
| **Magic / OpenRCX ratio** | **2.27x** |

Root cause (qualitative, not yet closed): the Magic technology file models
substrate coupling and fringe-field capacitance; the OpenRCX rules extract
only to an ideal reference and use a different capacitance table with no
substrate RC network, so OpenRCX systematically under-reports total net
capacitance. To close the loop, add dielectric/substrate data to the RCX
rules so both extractors target the same reference field solution, then
re-run this script and reduce the residual below a documented tolerance.
