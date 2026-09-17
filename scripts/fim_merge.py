#!/usr/bin/env python3
"""
Merge the per-sheet GeoJSON of several georeferenced runs into one FeatureCollection per kind, ready for geojson.io,
QGIS or a web map: one file with every block of the book, one with every page footprint, and so on.

    python3 scripts/fim_merge.py runs/hunyuan/2026-09-16_tiles_p0*_t1024 -o runs/hunyuan/victoria_1895_p04-p10
    -> runs/hunyuan/victoria_1895_p04-p10_blocks_wgs84.geojson
       runs/hunyuan/victoria_1895_p04-p10_page_wgs84.geojson

Every feature gets a 'sheet' property (the run's stem) if it has none. Runs that lack a kind (a sheet that did not
georeference, a sheet without tinted areas) are skipped with a note. --what picks the kinds:
blocks, buildings, page, street_names (default), areas, tokens, blocks_rejected. Only the WGS84 files are merged; the EPSG copies stay per run.
fim_batch.py calls this with --merge.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

KINDS = ["blocks", "buildings", "page", "street_names", "areas", "tokens", "blocks_rejected"]


def stem_of(run: Path) -> str | None:
    g = next(run.glob("*_georef.json"), None)
    return g.name[: -len("_georef.json")] if g else None


def merge(runs: list[Path], kind: str, out: Path) -> tuple[int, list[str]]:
    feats, sources, missing = [], [], []
    for run in runs:
        stem = stem_of(run)
        f = run / f"{stem}_{kind}_wgs84.geojson" if stem else None
        if f is None or not f.exists():
            missing.append(run.name)
            continue
        gj = json.loads(f.read_text())
        for ft in gj.get("features", []):
            ft.setdefault("properties", {}).setdefault("sheet", stem)
            feats.append(ft)
        sources.append({"run": str(run), "file": f.name, "n": len(gj.get("features", [])), "georeference": gj.get("georeference")})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"type": "FeatureCollection",
                               "note": f"{kind} of {len(sources)} sheets merged by scripts/fim_merge.py; the 'sheet' property says which",
                               "generated_utc": datetime.now(timezone.utc).isoformat(), "sources": sources, "features": feats}, indent=1))
    return len(feats), missing


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path, help="fim_georef.py run dirs (any order; the output keeps it)")
    ap.add_argument("-o", "--out-prefix", type=Path, required=True, help="output path prefix: <prefix>_<kind>_wgs84.geojson")
    ap.add_argument("--what", default="blocks,buildings,page,street_names", help=f"comma list of kinds to merge, from {KINDS} (default blocks,buildings,page,street_names)")
    args = ap.parse_args()
    kinds = [k.strip() for k in args.what.split(",") if k.strip()]
    bad = [k for k in kinds if k not in KINDS]
    if bad:
        raise SystemExit(f"unknown kind(s) {bad}; choose from {KINDS}")
    runs = [r for r in args.runs if r.is_dir()]
    for kind in kinds:
        out = args.out_prefix.parent / f"{args.out_prefix.name}_{kind}_wgs84.geojson"
        n, missing = merge(runs, kind, out)
        print(f"{kind}: {n} features from {len(runs) - len(missing)} sheets -> {out}" + (f"  (no {kind} in: {', '.join(missing)})" if missing else ""))


if __name__ == "__main__":
    main()
