#!/usr/bin/env python3
"""Check a CANOPY static checkout's downloaded assets and describe its scene."""
import argparse
import hashlib
import json
from pathlib import Path


def inspect(root):
    root = root.resolve()
    manifest = json.loads((root / "download-manifest.json").read_text())
    failures = []
    for entry in manifest["files"]:
        asset = (root / entry["path"]).resolve()
        if root not in asset.parents:
            failures.append({"path": entry["path"], "error": "path escapes site"})
            continue
        if not asset.is_file():
            failures.append({"path": entry["path"], "error": "missing"})
            continue
        digest = hashlib.sha256()
        with asset.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if asset.stat().st_size != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
            failures.append({"path": entry["path"], "error": "size or SHA256 differs"})
    expected_total = sum(entry["bytes"] for entry in manifest["files"])
    if expected_total != manifest["bytes"]:
        failures.append({"path": "download-manifest.json", "error": "total bytes differs"})
    catalog = json.loads((root / "scenes/index.json").read_text())
    scene_id = catalog["default"]
    scene = json.loads((root / "scenes" / scene_id / "scene.json").read_text())
    report = {
        "scene": scene_id,
        "manifest_version": manifest["version"],
        "checked_files": len(manifest["files"]),
        "manifest_bytes": expected_total,
        "grid": scene["grid"],
        "fields": {
            key: {name: value.get(name) for name in ("file", "cell_m", "frames", "own_clock", "y")}
            for key, value in scene["layers"].items()
        },
        "wind_history_overrides_display": bool(scene.get("wind_history")),
        "temperature_hidden": scene.get("corridor_context", {}).get("temperature_hidden"),
        "traffic_source": scene.get("corridor_context", {}).get("traffic_meta"),
        "failures": failures,
    }
    print(json.dumps(report, indent=2))
    return bool(failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    raise SystemExit(inspect(args.site.resolve()))
