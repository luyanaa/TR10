# TR-1um analog PEX

This directory is the analog parasitic-extraction boundary for the manual
`TR-1um` PDK.

## Extraction contract

`flow/signoff/run_magic_pex.sh` is the canonical analog entry point.  It takes
an analog GDS and top-cell name and produces:

- `<base>.spice`: Magic `extract all` + `ext2spice` output, including devices
  and lumped capacitance;
- `<base>.ext`: the native Magic extraction database;
- `<base>.layout.json`: normalized routed geometry;
- `<base>.fasthenry.inp`: a FastHenry2 conductor deck;
- `<base>.pex_manifest.json`: provenance, counts, warnings, and solver status.

The default Magic path deliberately uses the stable `extract all` flow.  The
installed Magic 8.3.623 full `extract do resistance` path was exercised on the
analog regression GDS and terminated in a segmentation fault, so it is not a
silent default.  Wire resistance/inductance/mutual coupling are represented
by the complementary FastHenry deck instead.

FastHenry is optional at runtime.  The checked-in converter generates a deck
when the `fasthenry` executable is unavailable; set
`PEX_FASTHENRY_BIN=/path/to/fasthenry` to select an installed solver explicitly.
Set `PEX_FASTHENRY_REQUIRED=1` to make missing solver availability or solver
failure fatal.  Set `PEX_FASTHENRY_RUN=0` to generate a deck without executing
the solver.  FastHenry does not generate MOS models or capacitance.

Example (inside the LibreLane nix shell):

```sh
PEX_GDS=flow/align_test/latest/TELESCOPIC_OTA_drawing.gds \
PEX_TOP=TELESCOPIC_OTA \
PEX_OUT=/tmp/tele_ota.magic.spice \
bash flow/signoff/run_magic_pex.sh
```

`layout_to_pex_json.py` accepts either routed DEF or GDS.  DEF preserves route
segments and top-level ports.  GDS is intentionally marked with a
`gds_bbox_approximation` warning: each rectangular M1/M2 shape becomes a
center-line segment and each V1 cut becomes a point via.  This provides a
repeatable geometry input for FastHenry but is not a substitute for a foundry
extraction database.

`tr1um_stackup.xml` contains explicit engineering values.  Metal thicknesses
are derived from the routing LEF sheet resistances (0.05 ohm/square for M1 and
0.03 ohm/square for M2) using 58 MS/m conductivity.  Dielectric thicknesses
and substrate conductivity are placeholders and must be replaced by qualified
process data before signoff.

## Ciel/Open PDK compatibility

The PDK remains usable today through the existing LibreLane manual-PDK path:
`$PDK_ROOT/pdk_root/TR-1um` with `--manual-pdk`.  The directory follows the
Open PDK shape (`libs.ref`, `libs.tech`) and keeps PEX tools under
`libs.tech/pex`, which is the package boundary a Ciel adapter should expose.

Ciel 2.4.0 currently recognizes only the built-in `sky130`, `gf180mcu`, and
`ihp-sg13g2` families.  It cannot select `TR-1um` merely because this
repository has Open-PDK-shaped files.  A real Ciel integration requires
upstream Ciel changes:

1. register a `tr-1um` family and the `TR-1um` variant;
2. add a family build/install adapter that creates
   `$PDK_ROOT/ciel/tr-1um/versions/<version>/TR-1um` and exposes the normal
   `libs.ref`/`libs.tech` tree;
3. add release metadata and a reproducible source/archive entry;
4. make the Ciel-enabled tool environment expose Magic, the FastHenry solver,
   and the PEX stackup as declared runtime inputs.

`ciel_compatibility.json` records this boundary without pretending that the
current Ciel release can build or enable this PDK.  No Ciel cache, symlink, or
user profile is modified by the PEX scripts.

All outputs are engineering estimates until process-qualified technology,
stackup, device models, substrate/well connectivity, and an installed
FastHenry solver are supplied.
