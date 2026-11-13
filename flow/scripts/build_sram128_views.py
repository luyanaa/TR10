#!/usr/bin/env python3
"""Derive the TR10_SRAM128 hard-macro views from the pinned C4004 source.

The source (``libs.ref/TR10_SRAM128/src``) is the Apache-2.0 SRAM128 macro
published by jun1okamura in TR-1um_C4004.  It is the 32x4-bit 6T SRAM used by
the C4004 core.  This script rewrites the views into the naming and layers of
this PDK:

* LEF: ``METAL1``/``METAL2``/``VIA1`` -> ``M1``/``M2``/``V1``; the ground
  supply ``VSS`` -> ``GND`` (the TR10 PDK name).
* Liberty: library renamed to ``TR10_SRAM128__typ_5p0V_25C`` and explicit
  ``pg_pin (VDD)`` / ``pg_pin (GND)`` records added so OpenROAD power
  connection and IR-drop steps see the supplies.
* SPICE/CDL: ``VSS`` -> ``GND``.
* GDS: shifted to the LEF origin and ``VSS`` pin labels renamed to ``GND``
  by ``build_sram128_gds.py``; the layer numbers already match TR-10.


Run the plain-Python part directly; the GDS label rename is a KLayout script.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "libs.ref/TR10_SRAM128"
SRC = LIB / "src"

LIB_NAME = "TR10_SRAM128__typ_5p0V_25C"

LAYER_MAP = {"METAL1": "M1", "METAL2": "M2", "VIA1": "V1"}


def rename_supplies(text: str) -> str:
    # Only the ground net is renamed; VDD already matches the PDK.
    text = re.sub(r"(?i)(?<![A-Za-z0-9_$])vss(?![A-Za-z0-9_$])", "GND", text)
    return text


def build_lef() -> str:
    text = (SRC / "SRAM128.lef").read_text()
    for old, new in LAYER_MAP.items():
        text = re.sub(rf"\b{old}\b", new, text)
    text = rename_supplies(text)
    # OpenROAD rejects MANUFACTURINGGRID declared before UNITS (LEFPARS-1505).
    text = re.sub(
        r"\nMANUFACTURINGGRID\s+([\d.]+)\s*;\s*\n+UNITS\s*\n\s*DATABASE MICRONS 1000 ;\s*\nEND UNITS\s*\n",
        r"\nUNITS\n    DATABASE MICRONS 1000 ;\nEND UNITS\nMANUFACTURINGGRID \1 ;\n",
        text,
    )
    # The GDS is normalised to the LEF origin (see build_sram128_gds.py), so the
    # upstream FOREIGN offset would only move the macro a second time.
    text = re.sub(r"\n\s*FOREIGN\s+\S+\s+[\d.\-]+\s+[\d.\-]+\s*;", "", text)
    header = (
        "# SRAM128 -- 32 word x 4 bit 6T SRAM macro (C4004)\n"
        "# Derived from jun1okamura/TR-1um_C4004 module/SRAM128 (Apache-2.0).\n"
        "# Layers renamed METAL1/METAL2/VIA1 -> M1/M2/V1; VSS -> GND.\n"
    )
    return header + text


def build_lib() -> str:
    text = (SRC / "SRAM128.lib").read_text()
    text = re.sub(r"library\s*\(\s*sram128_typ_5v0_25c\s*\)", f"library ({LIB_NAME})", text)
    text = rename_supplies(text)
    pg = (
        '    pg_pin (VDD) {\n'
        '      voltage_name : "VDD" ;\n'
        '      pg_type : primary_power ;\n'
        '    }\n'
        '    pg_pin (GND) {\n'
        '      voltage_name : "GND" ;\n'
        '      pg_type : primary_ground ;\n'
        '    }\n'
    )
    match = re.search(r"(\n\s*cell\s*\(\s*SRAM128\s*\)\s*\{)", text)
    if match is None:
        raise SystemExit("SRAM128 cell not found in the Liberty source")
    text = text[: match.end()] + "\n" + pg + text[match.end() :]
    header = (
        "/* TR10_SRAM128 -- derived from jun1okamura/TR-1um_C4004 SRAM128.\n"
        " * Supplies VDD/GND added for OpenROAD power connection; VSS -> GND.\n"
        " */\n"
    )
    return header + text


def build_spice() -> str:
    text = (SRC / "SRAM128.spice").read_text()
    return (
        "* TR10_SRAM128 transistor-level macro model\n"
        "* Derived from TR-1um_C4004/module/SRAM128/simulation (Apache-2.0).\n"
        "* Ground renamed VSS -> GND.\n"
        + rename_supplies(text)
    )


def build_cdl() -> str:
    text = build_spice()
    return text.replace("\nMP", "\nM").replace("\nMN", "\nM")


def write(path: Path, text: str) -> None:
    path.write_text(text)


def build_gds(gds_in: Path, gds_out: Path) -> None:
    """Shift the macro to the LEF origin and rename the VSS labels to GND.

    Delegated to ``build_sram128_gds.py`` (KLayout) because the normalisation
    needs GDS editing.  LibreLane merges macro GDS by cell name without
    applying the LEF FOREIGN offset, so the raw upstream view would be placed
    82.1/90.1 um off.
    """
    import shutil
    import subprocess

    klayout = shutil.which("klayout")
    if klayout is None:
        raise SystemExit(
            "klayout is required to normalise the SRAM128 GDS; "
            "run flow/scripts/build_sram128_gds.py manually"
        )
    script = Path(__file__).with_name("build_sram128_gds.py")
    gds_out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            klayout,
            "-b",
            "-r",
            str(script),
            f"-rd",
            f"src={gds_in}",
            f"-rd",
            f"out={gds_out}",
        ],
        check=True,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    (LIB / "lef").mkdir(parents=True, exist_ok=True)
    (LIB / "lib").mkdir(parents=True, exist_ok=True)
    (LIB / "gds").mkdir(parents=True, exist_ok=True)
    (LIB / "spice").mkdir(parents=True, exist_ok=True)
    (LIB / "cdl").mkdir(parents=True, exist_ok=True)

    write(LIB / "lef/SRAM128.lef", build_lef())
    write(LIB / f"lib/{LIB_NAME}.lib", build_lib())
    write(LIB / "spice/SRAM128.spice", build_spice())
    write(LIB / "cdl/SRAM128.cdl", build_cdl())

    gds_in = SRC / "SRAM128.gds"
    gds_out = LIB / "gds/SRAM128.gds"
    build_gds(gds_in, gds_out)

    notice = (
        "TR10_SRAM128 -- 32x4-bit 6T SRAM hard macro for the C4004 core.\n\n"
        "Derived from jun1okamura/TR-1um_C4004 (Apache-2.0):\n"
        "  module/SRAM128/SRAM128.lef\n"
        "  module/SRAM128/SRAM128.lib\n"
        "  module/SRAM128/SRAM128.gds\n"
        "  module/SRAM128/simulation/SRAM128.spice\n\n"
        "Copyright 2025 OpenSUSI ( https://www.opensusi.org/ )\n"
        "Copyright 2025 ISHI-KAI ( https://ishi-kai.org/ )\n"
        "Copyright 2025 TOKAI RIKA CO., LTD\n\n"
        "Changes: layer names METAL1/METAL2/VIA1 -> M1/M2/V1; ground VSS -> GND;\n"
        "Liberty library renamed and pg_pin records added.  See LICENSE.\n"
    )
    write(LIB / "NOTICE", notice)

    manifest = {
        "library": "TR10_SRAM128",
        "gds": "libs.ref/TR10_SRAM128/gds/SRAM128.gds",
        "lef": "libs.ref/TR10_SRAM128/lef/SRAM128.lef",
        "lib": f"libs.ref/TR10_SRAM128/lib/{LIB_NAME}.lib",
        "cdl": "libs.ref/TR10_SRAM128/cdl/SRAM128.cdl",
        "spice": "libs.ref/TR10_SRAM128/spice/SRAM128.spice",
        "license": "libs.ref/TR10_SRAM128/LICENSE",
        "notice": "libs.ref/TR10_SRAM128/NOTICE",
        "sha256": {
            p.name: sha256(p)
            for p in (
                LIB / "gds/SRAM128.gds",
                LIB / "lef/SRAM128.lef",
                LIB / f"lib/{LIB_NAME}.lib",
                LIB / "cdl/SRAM128.cdl",
                LIB / "spice/SRAM128.spice",
                LIB / "LICENSE",
                LIB / "NOTICE",
            )
        },
    }
    write(LIB / "TR10_SRAM128_manifest.json", json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {LIB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
