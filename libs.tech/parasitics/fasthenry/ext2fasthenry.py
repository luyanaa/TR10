#!/usr/bin/env python3
# Copyright 2026 Yan Lu with DeepSeek V4 Flash and GPT-5.6-Luna
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Convert normalized TR-1um routed geometry into a FastHenry2 deck.

FastHenry supplies frequency-dependent conductor R/L/M.  It does not replace
Magic's device and capacitance extraction; the two outputs are intentionally
kept separate in the PEX manifest.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


# TR-1um LEF cut size.  The normalized converter uses the same name for every
# M1-to-M2 cut because this PDK has one routing via class.
VIA_CUT_UM = {"V1": 1.4}


class Stackup:
    """Metal/via layers and materials read from the PEX stackup XML."""

    def __init__(self, xml_path: Path):
        root = ET.parse(xml_path).getroot()
        materials: dict[str, float] = {}
        for material in root.findall(".//Material"):
            name = material.get("Name")
            if not name:
                continue
            materials[name] = float(material.get("Conductivity", "0") or 0)
        self.materials = materials
        self.layers: dict[str, dict[str, Any]] = {}
        for layer in root.findall(".//Layer"):
            name = layer.get("Name")
            if not name:
                continue
            try:
                zmin = float(layer.get("Zmin"))
                zmax = float(layer.get("Zmax"))
                gds_layer = int(layer.get("Layer"))
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid layer geometry for {name!r}") from error
            self.layers[name] = {
                "zmin": zmin,
                "zmax": zmax,
                "type": (layer.get("Type") or "").upper(),
                "gds": gds_layer,
                "sigma": materials.get(layer.get("Material"), 0.0),
            }
        substrate = next(
            (
                dielectric
                for dielectric in root.findall(".//Dielectric")
                if dielectric.get("Name") == "Substrate"
            ),
            None,
        )
        if substrate is None:
            raise ValueError("stackup has no dielectric named Substrate")
        self.substrate = {
            "zmin": 0.0,
            "zmax": float(substrate.get("Thickness")),
            "sigma": materials.get(substrate.get("Material"), 0.0),
        }

    def metal_z(self, layer_name: str) -> tuple[float, float]:
        layer = self.layers.get(layer_name)
        if layer is None:
            raise ValueError(f"stackup has no layer named {layer_name}")
        return (
            layer["zmin"] - self.substrate["zmax"],
            layer["zmax"] - self.substrate["zmax"],
        )


def _layout_bbox(data: dict[str, Any]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for net in data.get("nets", []):
        for segment in net.get("segments", []):
            xs.extend((float(segment["x1"]), float(segment["x2"])))
            ys.extend((float(segment["y1"]), float(segment["y2"])))
        for via in net.get("vias", []):
            xs.append(float(via["x"]))
            ys.append(float(via["y"]))
    if not xs:
        raise ValueError("normalized layout has no geometry")
    return min(xs), min(ys), max(xs), max(ys)


def _validate_layout(data: dict[str, Any], stackup: Stackup) -> None:
    if data.get("schema") != 1:
        raise ValueError("normalized layout schema must be 1")
    if not data.get("design"):
        raise ValueError("normalized layout has no design name")
    if not data.get("nets"):
        raise ValueError("normalized layout has no nets")
    for net in data["nets"]:
        for segment in net.get("segments", []):
            layer = segment.get("layer")
            if layer not in stackup.layers:
                raise ValueError(f"segment references unknown stackup layer {layer!r}")
            if stackup.layers[layer]["type"] not in {"CONDUCTOR", "METAL"}:
                raise ValueError(f"segment layer {layer!r} is not a conductor")
            if float(segment.get("width", 0)) <= 0:
                raise ValueError(f"segment on {layer!r} has non-positive width")
        for via in net.get("vias", []):
            for layer in (via.get("lower_layer"), via.get("upper_layer")):
                if layer not in stackup.layers:
                    raise ValueError(f"via references unknown stackup layer {layer!r}")


def convert(
    data: dict[str, Any],
    stackup: Stackup,
    out_path: Path,
    fmin: float,
    fmax: float,
    ndec: int,
    nwinc: int,
    nhinc: int,
) -> dict[str, int]:
    _validate_layout(data, stackup)
    lines = [
        f"* TR-1um FastHenry2 deck (generated from {data['design']})",
        "* conductor R/L/M only; Magic supplies device/capacitance PEX",
        "* nets: " + ", ".join(str(net.get("name", "?")) for net in data.get("nets", [])),
        ".units uM",
        "",
    ]

    bbox = _layout_bbox(data)
    half = max(50.0, (bbox[2] - bbox[0]) / 2.0 + 20.0, (bbox[3] - bbox[1]) / 2.0 + 20.0)
    substrate = stackup.substrate
    lines.extend(
        [
            "* lossy silicon substrate (sigma in 1/(um*ohm))",
            f"g1 x1={-half:.4f} y1={-half:.4f} z1=0",
            f"+  x2={half:.4f} y2={-half:.4f} z2=0",
            f"+  x3={half:.4f} y3={half:.4f} z3=0",
            f"+  thick={substrate['zmax']:.4f} sigma={substrate['sigma'] / 1e6:.6g}",
            "+  file=NONE",
            "",
        ]
    )

    node_names: dict[tuple[str, str, float, float], str] = {}
    nodes: dict[tuple[str, str, float, float], tuple[float, float, float]] = {}
    segment_lines: list[str] = []
    external_ports: list[tuple[str, str]] = []

    def z_of(layer_name: str) -> tuple[float, float]:
        zmin, zmax = stackup.metal_z(layer_name)
        return (zmin + zmax) / 2.0, zmax - zmin

    def node(key: tuple[str, str, float, float], x: float, y: float, z: float) -> str:
        if key not in node_names:
            node_names[key] = f"n{len(node_names) + 1}"
            nodes[key] = (x, y, z)
        return node_names[key]

    segment_count = 0
    port_count = 0
    for net in data.get("nets", []):
        net_name = str(net.get("name", "?"))
        for segment in net.get("segments", []):
            layer = str(segment["layer"])
            zmid, thickness = z_of(layer)
            sigma = stackup.layers[layer]["sigma"] / 1e6
            if sigma <= 0:
                raise ValueError(f"layer {layer} has no positive conductivity")
            x1, y1 = float(segment["x1"]), float(segment["y1"])
            x2, y2 = float(segment["x2"]), float(segment["y2"])
            width = float(segment["width"])
            n1 = node((net_name, layer, x1, y1), x1, y1, zmid)
            n2 = node((net_name, layer, x2, y2), x2, y2, zmid)
            segment_count += 1
            segment_lines.append(
                f"e{segment_count} {n1} {n2} w={width:.4f} h={thickness:.4f} "
                f"sigma={sigma:.6g} nwinc={nwinc} nhinc={nhinc}"
            )
        for via in net.get("vias", []):
            lower, upper = str(via["lower_layer"]), str(via["upper_layer"])
            x, y = float(via["x"]), float(via["y"])
            # Terminate the via at the lower-metal top and upper-metal
            # bottom; the V1 stackup layer occupies the gap between them.
            zlo = stackup.metal_z(lower)[1]
            zhi = stackup.metal_z(upper)[0]
            width = VIA_CUT_UM.get(str(via.get("name", "V1")), VIA_CUT_UM["V1"])
            sigma = stackup.layers[upper]["sigma"] / 1e6
            if sigma <= 0:
                raise ValueError(f"via upper layer {upper} has no positive conductivity")
            n1 = node((net_name, lower, x, y), x, y, zlo)
            n2 = node((net_name, upper, x, y), x, y, zhi)
            segment_count += 1
            segment_lines.append(
                f"e{segment_count} {n1} {n2} w={width:.4f} h={abs(zhi - zlo):.4f} "
                f"sigma={sigma:.6g} nwinc={nwinc} nhinc={nhinc}"
            )
        for port in net.get("ports", []):
            layer = str(port["layer"])
            zmid, _ = z_of(layer)
            x, y = float(port["x"]), float(port["y"])
            key = (net_name, layer, x, y)
            port_node = node(key, x, y, zmid)
            external_ports.append((str(port.get("name", port_node)), port_node))
            port_count += 1

    for key, (x, y, z) in nodes.items():
        lines.append(f"{node_names[key]} x={x:.4f} y={y:.4f} z={z:.4f}")
    lines.extend(("", *segment_lines, ""))
    for port_name, port_node in external_ports:
        lines.append(f".external {port_node} {port_name}")
    lines.extend(("", f".freq fmin={fmin:.6g} fmax={fmax:.6g} ndec={ndec}", ".end"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": len(nodes), "segments": segment_count, "ports": port_count}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json", type=Path, help="normalized routed-layout JSON")
    parser.add_argument("stackup", type=Path, help="TR-1um stackup XML")
    parser.add_argument("-o", "--out", type=Path, default=Path("out.inp"))
    parser.add_argument("--fmin", type=float, default=1e8)
    parser.add_argument("--fmax", type=float, default=1e10)
    parser.add_argument("--ndec", type=int, default=20)
    parser.add_argument("--nwinc", type=int, default=4)
    parser.add_argument("--nhinc", type=int, default=2)
    args = parser.parse_args(argv)
    data = json.loads(args.json.read_text(encoding="utf-8"))
    counts = convert(
        data,
        Stackup(args.stackup),
        args.out,
        args.fmin,
        args.fmax,
        args.ndec,
        args.nwinc,
        args.nhinc,
    )
    print(f"wrote {args.out}: {counts['nodes']} nodes, {counts['segments']} segments, {counts['ports']} ports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
