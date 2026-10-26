#!/usr/bin/env python3
"""Normalize TR-1um routed geometry for Magic/FastHenry PEX.

The normalized JSON is intentionally small and tool-neutral.  DEF input keeps
router geometry and connections.  GDS input is a deterministic approximation:
rectangular M1/M2 shapes become center-line segments and V1 cuts become point
vias.  The GDS approximation is suitable for generating a FastHenry deck, not
for replacing a signoff router database.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


THIS_FILE = Path(__file__).resolve()
REPO_ROOT = next(
    (
        parent
        for parent in THIS_FILE.parents
        if (parent / "flow/scripts/analysis/extract_tr1um_parasitics.py").is_file()
    ),
    None,
)
if REPO_ROOT is None:  # pragma: no cover - only reachable from a broken install.
    raise RuntimeError("cannot locate repository root from layout_to_pex_json.py")
ANALYSIS_DIR = REPO_ROOT / "flow/scripts/analysis"
sys.path.insert(0, str(ANALYSIS_DIR))

from extract_tr1um_parasitics import (  # noqa: E402
    DefConnection,
    Segment,
    Via,
    flatten_gds,
    parse_def_segments,
    parse_gds,
)


GDS_METAL_LAYERS = {13: "M1", 20: "M2"}
GDS_VIA_LAYERS = {19: "V1"}

def _float(value: Any) -> float:
    return float(value)

def _shape_bbox(shape: Any) -> tuple[float, float, float, float] | None:
    bbox = getattr(shape, "bbox_um", None)
    if bbox is None or len(bbox) != 4:
        return None
    x1, y1, x2, y2 = (_float(item) for item in bbox)
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
def _inside(x: float, y: float, bbox: tuple[float, float, float, float], tolerance: float = 1e-9) -> bool:
    x1, y1, x2, y2 = bbox
    return x1 - tolerance <= x <= x2 + tolerance and y1 - tolerance <= y <= y2 + tolerance



def _shape_net(
    bbox: tuple[float, float, float, float],
    labels: list[tuple[str, float, float]],
) -> str | None:
    candidates = [name for name, x, y in labels if _inside(x, y, bbox)]
    if not candidates:
        return None
    return sorted(set(candidates))[0]


def _rectangle_segment(
    net: str,
    layer: str,
    bbox: tuple[float, float, float, float],
    source: str,
) -> Segment:
    x1, y1, x2, y2 = bbox
    width_x = x2 - x1
    width_y = y2 - y1
    if width_x >= width_y:
        return Segment(net, layer, x1, (y1 + y2) / 2.0, x2, (y1 + y2) / 2.0, max(width_y, 1e-6), source)
    return Segment(net, layer, (x1 + x2) / 2.0, y1, (x1 + x2) / 2.0, y2, max(width_x, 1e-6), source)


def _unique_name(prefix: str, used: set[str]) -> str:
    candidate = prefix
    index = 1
    while candidate in used:
        candidate = f"{prefix}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _segment_record(segment: Segment, index: int) -> dict[str, Any]:
    return {
        "id": f"s{index}",
        "layer": segment.layer,
        "x1": segment.x1_um,
        "y1": segment.y1_um,
        "x2": segment.x2_um,
        "y2": segment.y2_um,
        "width": segment.width_um,
        "source": segment.source,
    }


def _via_record(via: Via, index: int) -> dict[str, Any]:
    return {
        "id": f"v{index}",
        "name": "V1",
        "x": via.x_um,
        "y": via.y_um,
        "lower_layer": via.lower_layer,
        "upper_layer": via.upper_layer,
        "source": via.source,
    }


def _port_record(connection: DefConnection, segments: list[Segment]) -> dict[str, Any]:
    if connection.location_um is None:
        if segments:
            segment = segments[0]
            x = (segment.x1_um + segment.x2_um) / 2.0
            y = (segment.y1_um + segment.y2_um) / 2.0
        else:
            x = y = 0.0
    else:
        x, y = connection.location_um
    layer = "M1"
    if segments:
        layer = min(
            segments,
            key=lambda segment: abs(segment.x1_um - x)
            + abs(segment.y1_um - y)
            + abs(segment.x2_um - x)
            + abs(segment.y2_um - y),
        ).layer
    return {
        "name": connection.node_name,
        "direction": connection.direction,
        "layer": layer,
        "x": x,
        "y": y,
        "instance": connection.instance,
        "pin": connection.pin,
    }


def _assemble_json(
    design: str,
    grouped_segments: dict[str, list[Segment]],
    grouped_vias: dict[str, list[Via]],
    connections: dict[str, list[DefConnection]],
    special_nets: set[str],
    source: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    names = sorted(set(grouped_segments) | set(grouped_vias) | set(connections))
    nets: list[dict[str, Any]] = []
    for net_name in names:
        segments = grouped_segments.get(net_name, [])
        vias = grouped_vias.get(net_name, [])
        ports = [
            _port_record(connection, segments)
            for connection in connections.get(net_name, [])
            if connection.instance is None
        ]
        if not segments and not vias and not ports:
            continue
        nets.append(
            {
                "name": net_name,
                "special": net_name in special_nets,
                "ports": ports,
                "segments": [_segment_record(segment, index) for index, segment in enumerate(segments)],
                "vias": [_via_record(via, index) for index, via in enumerate(vias)],
            }
        )
    if not any(net["segments"] for net in nets):
        raise ValueError("layout contains no M1/M2 routed segments")
    return {
        "schema": 1,
        "design": design,
        "units": {"length": "um"},
        "source": source,
        "nets": nets,
        "warnings": sorted(set(warnings)),
    }


def from_def(
    path: Path,
    lef_dir: Path | None = None,
    rc_path: Path | None = None,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if rc_path is None:
        rc_path = REPO_ROOT / "flow/pdk_root/TR-1um/libs.tech/librelane/rc_estimate.json"
    if not rc_path.is_file():
        raise ValueError(f"DEF normalization requires an RC layer model: {rc_path}")
    rc = json.loads(rc_path.read_text(encoding="utf-8"))
    design, segments, by_net, vias, connections = parse_def_segments(text, rc, lef_dir)
    grouped_segments: dict[str, list[Segment]] = defaultdict(list)
    grouped_vias: dict[str, list[Via]] = defaultdict(list)
    for segment in segments:
        grouped_segments[segment.net].append(segment)
    for via in vias:
        grouped_vias[via.net].append(via)
    special_nets = {
        net
        for net, stats in by_net.items()
        if bool(stats.get("__special_net__"))
    }
    warnings: list[str] = []
    if lef_dir is None:
        warnings.append("def_pin_locations_are_router_or_port_approximations_without_lef")
    return _assemble_json(
        design,
        grouped_segments,
        grouped_vias,
        connections,
        special_nets,
        {
            "kind": "def",
            "path": str(path),
            "lef_dir": str(lef_dir) if lef_dir else None,
            "rc_model": str(rc_path),
        },
        warnings,
    )


def _gds_shapes(path: Path, top: str) -> tuple[list[Any], list[Any], float]:
    needed_layers = {
        (layer, 0)
        for layer in (*GDS_METAL_LAYERS.keys(), *GDS_VIA_LAYERS.keys())
    }
    structures, meters_per_dbu = parse_gds(path, needed_layers)
    shapes, labels = flatten_gds(structures, meters_per_dbu, top, needed_layers)
    if not structures:
        raise ValueError(f"GDS contains no structures: {path}")
    return shapes, labels, meters_per_dbu * 1e6


def from_gds(path: Path, top: str) -> dict[str, Any]:
    shapes, labels, dbu_to_um = _gds_shapes(path, top)
    metal_shapes: dict[str, list[tuple[tuple[float, float, float, float], str]]] = defaultdict(list)
    via_shapes: list[tuple[tuple[float, float, float, float], str]] = []
    labels_by_layer: dict[str, list[tuple[str, float, float]]] = defaultdict(list)
    for label in labels:
        layer = int(label.layer)
        if layer in GDS_METAL_LAYERS:
            x, y = label.point_um
            text = str(label.text).strip()
            if text:
                labels_by_layer[GDS_METAL_LAYERS[layer]].append((text, x, y))
    for shape in shapes:
        layer = int(getattr(shape, "layer", -1))
        datatype = int(getattr(shape, "datatype", 0))
        bbox = _shape_bbox(shape)
        if bbox is None or datatype != 0:
            continue
        if layer in GDS_METAL_LAYERS:
            metal_shapes[GDS_METAL_LAYERS[layer]].append((bbox, "GDS"))
        elif layer in GDS_VIA_LAYERS:
            via_shapes.append((bbox, "GDS"))

    raw_segments: dict[str, list[Segment]] = defaultdict(list)
    raw_vias: list[tuple[str, str, float, float, str]] = []
    warnings = ["gds_bbox_approximation"]
    used_names: set[str] = set()
    shape_nets: dict[tuple[str, int], str] = {}
    parent: dict[str, str] = {}

    def find(net: str) -> str:
        parent.setdefault(net, net)
        root = net
        while parent[root] != root:
            root = parent[root]
        while parent[net] != net:
            next_net = parent[net]
            parent[net] = root
            net = next_net
        return root

    def union(first: str, second: str) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    for layer, layer_shapes in metal_shapes.items():
        for index, (bbox, source) in enumerate(layer_shapes):
            net = _shape_net(bbox, labels_by_layer[layer])
            if net is None:
                net = _unique_name(f"__unlabeled_{layer}", used_names)
                warnings.append("unlabeled_metal_shape_created_synthetic_net")
            used_names.add(net)
            find(net)
            shape_nets[(layer, index)] = net
            raw_segments[net].append(_rectangle_segment(net, layer, bbox, source))

    seen_vias: set[tuple[str, str, float, float]] = set()
    for bbox, source in via_shapes:
        x = (bbox[0] + bbox[2]) / 2.0
        y = (bbox[1] + bbox[3]) / 2.0
        lower_candidates = [
            shape_nets[("M1", index)]
            for index, (metal_bbox, _) in enumerate(metal_shapes["M1"])
            if _inside(x, y, metal_bbox) and ("M1", index) in shape_nets
        ]
        upper_candidates = [
            shape_nets[("M2", index)]
            for index, (metal_bbox, _) in enumerate(metal_shapes["M2"])
            if _inside(x, y, metal_bbox) and ("M2", index) in shape_nets
        ]
        if not lower_candidates or not upper_candidates:
            warnings.append("via_without_both_metal_layers_skipped")
            continue
        lower_net = lower_candidates[0]
        upper_net = upper_candidates[0]
        if lower_net != upper_net:
            warnings.append("via_connects_distinct_labeled_nets")
        via_key = (lower_net, upper_net, round(x, 6), round(y, 6))
        if via_key in seen_vias:
            warnings.append("duplicate_via_shapes_collapsed")
            continue
        seen_vias.add(via_key)
        union(lower_net, upper_net)
        raw_vias.append((lower_net, upper_net, x, y, source))

    grouped_segments: dict[str, list[Segment]] = defaultdict(list)
    grouped_vias: dict[str, list[Via]] = defaultdict(list)
    for net, segments in raw_segments.items():
        root = find(net)
        for segment in segments:
            grouped_segments[root].append(
                Segment(
                    root,
                    segment.layer,
                    segment.x1_um,
                    segment.y1_um,
                    segment.x2_um,
                    segment.y2_um,
                    segment.width_um,
                    segment.source,
                )
            )
    for lower_net, upper_net, x, y, source in raw_vias:
        root = find(lower_net)
        grouped_vias[root].append(Via(root, x, y, "M1", "M2", source))

    connections: dict[str, list[DefConnection]] = defaultdict(list)
    for layer, layer_labels in labels_by_layer.items():
        for label, x, y in layer_labels:
            containing = [
                shape_nets[(layer, index)]
                for index, (bbox, _) in enumerate(metal_shapes[layer])
                if _inside(x, y, bbox) and (layer, index) in shape_nets
            ]
            if containing:
                root = find(containing[0])
                connections[root].append(DefConnection(root, None, label, None, "B", (x, y)))
    return _assemble_json(
        top,
        grouped_segments,
        grouped_vias,
        connections,
        set(),
        {"kind": "gds", "path": str(path), "top": top, "dbu_to_um": dbu_to_um},
        warnings,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--def", dest="def_path", type=Path, help="routed DEF input")
    source.add_argument("--gds", dest="gds_path", type=Path, help="GDS input")
    parser.add_argument("--top", help="GDS top cell (required with --gds)")
    parser.add_argument("--lef-dir", type=Path, help="optional LEF directory for DEF pin locations")
    parser.add_argument("--rc", type=Path, help="RC layer model JSON for DEF route widths")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.gds_path is not None and not args.top:
        raise SystemExit("--top is required with --gds")
    if args.def_path is not None:
        result = from_def(args.def_path, args.lef_dir, args.rc)
    else:
        result = from_gds(args.gds_path, args.top)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote normalized PEX layout: {args.output}")
    print(
        f"nets={len(result['nets'])} "
        f"segments={sum(len(net['segments']) for net in result['nets'])} "
        f"vias={sum(len(net['vias']) for net in result['nets'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
