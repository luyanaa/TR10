# TR10_SRAM128 — 32 x 4-bit 6T SRAM hard macro

The SRAM used by the C4004 core, derived from the Apache-2.0 macro published
with [`jun1okamura/TR-1um_C4004`](https://github.com/jun1okamura/TR-1um_C4004)
(`module/SRAM128/`, pinned at `db826b1`).  See `LICENSE` and `NOTICE`.

| view | file |
|---|---|
| LEF | `lef/SRAM128.lef` (1166.1 x 185.6 um, M1/M2 pins) |
| Liberty | `lib/TR10_SRAM128__typ_5p0V_25C.lib` |
| GDS | `gds/SRAM128.gds` |
| SPICE / CDL | `spice/SRAM128.spice`, `cdl/SRAM128.cdl` |
| upstream source snapshot | `src/` (unmodified) |

## Regenerating the views

```bash
python3 flow/scripts/build_sram128_views.py
```

The script rewrites the `src/` snapshot into this library:

- **Layer names** `METAL1`/`METAL2`/`VIA1` -> `M1`/`M2`/`V1`; the ground
  supply `VSS` -> `GND` (the TR10 net name) in LEF, Liberty, SPICE and CDL.
- **Liberty** library renamed to `TR10_SRAM128__typ_5p0V_25C` and explicit
  `pg_pin (VDD)` / `pg_pin (GND)` groups added, otherwise the PDN and the
  IR-drop step cannot see the macro supplies.
- **LEF** `MANUFACTURINGGRID` moved after `UNITS` (OpenROAD
  `LEFPARS-1505`) and the `FOREIGN` statement dropped — see below.
- **GDS** normalised to the LEF origin by
  `flow/scripts/build_sram128_gds.py` (needs `klayout`): every shape of the
  top cell is shifted by (+82.1, +90.1) um so the bounding box becomes
  `(0, 0) - (1166.1, 185.6)` == the LEF `SIZE`, and the `VSS` pin labels are
  renamed `GND`.

`TR10_SRAM128_manifest.json` records the sha256 of every derived file.

The LEF, Liberty, SPICE and CDL rebuild byte-identically, so the manifest
hashes hold.  The GDS does not: KLayout writes the current date and time into
`BGNLIB` and every `BGNSTR` record, so a regeneration changes only those
timestamp bytes (at most a few hundred, depending on how far apart the two
runs are) and no geometry.  Geometric equivalence was verified by re-deriving
the views into a scratch tree and by KLayout comparing bbox
`(0,0)-(1166.1,185.6)` and the A0 pin alignment.

## Known limitation: magic cannot read the macro GDS

The upstream view keeps two constructs that magic's GDS reader rejects:

- shapes on `235/0`, which `libs.tech/magic/TR10.tech` does not map (magic
  prints `Unknown layer/datatype in boundary, layer=235 type=0`), and
- `AREF` arrays whose row displacement it refuses
  (`# rows doesn't divide displacement ref pt`).

Magic still loads the cells, but LibreLane treats the resulting
`Error while reading cell …` lines as fatal, so `examples/c4004_cmp` mounts a
patched `scripts/magic/lef.tcl` that skips `read_macro_gds` (the macro is
already present as an abstract view from `MACRO_LEFS`).  KLayout, OpenROAD and
the PDK DRC/LVS decks read the view without complaint; KLayout is the signoff
GDS tool for this example.

## Why the GDS is shifted

The upstream view is a chip fragment: the geometry starts at
(-82.1, -90.1) um and the LEF compensates with
`FOREIGN SRAM128 82.100 90.100`.  LibreLane merges macro GDS into the design
layout **by cell name only** and does not apply the LEF `FOREIGN` offset, so
the raw view would sit 82.1/90.1 um away from its pins, rails and
obstructions.  Normalising the GDS and dropping `FOREIGN` keeps the two
views consistent for both def2gds and the LVS extraction.

## Use

`examples/c4004_cmp/config.json` attaches the macro through
`MACROS` (GDS/LEF/LIB/SPICE + the fixed instance `u_sram` at
`(340.2, 1614.6)`, orientation `N`), `EXTRA_LEFS`, and
`PDN_MACRO_CONNECTIONS = ["u_sram VDD GND VDD GND"]`.
