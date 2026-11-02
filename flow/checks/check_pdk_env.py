#!/usr/bin/env python3
"""TR10 PDK environment/manifest self-check.

Verifies:
  * every file referenced by the LibreLane config and the per-library
    manifests exists inside the repository;
  * Liberty files referenced by manifests match their recorded sha256;
  * RCX_RULESETS points at an OpenRCX .rules file (not JSON);
  * xschem model path resolves to libs.tech/ngspice/models;
  * layer-number sanity: drawing markers (240/0, 241/0) do not collide with
    MDP recognition outputs (150/0, 151/0).

Exit 0 on success, 1 on any failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

FAIL = False


def fail(msg: str) -> None:
    global FAIL
    FAIL = True
    print("FAIL:", msg)


def ok(msg: str) -> None:
    print("ok:  ", msg)


def main() -> int:
    pdk = os.environ.get("PDK", "TR10")
    root = Path(__file__).resolve().parents[2]
    pdk_root_env = os.environ.get("PDK_ROOT")
    if pdk_root_env:
        pdk_root = Path(pdk_root_env)
    else:
        pdk_root = root.parent
    pdk_dir = pdk_root / pdk
    if not pdk_dir.is_dir() and root.name == pdk:
        pdk_dir = root
    if not pdk_dir.is_dir():
        fail(f"PDK directory not found: {pdk_dir}")
        return 1

    # ---- LibreLane config-referenced files ---------------------------------
    cfg = pdk_dir / "libs.tech/librelane/config.tcl"
    cfg_text = cfg.read_text()
    for var, rel in [
        ("TECH_LEFS", "libs.ref/TR10_fd_sc/techlef/TR10_tech.tlef"),
        ("TECH_LEFS", "libs.ref/TR10_gen_sc/techlef/TR10_tech.tlef"),
        ("KLAYOUT_TECH", "libs.tech/klayout/tech/TR10.lyt"),
        ("KLAYOUT_PROPERTIES", "libs.tech/klayout/tech/TR10.lyp"),
        ("KLAYOUT_DRC_RUNSET", "libs.tech/klayout/tech/drc/run.drc"),
        ("KLAYOUT_DEF_LAYER_MAP", "libs.tech/klayout/tech/def_layer_map.map"),
        ("MAGICRC", "libs.tech/magic/TR10.magicrc"),
        ("MAGIC_TECH", "libs.tech/magic/TR10.tech"),
        ("MAGIC_PDK_SETUP", "libs.tech/magic/TR10.tcl"),
        ("NETGEN_SETUP", "libs.tech/netgen/TR10_setup.tcl"),
        ("FP_TRACKS_INFO(fd)", "libs.tech/librelane/TR10_fd_sc/tracks.info"),
        ("FP_TRACKS_INFO(gen)", "libs.tech/librelane/TR10_gen_sc/tracks.info"),
    ]:
        if not (pdk_dir / rel).is_file():
            fail(f"{var} references missing file: {rel}")
    ok("config-referenced tool files exist")

    # ---- RCX_RULESETS sanity -----------------------------------------------
    m = re.search(r'RCX_RULESETS\)\s+"[^"]+"\s+"?\$::env\(PDK_ROOT\)/\$::env\(PDK\)/([^"]+)"?', cfg_text)
    if m:
        rcx = pdk_dir / m.group(1)
        if rcx.suffix == ".json":
            fail("RCX_RULESETS points at a JSON geometry model, not an OpenRCX .rules file")
        elif not rcx.is_file():
            fail(f"RCX_RULESETS target missing: {m.group(1)}")
        else:
            ok(f"RCX_RULESETS -> {m.group(1)}")
    else:
        fail("could not parse RCX_RULESETS from librelane config")

    # ---- manifests ----------------------------------------------------------
    for lib in ("TR10_fd_sc", "TR10_gen_sc"):
        man_path = pdk_dir / f"libs.ref/{lib}/{lib}_manifest.json"
        if not man_path.is_file():
            fail(f"manifest missing: {man_path}")
            continue
        man = json.loads(man_path.read_text())
        for key, rel in man.items():
            if not isinstance(rel, str) or "/" not in rel:
                continue
            target = pdk_dir / rel
            if not target.is_file():
                fail(f"{lib}: manifest references missing {rel}")
                continue
            want = man.get("sha256", {}).get(target.name)
            if want:
                got = hashlib.sha256(target.read_bytes()).hexdigest()
                if got != want:
                    fail(f"{lib}: sha256 mismatch for {rel}")
        ok(f"{lib} manifest: all referenced files present, Liberty sha256 verified")

    # ---- xschem model path ---------------------------------------------------
    xschemrc = (pdk_dir / "libs.tech/xschem/xschemrc").read_text()
    if "libs.tech/spice/models" in xschemrc:
        fail("xschemrc still points at non-existent libs.tech/spice/models")
    elif "libs.tech/ngspice/models" not in xschemrc:
        fail("xschemrc does not reference libs.tech/ngspice/models")
    elif not (pdk_dir / "libs.tech/ngspice/models").is_dir():
        fail("libs.tech/ngspice/models directory missing")
    else:
        ok("xschemrc model path -> libs.tech/ngspice/models")

    # ---- voltage-marker layer sanity -----------------------------------------
    layers_drc = (pdk_dir / "libs.tech/klayout/tech/drc/00_Layers.drc").read_text()
    if re.search(r"V15_MARKER\s*=\s*input\(150", layers_drc):
        fail("V15_MARKER still on 150/0 (collides with MDP DLWLMP)")
    if re.search(r"V27_MARKER\s*=\s*input\(151", layers_drc):
        fail("V27_MARKER still on 151/0 (collides with MDP DLWLMN)")
    for layer, name in [(240, "V15_MARKER"), (241, "V27_MARKER")]:
        if f"input({layer}, 0)" not in layers_drc:
            fail(f"{name} not on expected annotation layer {layer}/0")
    ok("V15/V27 markers moved off foundry recognition layer numbers")

    print("-" * 50)
    print("RESULT:", "FAIL" if FAIL else "PASS")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
