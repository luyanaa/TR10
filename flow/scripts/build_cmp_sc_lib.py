#!/usr/bin/env python3
"""Derive the TR10_cmp_sc views from the pinned C4004 source.

The source (``libs.ref/TR10_cmp_sc/src``) is the Apache-2.0 TR-1um standard
cell library published by jun1okamura in TR-1um_C4004.  This script builds the
views LibreLane needs with the naming and electrical model of this PDK:

* technology LEF: site TR1UM (5.4 x 59.4), M1/M2 each on a 5.4 um pitch with a
  2.7 um offset, M1 width 1.8 / space 1.4, M2 width 3.4 / space 2.0;
* cell LEF: signal pins on M2 only, real M1/M2 obstruction polygons carried
  over verbatim from the source LEF (the sparse interior metal leaves room
  for through-cell M1 routing -- a full-cell blockages makes the library
  unroutable), PG pins replaced by full-width abutment rails on M1 (plus
  the TAP M2 straps);
* Liberty: supplies renamed VDD/GND, TAP2S/OSS_ESD_5V_DIO/REG8x16 removed
  (no layout), TIEHI/TIELO added;
* CDL/SPICE: the checked-in transistor netlists, supplies renamed;
* Verilog: powered blackbox-compatible models generated from the LEF ports;
* manifest with sha256 for the PDK self-check.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "libs.ref/TR10_cmp_sc"
SRC = LIB / "src"

ROW_H = 59.4
SITE_W = 5.4
VDD_LO, VDD_HI = 55.7, 58.3
GND_LO, GND_HI = 1.1, 3.7
TIE_W = 2 * SITE_W

INTERNAL_PINS = {"CKB", "CKP", "QM", "QS"}
SOURCE_ONLY_CELLS = {"TAP2S", "OSS_ESD_5V_DIO", "REG8x16"}


def balanced(text: str, match: re.Match) -> str:
    depth = 1
    index = match.end()
    while index < len(text) and depth:
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    return text[match.start():index]


def blocks(text: str, keyword: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in re.finditer(rf"(?i)\b{keyword}\s*\(\s*([^()]+?)\s*\)\s*\{{", text):
        result[match.group(1).strip()] = balanced(text, match)
    return result


def liberty_pins() -> dict[str, dict[str, str]]:
    text = (SRC / "tr1um_typ_5v0_25c.lib").read_text()
    result: dict[str, dict[str, str]] = {}
    for cell, body in blocks(text, "cell").items():
        pins: dict[str, str] = {}
        for pin, pin_body in blocks(body, "pin").items():
            found = re.search(r"(?i)\bdirection\s*:\s*([A-Za-z_]+)\s*;", pin_body)
            if found:
                pins[pin] = found.group(1).lower()
        result[cell] = pins
    return result


def lef_macros() -> dict[str, dict]:
    text = (SRC / "TR-1um_cells.lef").read_text()
    result: dict[str, dict] = {}
    for match in re.finditer(r"(?m)^MACRO (\S+)\n(.*?)^END \1\s*$", text, re.S):
        name, body = match.group(1), match.group(2)
        size = re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;", body)
        klass = re.search(r"CLASS\s+([^;]+);", body)
        pins: dict[str, list[tuple[float, float, float, float]]] = {}
        pin_layers: dict[str, dict[str, list[tuple[float, float, float, float]]]] = {}
        for pin_match in re.finditer(r"(?m)^\s*PIN (\S+)\n(.*?)^\s*END \1\s*$", body, re.S):
            pin_name, pin_body = pin_match.group(1), pin_match.group(2)
            rects = [
                tuple(float(v) for v in r.groups())
                for r in re.finditer(
                    r"RECT\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s*;",
                    pin_body,
                )
            ]
            pins[pin_name] = rects
            # Per-layer pin shapes: the TAP cells need their real (short) M2
            # rail stubs, not a synthesized full-height bar.
            layers: dict[str, list[tuple[float, float, float, float]]] = {}
            parts = re.split(r"(?m)^\s*LAYER\s+(\w+)\s*;\s*$", pin_body)
            for i in range(1, len(parts), 2):
                layers.setdefault(parts[i], []).extend(
                    tuple(float(v) for v in r.groups())
                    for r in re.finditer(
                        r"RECT\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s*;",
                        parts[i + 1],
                    )
                )
            pin_layers[pin_name] = layers
        # Carry the real obstruction shapes (sparse polygons that only cover
        # actual metal, never the whole cell) so detail routing can still
        # cross the interior on M1.  Layer names are remapped to the PDK's.
        obs_lines: list[str] = []
        obs = re.search(r"(?m)^  OBS\n(.*?)^  END[ \t]*$", body, re.S)
        if obs:
            for line in obs.group(1).splitlines():
                line = re.sub(
                    r"LAYER\s+(METAL1|METAL2|VIA1)",
                    lambda m: "LAYER " + {"METAL1": "M1", "METAL2": "M2", "VIA1": "V1"}[m.group(1)],
                    line,
                )
                obs_lines.append(line.rstrip())
        result[name] = {
            "width": float(size.group(1)),
            "height": float(size.group(2)),
            "class": klass.group(1).strip() if klass else "CORE",
            "pins": pins,
            "pin_layers": pin_layers,
            "obs": obs_lines,
        }
    return result


def fmt(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text else "0"


def rect(x0: float, y0: float, x1: float, y1: float) -> str:
    return f"        RECT {fmt(x0)} {fmt(y0)} {fmt(x1)} {fmt(y1)} ;"


def build_techlef() -> str:
    return """VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS
  DATABASE MICRONS 1000 ;
END UNITS
MANUFACTURINGGRID 0.001 ;
SITE TR1UM
  CLASS CORE ;
  SIZE 5.400 BY 59.400 ;
  SYMMETRY Y ;
END TR1UM
# Compatibility site so shared views that hard-reference TR10_access_site
# (e.g. TR10_fd_pr/TR10_gen_pr antenna LEFs) can still be read alongside
# this techlef without an unknown-site error.
SITE TR10_access_site
  CLASS CORE ;
  SIZE 0.100 BY 75.600 ;
  SYMMETRY Y ;
END TR10_access_site
LAYER M1
  TYPE ROUTING ; DIRECTION HORIZONTAL ; WIDTH 1.8 ; MINWIDTH 1.8 ; SPACING 1.4 ; PITCH 5.4 ; OFFSET 2.7 ; AREA 3.24 ;
  RESISTANCE RPERSQ 0.050 ; CAPACITANCE CPERSQDIST 0.000035 ; EDGECAPACITANCE 0.000050 ;
END M1
LAYER V1
  TYPE CUT ; WIDTH 1.4 ; SPACING 1.5 ;
  RESISTANCE 1.000 ;
  # Engineering nominal via resistance; sensitivity range is 0.5..2.0 ohm.
END V1
LAYER M2
  TYPE ROUTING ; DIRECTION VERTICAL ; WIDTH 3.4 ; MINWIDTH 3.0 ; SPACING 2.0 ; PITCH 5.4 ; OFFSET 2.7 ; AREA 9.0 ;
  RESISTANCE RPERSQ 0.030 ; CAPACITANCE CPERSQDIST 0.0000175 ; EDGECAPACITANCE 0.000050 ;
END M2
VIA M1M2_V1 DEFAULT
  LAYER M1 ; RECT -1.7 -1.7 1.7 1.7 ;
  LAYER V1 ; RECT -0.7 -0.7 0.7 0.7 ;
  LAYER M2 ; RECT -1.7 -1.7 1.7 1.7 ;
END M1M2_V1
END LIBRARY
"""


def pg_pins(name: str, width: float, klass: str, pin_layers: dict | None = None) -> str:
    pin_layers = pin_layers or {}

    def m2_rects(pin: str, fallback_x0: float, fallback_x1: float) -> list[str]:
        """Real M2 stubs from the source LEF, or a conservative fallback.

        The TAP cells carry two short M2 stubs at each rail (y 1.1..4.5 and
        54.9..58.3) plus an M2 obstruction between them.  Synthesizing a
        full-height bar instead makes the cell look like it owns a whole M2
        signal track *and* leaves the real obstruction undeclared, so signal
        wires short to VDD/GND at every TAP instance.
        """
        rects = (pin_layers.get(pin) or {}).get("METAL2") or [] if TAP_SOURCE_M2 else []
        if rects:
            return [rect(*r) for r in rects]
        return [rect(fallback_x0, GND_LO, fallback_x1, VDD_HI)]

    lines = [
        "  PIN VDD",
        "    DIRECTION INOUT ;",
        "    USE POWER ;",
        "    PORT",
        "      LAYER M1 ;",
        rect(0, VDD_LO, width, VDD_HI),
    ]
    if klass.endswith("WELLTAP"):
        lines += ["      LAYER M2 ;"] + m2_rects("vdd", 6.4, 9.8)
    lines += ["    END", "  END VDD", "  PIN GND", "    DIRECTION INOUT ;", "    USE GROUND ;", "    PORT", "      LAYER M1 ;", rect(0, GND_LO, width, GND_HI)]
    if klass.endswith("WELLTAP"):
        lines += ["      LAYER M2 ;"] + m2_rects("vss", 1.0, 4.4)
    lines += ["    END", "  END GND"]
    return "\n".join(lines)


def complement_rects(width: float, height: float, holes: list[tuple[float, float, float, float]]) -> list[tuple[float, float, float, float]]:
    """Rectangle-decompose ``[0,width] x [0,height]`` minus ``holes``.

    LEF OBS has no concept of holes, so a "sparse hole" in a full-cell
    blockage has to be expressed as a set of covering rectangles.  A
    scanline over the hole x-boundaries emits one vertical slab per column
    and fills the y-gaps inside each slab.
    """
    xs = sorted({0.0, width, *[h[0] for h in holes], *[h[2] for h in holes]})
    out: list[tuple[float, float, float, float]] = []
    for xa, xb in zip(xs, xs[1:]):
        if xb - xa <= 1e-9:
            continue
        spans = sorted((h[1], h[3]) for h in holes if h[0] < xb - 1e-9 and h[2] > xa + 1e-9)
        merged: list[list[float]] = []
        for y0, y1 in spans:
            if merged and y0 <= merged[-1][1] + 1e-9:
                merged[-1][1] = max(merged[-1][1], y1)
            else:
                merged.append([y0, y1])
        y = 0.0
        for y0, y1 in merged:
            if y0 > y + 1e-9:
                out.append((xa, y, xb, y0))
            y = max(y, y1)
        if y < height - 1e-9:
            out.append((xa, y, xb, height))
    return out


def build_cell_lef(name: str, info: dict, directions: dict[str, str], signal_layer: str = "M2") -> str:
    width = info["width"]
    klass = info["class"]
    lines = [
        f"MACRO {name}",
        f"  CLASS {klass} ;",
        f"  FOREIGN {name} 0 0 ;",
        "  ORIGIN 0 0 ;",
        f"  SIZE {fmt(width)} BY {fmt(info['height'])} ;",
        "  SITE TR1UM ;",
        "  SYMMETRY X Y ;",
        pg_pins(name, width, klass, info.get("pin_layers")),
    ]

    # The source LEF's non-M1 obstructions (the TAP cells' M2 bars) are real
    # metal and must stay declared; otherwise signal M2 routes straight
    # through a TAP and shorts to VDD/GND.
    source_m2_obs: list[str] = []
    current_layer = None
    for obs_line in (info["obs"] if TAP_SOURCE_M2 else []):
        layer_match = re.search(r"LAYER\s+(\w+)", obs_line)
        if layer_match:
            current_layer = layer_match.group(1)
            continue
        if current_layer == "M2" and re.search(r"RECT|POLYGON", obs_line):
            source_m2_obs.append(obs_line)

    internal_obs: list[str] = []
    signal_rects: list[tuple[float, float, float, float]] = []
    for pin, rects in info["pins"].items():
        low = pin.lower()
        if low in {"vdd", "vss"}:
            continue
        if pin in INTERNAL_PINS:
            internal_obs += rects
            continue
        direction = directions.get(pin, "inout").upper()
        if name in {"TLAT"}:
            direction = "OUTPUT" if pin in {"Q", "QB"} else "INPUT"
        signal_rects += rects
        lines += [
            f"  PIN {pin}",
            f"    DIRECTION {direction} ;",
            "    USE SIGNAL ;",
            "    PORT",
            f"      LAYER {signal_layer} ;",
        ]
        lines += [rect(*r) for r in rects]
        lines += ["    END"]
        if PIN_HOLES and signal_layer == "M2":
            # The C4004 cells carry a real M1 landing pad under every signal
            # pin (verified in the GDS: each pin rect is fully covered by M1)
            # plus a 1.4x1.4 V1 at the pin centre.  The upstream LEF omits
            # both, so declare the M1 pad as a second port of the same pin.
            lines += ["    PORT", "      LAYER M1 ;"]
            lines += [rect(*r) for r in rects]
            lines += ["    END"]
        lines += ["  END " + pin]

    if PIN_HOLES and signal_layer == "M2":
        # Sparse-hole experiment: keep the cell interior blocked except at
        # the signal pins, where the source GDS has real M1/V1 pin-access
        # metal.  M1 gets a pad-sized hole, V1 a 1.4x1.4 hole on the pin
        # centre so a routing via lands exactly on the cell's own V1.
        v1_holes = [((r[0] + r[2]) / 2 - 0.7, (r[1] + r[3]) / 2 - 0.7, (r[0] + r[2]) / 2 + 0.7, (r[1] + r[3]) / 2 + 0.7) for r in signal_rects]
        lines += ["  OBS", "    LAYER M1 ;"]
        lines += [rect(*r) for r in complement_rects(width, info["height"], signal_rects)]
        lines += ["    LAYER V1 ;"]
        lines += [rect(*r) for r in complement_rects(width, info["height"], v1_holes)]
        if source_m2_obs:
            lines += ["    LAYER M2 ;"] + source_m2_obs
    elif FULL_OBS:
        # Full-cell M1/V1 blockages keep detail routing out of the cell
        # interior (pin access then escapes through the inter-cell gaps).
        lines += ["  OBS", "    LAYER M1 ;", rect(0, 0, width, info["height"]), "    LAYER V1 ;", rect(0, 0, width, info["height"])]
        if source_m2_obs:
            lines += ["    LAYER M2 ;"] + source_m2_obs
    else:
        # Sparse-OBS variant (pin-access experiment): keep the real upstream
        # METAL1 obstruction polygons plus a full-cell V1 blockage, so M1
        # routing may cross the cell interior on the empty columns while V1
        # still cannot land inside the footprint.  This is what the upstream
        # .lef actually encodes.
        lines += ["  OBS", "    LAYER M1 ;"]
        for ol in info["obs"]:
            if re.search(r"LAYER\s+M1", ol):
                continue
            for sh in ol.splitlines():
                if re.search(r"RECT|POLYGON", sh):
                    lines.append(sh)
        lines += ["    LAYER V1 ;", rect(0, 0, width, info["height"])]
    if internal_obs:
        lines.append("    LAYER M2 ;")
        lines += [rect(*r) for r in internal_obs]
    lines += ["  END", f"END {name}", ""]
    return "\n".join(lines)


def build_tie_lef(name: str, high: bool) -> str:
    pin = "HI" if high else "LO"
    strap = (3.4, 42.7, 6.4, VDD_LO) if high else (3.4, GND_HI, 6.4, 16.2)
    return "\n".join(
        [
            f"MACRO {name}",
            "  CLASS CORE ;",
            f"  FOREIGN {name} 0 0 ;",
            "  ORIGIN 0 0 ;",
            f"  SIZE {fmt(TIE_W)} BY {fmt(ROW_H)} ;",
            "  SITE TR1UM ;",
            "  SYMMETRY X Y ;",
            pg_pins(name, TIE_W, "CORE"),
            f"  PIN {pin}",
            "    DIRECTION OUTPUT ;",
            "    USE SIGNAL ;",
            "    PORT",
            "      LAYER M1 ;",
            rect(*strap),
            "    END",
            f"  END {pin}",
            # Only the supply stub is real metal; keep the rest of the cell
            # open so M1 can route through like in every other cell.
            "  OBS",
            "    LAYER M1 ;",
            rect(*strap),
            "  END",
            f"END {name}",
            "",
        ]
    )


FULL_OBS = True
# Sparse-V1-hole experiment: full-cell M1/V1 OBS minus pad-sized holes at the
# signal pins, with the cells' real M1 pad declared as an extra pin port.
PIN_HOLES = False
# TAP-cell M2 experiment: use the source LEF's short M2 rail stubs plus its
# middle M2 obstruction instead of the full-height power bar.  The physical
# cell really is a full-height bar (verified in the GDS), so the default
# full-height pin is the accurate abstraction; the OBS split measured worse
# (56 DRC with 14 VDD/GND conflicts vs 34 with 2), so it stays off.
TAP_SOURCE_M2 = False

def build_lef(signal_layer: str = "M2") -> str:
    macros = lef_macros()
    directions = liberty_pins()
    body = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', ""]
    for name, info in macros.items():
        body.append(build_cell_lef(name, info, directions.get(name, {}), signal_layer))
    body.append(build_tie_lef("TIEHI", high=True))
    body.append(build_tie_lef("TIELO", high=False))
    body.append("END LIBRARY")
    return "\n".join(body)


def build_liberty() -> str:
    text = (SRC / "tr1um_typ_5v0_25c.lib").read_text()
    text = re.sub(r"(?i)library\s*\(\s*tr1um_typ_5v0_25c\s*\)", "library (TR10_cmp_sc_typ_5p0V_25C)", text)

    for unwanted in SOURCE_ONLY_CELLS:
        match = re.search(rf"(?i)\bcell\s*\(\s*{re.escape(unwanted)}\s*\)\s*\{{", text)
        if not match:
            continue
        block = balanced(text, match)
        text = text.replace(block, "")

    # Physical cells carry a single lowercase vdd pin.  Turn it into a real
    # Liberty pg_pin pair so OpenROAD/PowerGrid recognise the supply.
    replacements = []
    for match in re.finditer(r"(?i)\bpin\s*\(\s*vdd\s*\)\s*\{", text):
        replacements.append(balanced(text, match))
    replacement = (
        'pg_pin (VDD) {\n      voltage_name : "VDD" ;\n      pg_type : primary_power ;\n    }\n'
        '    pg_pin (GND) {\n      voltage_name : "GND" ;\n      pg_type : primary_ground ;\n    }'
    )
    for block in replacements:
        text = text.replace(block, replacement)

    tie_cells = """
  cell (TIEHI) {
    area : 641.520000 ;
    pg_pin (VDD) {
      voltage_name : "VDD" ;
      pg_type : primary_power ;
    }
    pg_pin (GND) {
      voltage_name : "GND" ;
      pg_type : primary_ground ;
    }
    pin (HI) { direction : output ; function : "1" ; capacitance : 0.05 ; }
  }
  cell (TIELO) {
    area : 641.520000 ;
    pg_pin (VDD) {
      voltage_name : "VDD" ;
      pg_type : primary_power ;
    }
    pg_pin (GND) {
      voltage_name : "GND" ;
      pg_type : primary_ground ;
    }
    pin (LO) { direction : output ; function : "0" ; capacitance : 0.05 ; }
  }
"""
    return text.rstrip().rstrip("}") + tie_cells + "\n}\n"


def rename_supplies(text: str) -> str:
    text = re.sub(r"(?i)(?<![A-Za-z0-9_$])vdd(?![A-Za-z0-9_$])", "VDD", text)
    text = re.sub(r"(?i)(?<![A-Za-z0-9_$])vss(?![A-Za-z0-9_$])", "GND", text)
    return text


def build_spice() -> tuple[str, str]:
    chunks = []
    for path in sorted((SRC / "simulation").glob("*.spice")):
        chunks.append(rename_supplies(path.read_text()))
    header = (
        "* TR10_cmp_sc transistor-level cell models\n"
        "* Derived from TR-1um_C4004/module/STDCELL/simulation (Apache-2.0).\n"
        "* Supplies renamed vdd/vss -> VDD/GND for the TR10 PDK LVS decks.\n\n"
    )
    body = derive_dff2_spice(derive_edff_spice(header + "\n".join(chunks))) + "\n" + build_feedthru_spice() + "\n" + build_tgmux_spice()
    cdl = body.replace("\nMP", "\nM").replace("\nMN", "\nM")
    return body, cdl


def build_verilog() -> str:
    macros = lef_macros()
    directions = liberty_pins()
    functions = {}
    lib_text = (SRC / "tr1um_typ_5v0_25c.lib").read_text()
    for cell, body in blocks(lib_text, "cell").items():
        for pin, pin_body in blocks(body, "pin").items():
            found = re.search(r'function\s*:\s*"([^"]+)"', pin_body)
            if found:
                functions[(cell, pin)] = found.group(1)

    out = ["// TR10_cmp_sc powered models (blackbox-compatible).", ""]
    # TIEHI/TIELO are appended to the LEF by build_lef() but are not in the
    # source LEF, so lef_macros() does not see them -- emit manually.
    tie = {
        "TIEHI": {"pins": {"HI": []}},
        "TIELO": {"pins": {"LO": []}},
    }
    for name, info in list(macros.items()) + list(tie.items()):
        ports = ["VDD", "GND"]
        signal = [p for p in info["pins"] if p.lower() not in {"vdd", "vss"} and p not in INTERNAL_PINS]
        ports += signal
        decl = []
        for pin in ports:
            if pin in {"VDD", "GND"}:
                decl.append(f"  inout {pin};")
            else:
                direction = directions.get(name, {}).get(pin, "inout")
                if name in {"TLAT", "TIEHI", "TIELO"}:
                    direction = "output" if pin not in {"VDD", "GND"} else direction
                decl.append(f"  {direction} {pin};")

        out.append(f"module {name} ({', '.join(ports)});")
        out.extend(decl)
        if name == "TIEHI":
            out.append("  assign HI = 1'b1;")
        elif name == "TIELO":
            out.append("  assign LO = 1'b0;")
        out.append("endmodule")
        out.append("")
        if name == "DFF":
            dports = ["VDD", "GND", "CK", "D0", "Q0", "QB0", "D1", "Q1", "QB1"]
            ddecl = []
            for pin in dports:
                if pin in {"VDD", "GND"}:
                    ddecl.append(f"  inout {pin};")
                elif pin in {"Q0", "Q1", "QB0", "QB1"}:
                    ddecl.append(f"  output {pin};")
                else:
                    ddecl.append(f"  input {pin};")
            out.append(f"module DFF2 ({', '.join(dports)});")
            out.extend(ddecl)
            out.append("endmodule")
            out.append("")
        if name == "EDFFRB":
            eports = ["VDD", "GND"] + list(signal)
            edecl = []
            for pin in eports:
                if pin in {"VDD", "GND"}:
                    edecl.append(f"  inout {pin};")
                else:
                    direction = directions.get("EDFFRB", {}).get(pin, "inout")
                    edecl.append(f"  {direction} {pin};")
            out.append(f"module EDFF ({', '.join(eports)});")
            out.extend(edecl)
            out.append("endmodule")
            out.append("")
    out.append("module FEEDTHRU (VDD, GND, A);")
    out.append("  inout VDD;")
    out.append("  inout GND;")
    out.append("  inout A;")
    out.append("endmodule")
    out.append("")
    out.append("module MUXTG2 (A, B, Y, S, VDD, GND);")
    out.append("  input A;")
    out.append("  input B;")
    out.append("  input S;")
    out.append("  output Y;")
    out.append("  inout VDD;")
    out.append("  inout GND;")
    out.append("endmodule")
    out.append("")
    return "\n".join(out)


def derive_edff_lef(text: str) -> str:
    """Clone the EDFFRB macro as EDFF (same geometry, RSTB pin kept).

    The cell is the existing EDFFRB layout; the netlist ties RSTB high with a
    TIEHI, so no GDS edit is needed and the reset gate is held inactive.
    """
    match = re.search(r"(?ms)^MACRO EDFFRB\n(.*?)^END EDFFRB", text)
    if not match:
        return text
    block = (
        match.group(0)
        .replace("MACRO EDFFRB", "MACRO EDFF")
        .replace("END EDFFRB", "END EDFF")
        .replace("FOREIGN EDFFRB", "FOREIGN EDFF")
    )
    return text.replace("END LIBRARY", block + "\nEND LIBRARY", 1)


def derive_edff_liberty(text: str) -> str:
    """Clone EDFFRB as EDFF (same pins incl. RSTB; the netlist ties it high)."""
    match = re.search(r"(?i)\bcell\s*\(\s*EDFFRB\s*\)\s*\{", text)
    if not match:
        return text
    block = balanced(text, match)
    block = re.sub(r"(?i)cell\s*\(\s*EDFFRB\s*\)", "cell (EDFF)", block)
    return text.rstrip().rstrip("}") + block + "\n}\n"


def derive_edff_spice(body: str) -> str:
    """Clone the EDFFRB subckt as EDFF (RSTB port kept; tied in the netlist)."""
    match = re.search(r"(?ms)^\.subckt\s+EDFFRB\b.*?^\.ends", body)
    if not match:
        return body
    block = match.group(0).replace(".subckt EDFFRB", ".subckt EDFF", 1)
    return body + "\n" + block


def build_dff2_lef(signal_layer: str = "M2") -> str:
    """Two DFFs with one shared CK pin.

    The second DFF's CK pin is joined to the first with an M2 strap in the
    CK band (y 50.9..54.3); the other DFF pins are in the y 27.9..31.3 band,
    so the strap does not cross them.  ``signal_layer`` is M1 for the GRT
    view and M2 for the DRT view, matching the two-LEF recipe.
    """
    w = 129.6
    lines = [
        "MACRO DFF2",
        "  CLASS CORE ;",
        "  FOREIGN DFF2 0 0 ;",
        "  ORIGIN 0 0 ;",
        f"  SIZE {fmt(w)} BY 59.4 ;",
        "  SITE TR1UM ;",
        "  SYMMETRY X Y ;",
        "  PIN VDD",
        "    DIRECTION INOUT ;",
        "    USE POWER ;",
        "    PORT",
        "      LAYER M1 ;",
        rect(0, 55.7, w, 58.3),
        "    END",
        "  END VDD",
        "  PIN GND",
        "    DIRECTION INOUT ;",
        "    USE GROUND ;",
        "    PORT",
        "      LAYER M1 ;",
        rect(0, 1.1, w, 3.7),
        "    END",
        "  END GND",
    ]
    pins = [
        ("CK", 6.4, 74.6, 50.9, 54.3, "INPUT"),
        ("D0", 11.8, 15.2, 27.9, 31.3, "INPUT"),
        ("D1", 76.6, 80.0, 27.9, 31.3, "INPUT"),
        ("Q0", 60.4, 63.8, 27.9, 31.3, "OUTPUT"),
        ("Q1", 125.2, 128.6, 27.9, 31.3, "OUTPUT"),
        ("QB0", 55.0, 58.4, 27.9, 31.3, "OUTPUT"),
        ("QB1", 119.8, 123.2, 27.9, 31.3, "OUTPUT"),
    ]
    for name, x0, x1, y0, y1, direction in pins:
        lines += [
            f"  PIN {name}",
            f"    DIRECTION {direction} ;",
            "    USE SIGNAL ;",
            "    PORT",
            f"      LAYER {signal_layer} ;",
            rect(x0, y0, x1, y1),
            "    END",
            f"  END {name}",
        ]
    lines += [
        "  OBS",
        "    LAYER M1 ;",
        rect(0, 0, w, 59.4),
        "    LAYER V1 ;",
        rect(0, 0, w, 59.4),
        "  END",
        "END DFF2",
    ]
    return "\n".join(lines)


def derive_dff2_liberty(text: str) -> str:
    """Clone DFF as DFF2: two state groups, D/Q/QB pins suffixed."""
    match = re.search(r"(?i)\bcell\s*\(\s*DFF\s*\)\s*\{", text)
    if not match:
        return text
    block = balanced(text, match)
    block = block.replace("area : 3849.1;", "area : 7698.2;")
    block = re.sub(r"(?i)cell\s*\(\s*DFF\s*\)", "cell (DFF2)", block)
    ff = re.search(r"(?s)ff\s*\(IQ, IQN\)\s*\{.*?\n    \}", block)
    if ff:
        two = (
            'ff (IQ0, IQN0) {\n      next_state : "D0";\n      clocked_on : "CK";\n    }\n'
            '    ff (IQ1, IQN1) {\n      next_state : "D1";\n      clocked_on : "CK";\n    }'
        )
        block = block.replace(ff.group(0), two)
    for pin, p0, p1 in [("D", "D0", "D1"), ("Q", "Q0", "Q1"), ("QB", "QB0", "QB1")]:
        mm = re.search(rf"(?i)\bpin\s*\(\s*{pin}\s*\)\s*\{{", block)
        if not mm:
            continue
        blk = balanced(block, mm)
        b0 = blk.replace(f"pin ({pin})", f"pin ({p0})")
        if pin == "Q":
            b0 = b0.replace('function : "IQ"', 'function : "IQ0"')
        if pin == "QB":
            b0 = b0.replace('function : "IQN"', 'function : "IQN0"')
        b1 = b0.replace(f"pin ({p0})", f"pin ({p1})")
        if pin == "Q":
            b1 = b1.replace('function : "IQ0"', 'function : "IQ1"')
        if pin == "QB":
            b1 = b1.replace('function : "IQN0"', 'function : "IQN1"')
        block = block.replace(blk, b0 + "\n    " + b1)
    return text.rstrip().rstrip("}") + block + "\n}\n"


def derive_dff2_spice(body: str) -> str:
    """Add the DFF2 subckt: two DFF instances sharing CK."""
    block = (
        ".subckt DFF2 CK D0 QB0 Q0 D1 QB1 Q1 VDD GND\n"
        # the LVS contract orders the DFF cell's ports QB,D,Q,CK,VDD,GND
        # (from the extracted layout), so the positional X lines follow it
        "X0 QB0 D0 Q0 CK VDD GND DFF\n"
        "X1 QB1 D1 Q1 CK VDD GND DFF\n"
        ".ends\n"
    )
    return body + "\n" + block


def build_feedthru_lef() -> str:
    """One-site feedthrough: M2 strap through the row + M1 rails + N-well.

    The A pin is a full-height M2 strap; the VDD/GND rails are M1.  There are
    no transistors, so the cell carries the N-well only (to keep the row well
    continuous) and no AA/GP.
    """
    w = 5.4
    lines = [
        "MACRO FEEDTHRU",
        "  CLASS CORE ;",
        "  FOREIGN FEEDTHRU 0 0 ;",
        "  ORIGIN 0 0 ;",
        f"  SIZE {fmt(w)} BY 59.4 ;",
        "  SITE TR1UM ;",
        "  SYMMETRY X Y ;",
        "  PIN VDD", "    DIRECTION INOUT ;", "    USE POWER ;", "    PORT", "      LAYER M1 ;", rect(0, 55.7, w, 58.3), "    END", "  END VDD",
        "  PIN GND", "    DIRECTION INOUT ;", "    USE GROUND ;", "    PORT", "      LAYER M1 ;", rect(0, 1.1, w, 3.7), "    END", "  END GND",
        "  PIN A", "    DIRECTION INOUT ;", "    USE SIGNAL ;", "    PORT", "      LAYER M2 ;", rect(1.0, 0.0, 4.4, 59.4), "    END", "  END A",
        "END FEEDTHRU",
    ]
    return "\n".join(lines)


def build_feedthru_liberty() -> str:
    return """
  cell (FEEDTHRU) {
    area : 320.760000 ;
    pg_pin (VDD) {
      voltage_name : "VDD" ;
      pg_type : primary_power ;
    }
    pg_pin (GND) {
      voltage_name : "GND" ;
      pg_type : primary_ground ;
    }
    pin (A) { direction : inout ; capacitance : 0.05 ; }
  }
"""


def build_feedthru_spice() -> str:
    return ".subckt FEEDTHRU A VDD GND\n.ends\n"


def build_tgmux_lef(signal_layer: str = "M2") -> str:
    """PCell-based 6T TG MUX2 (54.0 x 59.4, M2 signal pins)."""
    # Keep the M1 (global-route) Y pin identical to the M2 (detail-route)
    # pin.  The old 19.0..30.1 M1 pin made global_route approach Y from the
    # lower-left, which forced a Y wire 0.7 um above the internal n4 strap.
    y_pin = (22.0, 27.9, 25.4, 31.3)
    lines = [
        "MACRO MUXTG2",
        "  CLASS CORE ;",
        "  FOREIGN MUXTG2 0 0 ;",
        "  ORIGIN 0 0 ;",
        "  SIZE 54.0 BY 59.4 ;",
        "  SITE TR1UM ;",
        "  SYMMETRY X Y ;",
    ]
    s_rect = (40.2, 27.9, 43.6, 31.3)
    a_rect = (13.5, 27.9, 16.9, 31.3)
    pins = [
        ("VDD", "INOUT", "POWER", 0.0, 55.7, 54.0, 58.3),
        ("GND", "INOUT", "GROUND", 0.0, 1.1, 54.0, 3.7),
        ("A", "INPUT", "SIGNAL", *a_rect),
        ("Y", "OUTPUT", "SIGNAL", *y_pin),
        ("B", "INPUT", "SIGNAL", 32.1, 27.9, 35.5, 31.3),
        ("S", "INPUT", "SIGNAL", *s_rect),
    ]
    # Local M2 keep-outs for the two internal straps.  Detail routing may
    # still cross the cell at the pin band (y27.9..31.3), but must not run
    # parallel at the 0.6/1.4 um spacing seen in the first flow run.
    # n4 is routed entirely on M1.  The S strap is still a full-height M2
    # wall; put the keep-out only in the global-route LEF so global_route
    # pulls the B wire left, while the detail-route LEF stays OBS-free (an
    # OBS at the wire's landing track makes DRT report a wire-to-instance
    # spacing violation).
    obs_m2 = []

    for name, direction, use, x0, y0, x1, y1 in pins:
        layer = "M1" if name in {"VDD", "GND"} else signal_layer
        lines += [
            f"  PIN {name}",
            f"    DIRECTION {direction} ;",
            f"    USE {use} ;",
            "    PORT",
            f"      LAYER {layer} ;",
            f"        RECT {fmt(x0)} {fmt(y0)} {fmt(x1)} {fmt(y1)} ;",
            "    END",
            f"  END {name}",
        ]
    lines += [
        "  OBS",
        "    LAYER M1 ;",
        rect(0, 0, 54.0, 59.4),
        "    LAYER V1 ;",
        rect(0, 0, 54.0, 59.4),
        "    LAYER M2 ;",
    ]
    lines += [rect(*r) for r in obs_m2]
    lines += [
        "  END",
        "END MUXTG2",
    ]
    return "\n".join(lines)

def derive_tgmux_liberty(text: str) -> str:
    """Clone MUX2 as MUXTG2 (same function and pins, 4-site footprint)."""
    match = re.search(r"(?i)\bcell\s*\(\s*MUX2\s*\)\s*\{", text)
    if not match:
        return text
    block = balanced(text, match)
    block = re.sub(r"(?i)cell\s*\(\s*MUX2\s*\)", "cell (MUXTG2)", block)
    block = block.replace("area : 1924.6;", "area : 3207.6;")
    return text.rstrip().rstrip("}") + block + "\n}\n"


def build_tgmux_spice() -> str:
    return (
        ".subckt MUXTG2 A B Y S VDD GND\n"
        "MP0 VDD S n4 VDD PMOS W=5.2u L=1.0u\n"
        "MN5 GND S n4 GND NMOS W=3.4u L=1.0u\n"
        "MP3 A S Y VDD PMOS W=5.2u L=1.0u\n"
        "MN2 A n4 Y GND NMOS W=3.4u L=1.0u\n"
        "MP4 Y n4 B VDD PMOS W=5.2u L=1.0u\n"
        "MN3 Y S B GND NMOS W=3.4u L=1.0u\n"
        ".ends\n"
    )


def write_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main() -> int:
    write_if_changed(LIB / "techlef/TR10_tech.tlef", build_techlef())
    lef = derive_edff_lef(build_lef())
    write_if_changed(LIB / "lef/TR10_cmp_sc.lef", lef.replace("END LIBRARY", build_dff2_lef() + "\n" + build_feedthru_lef() + "\n" + build_tgmux_lef("M2") + "\nEND LIBRARY", 1))
    # Global-route variant: identical except signal pins live on M1 so
    # global_route spends M1 guides over the cells; detail route still uses
    # the M2-pin LEF above (mirrors the upstream C4004 two-LEF flow).
    grt = derive_edff_lef(build_lef(signal_layer="M1"))
    write_if_changed(LIB / "lef/TR10_cmp_sc_grt.lef", grt.replace("END LIBRARY", build_dff2_lef("M1") + "\n" + build_feedthru_lef() + "\n" + build_tgmux_lef("M1") + "\nEND LIBRARY", 1))
    # Sparse-OBS experiment variant: real upstream M1 obstruction polygons +
    # full-cell V1 blockage, so M1 may cross the cell interior on empty
    # columns.  Selected per-design via TR10_CMP_SC_SPARSE_LEF.
    globals()["FULL_OBS"] = False
    write_if_changed(LIB / "lef/TR10_cmp_sc_sparse.lef", build_lef())
    globals()["FULL_OBS"] = True
    # Sparse-V1-hole experiment: M1 pad + V1 hole at every signal pin, with
    # the M1 pad declared as an additional port of the pin.
    globals()["PIN_HOLES"] = True
    write_if_changed(LIB / "lef/TR10_cmp_sc_v1hole.lef", build_lef())
    globals()["PIN_HOLES"] = False
    lib_text = derive_tgmux_liberty(derive_dff2_liberty(derive_edff_liberty(build_liberty())))
    lib_text = lib_text.rstrip().rstrip("}") + build_feedthru_liberty() + "\n}\n"
    write_if_changed(LIB / "lib/TR10_cmp_sc__typ_5p0V_25C.lib", lib_text)
    spice, cdl = build_spice()
    write_if_changed(LIB / "spice/TR10_cmp_sc.spice", spice)
    write_if_changed(LIB / "cdl/TR10_cmp_sc.cdl", cdl)
    write_if_changed(LIB / "verilog/TR10_cmp_sc.v", build_verilog())

    manifest = {
        "library": "TR10_cmp_sc",
        "gds": "libs.ref/TR10_cmp_sc/gds/TR10_cmp_sc.gds",
        "lef": "libs.ref/TR10_cmp_sc/lef/TR10_cmp_sc.lef",
        "lef_grt": "libs.ref/TR10_cmp_sc/lef/TR10_cmp_sc_grt.lef",
        "techlef": "libs.ref/TR10_cmp_sc/techlef/TR10_tech.tlef",
        "cdl": "libs.ref/TR10_cmp_sc/cdl/TR10_cmp_sc.cdl",
        "lib": "libs.ref/TR10_cmp_sc/lib/TR10_cmp_sc__typ_5p0V_25C.lib",
        "spice": "libs.ref/TR10_cmp_sc/spice/TR10_cmp_sc.spice",
        "verilog": "libs.ref/TR10_cmp_sc/verilog/TR10_cmp_sc.v",
        "license": "libs.ref/TR10_cmp_sc/LICENSE",
        "notice": "libs.ref/TR10_cmp_sc/NOTICE",
    }
    hashes = {}
    for rel in manifest.values():
        if not isinstance(rel, str) or "/" not in rel:
            continue
        path = ROOT / rel
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["sha256"] = hashes
    write_if_changed(LIB / "TR10_cmp_sc_manifest.json", json.dumps(manifest, indent=1) + "\n")
    print("generated TR10_cmp_sc views")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
