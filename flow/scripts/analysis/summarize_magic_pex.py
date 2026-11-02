#!/usr/bin/env python3
"""Summarize Magic PEX output and the complementary FastHenry deck."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


_VALUE_RE = re.compile(r"^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)([fpnumkKMGT]?)$")
_SUFFIX_SCALE = {
    "": 1.0,
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}


def _value(token: str) -> float | None:
    match = _VALUE_RE.match(token.strip())
    if match is None:
        return None
    return float(match.group(1)) * _SUFFIX_SCALE[match.group(2)]


def _parse_spice(path: Path) -> dict[str, Any]:
    devices = 0
    capacitors = 0
    resistors = 0
    inductors = 0
    capacitor_farads = 0.0
    resistor_ohms = 0.0
    nodes: set[str] = set()
    models: dict[str, int] = {}
    warnings: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("*"):
            continue
        fields = line.split()
        kind = fields[0][:1].upper()
        if kind in {"M", "Q", "D"}:
            devices += 1
            nodes.update(fields[1:5])
            if len(fields) > 5:
                models[fields[5]] = models.get(fields[5], 0) + 1
        elif kind == "C":
            capacitors += 1
            nodes.update(fields[1:3])
            if len(fields) > 3:
                parsed = _value(fields[3])
                if parsed is not None:
                    capacitor_farads += parsed
        elif kind == "R":
            resistors += 1
            nodes.update(fields[1:3])
            if len(fields) > 3:
                parsed = _value(fields[3])
                if parsed is not None:
                    resistor_ohms += parsed
        elif kind == "L":
            inductors += 1
            nodes.update(fields[1:3])
        for node in fields[1:5]:
            if node.startswith("w_"):
                warnings.add("unbound_well_or_substrate_node_in_magic_output")
    return {
        "devices": devices,
        "capacitors": capacitors,
        "resistors": resistors,
        "inductors": inductors,
        "capacitor_total_f": capacitor_farads,
        "resistor_total_ohm": resistor_ohms,
        "node_count": len(nodes),
        "nodes": sorted(nodes),
        "models": dict(sorted(models.items())),
        "warnings": sorted(warnings),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spice", type=Path, required=True)
    parser.add_argument("--ext", type=Path, required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--magic-tech", type=Path, required=True)
    parser.add_argument("--gds", type=Path, required=True)
    parser.add_argument("--layout-json", type=Path, required=True)
    parser.add_argument("--fast-henry-status", required=True)
    parser.add_argument("--fast-henry-input", type=Path)
    parser.add_argument("--fast-henry-log", type=Path)
    parser.add_argument("--fast-henry-solver")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.spice.is_file():
        raise SystemExit(f"Magic SPICE output does not exist: {args.spice}")
    if not args.ext.is_file():
        raise SystemExit(f"Magic extraction database does not exist: {args.ext}")
    layout = json.loads(args.layout_json.read_text(encoding="utf-8"))
    spice = _parse_spice(args.spice)
    warnings = set(layout.get("warnings", [])) | set(spice.pop("warnings", []))
    warnings.add("magic_output_is_engineering_pex_not_foundry_qualified")
    warnings.add("magic_default_path_extracts_devices_and_capacitance_only")
    manifest = {
        "schema": 1,
        "design": args.design,
        "qualification": "engineering_estimate_not_foundry_qualified",
        "source": {
            "gds": str(args.gds),
            "top": args.design,
            "layout_json": str(args.layout_json),
        },
        "magic": {
            "technology": str(args.magic_tech),
            "spice": str(args.spice),
            "ext": str(args.ext),
            "mode": "extract_all_ext2spice",
        },
        "parasitics": spice,
        "fast_henry": {
            "status": args.fast_henry_status,
            "input": str(args.fast_henry_input) if args.fast_henry_input else None,
            "run_log": str(args.fast_henry_log) if args.fast_henry_log else None,
            "solver": args.fast_henry_solver,
            "provides": ["frequency_dependent_resistance", "inductance", "mutual_inductance"],
            "does_not_provide": ["device_models", "junction_capacitance", "interconnect_capacitance"],
        },
        "warnings": sorted(warnings),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote Magic PEX manifest: {args.output}")
    print(
        "devices={devices} capacitors={capacitors} resistors={resistors} nodes={node_count}".format(
            **spice
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
