#!/usr/bin/env python3
"""
Run the pipeline over many sheets of one book and merge the results: OCR -> blocks -> georeference per sheet, then a
second pass for the sheets that could not be placed, using the sheets around them, then one GeoJSON per kind.

    python3 scripts/fim_batch.py data/1895/p04.jpg data/1895/p05.jpg ... --crop 320,160,6880,7970 \\
        --streets data/modern/<city>_streets_epsg<code>.geojson --alias configs/georef/aliases_<city>_<year>.json \\
        --merge runs/hunyuan/<book>_p04-p10

Per sheet, pass 1:  fim_tile_ocr.py (--resume: finished tiles are reused, so re-running is cheap)
                    fim_blocks.py [fim_areas.py with --areas]
                    fim_georef.py --streets ... --alias ...
Pass 2, for sheets whose fit was refused (too few street labels) or produced no page footprint:
                    fim_georef.py --near <every sheet placed so far> --fuzzy --min-labels 4
                    and, if that still fails and --fallback-rotations is set, OCR again with rotated views (upright
                    tiles are reused) and fit once more the same way
--merge PREFIX:     fim_merge.py over the placed sheets -> PREFIX_blocks_wgs84.geojson, PREFIX_page_wgs84.geojson,
                    PREFIX_street_names_wgs84.geojson (+ areas with --areas; --merge-what to choose)

Nothing here is specific to a city or a book: the sheets, crop, prompt preset, street layer and alias file are all
arguments. Meant to run inside tmux; everything is printed, and a summary table closes the run. Sheets are processed in
the order given; a failure on one sheet never stops the others.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from fim_runlog import Stage, rel, streets_provenance  # noqa: E402


def run(cmd: list[str]) -> bool:
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=ROOT).returncode == 0


def stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def placed(run_dir: Path) -> bool:
    """A sheet counts as placed when its page footprint exists and is newer than the OCR (so not from an older fit)."""
    stem = run_dir.name
    tiles = next(run_dir.glob("*_tiles.json"), None)
    page = next(run_dir.glob("*_page_wgs84.geojson"), None)
    return bool(tiles and page and page.stat().st_mtime >= tiles.stat().st_mtime - 1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path, help="sheet scans, in book order")
    ap.add_argument("--streets", type=Path, required=True, help="modern street layer for fim_georef.py")
    ap.add_argument("--alias", type=Path, default=None, help="alias file for fim_georef.py")
    ap.add_argument("--crop", default=None, help="content box X0,Y0,X1,Y1 in scan px, same for every sheet (fim_tile_ocr.py --crop)")
    ap.add_argument("--tile", type=int, default=1024)
    ap.add_argument("--max-new-tokens", type=int, default=4096)
    ap.add_argument("--rotations", default="0", help="OCR views for pass 1 (default 0 = upright only)")
    ap.add_argument("--fallback-rotations", default="0,30,60", help="OCR views for a sheet that still cannot be placed after pass 2 ('' = never re-OCR)")
    ap.add_argument("--preset", default="text_coords", help="prompt preset in configs/prompts/")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "runs/hunyuan")
    ap.add_argument("--name", default="{date}_tiles_{stem}_t{tile}", help="run dir name pattern (fields: date, stem, tile)")
    ap.add_argument("--areas", action="store_true", help="also trace colour-wash areas (key plans)")
    ap.add_argument("--skip-ocr", action="store_true", help="do not call fim_tile_ocr.py at all (runs must already exist)")
    ap.add_argument("--min-labels-near", type=int, default=4, help="--min-labels for the pass-2 fit with --near (default 4)")
    ap.add_argument("--georef-arg", action="append", default=[], help="extra argument passed to every fim_georef.py call (repeatable; e.g. --georef-arg=--lots=none for a plan without lot numbers)")
    ap.add_argument("--blocks-arg", action="append", default=[], help="extra argument passed to every fim_blocks.py call (repeatable; e.g. --blocks-arg=--neck-px=8 for a plan with narrow streets)")
    ap.add_argument("--merge", type=Path, default=None, metavar="PREFIX", help="after the fits, merge the placed sheets' GeoJSON into PREFIX_<kind>_wgs84.geojson")
    ap.add_argument("--merge-what", default=None, help="kinds for --merge (default: blocks,outlines,page,street_names, plus areas with --areas)")
    ap.add_argument("--year", type=int, default=None, help="year of the plans, passed to fim_georef.py for the street-name log")
    args = ap.parse_args()

    today = date.today().isoformat()
    # run log (scripts/fim_runlog.py): one 'batch' event in the master with every sheet's outcome; the children's own
    # events (ocr, blocks, georef ...) carry this batch_id through the environment, so a book's run can be pulled together
    batch_id = f"{today}_{args.images[0].stem}-{args.images[-1].stem}_{uuid.uuid4().hex[:6]}"
    os.environ["FIM_BATCH_ID"] = batch_id
    with Stage(None, "batch", batch_id=batch_id, n_sheets=len(args.images), streets_file=rel(args.streets), streets=streets_provenance(args.streets),
               alias_file=rel(args.alias) if args.alias else None, crop=args.crop, tile=args.tile, rotations=args.rotations, fallback_rotations=args.fallback_rotations,
               preset=args.preset, year=args.year, min_labels_near=args.min_labels_near, georef_args=args.georef_arg, blocks_args=args.blocks_arg,
               merge_prefix=rel(args.merge) if args.merge else None, skip_ocr=args.skip_ocr, areas=args.areas) as log:
        run_book(args, today, log)


def run_book(args: argparse.Namespace, today: str, log: Stage) -> None:
    sheets = []
    for img in args.images:
        stem = img.stem
        sheets.append({"image": img, "stem": stem, "run": args.out_dir / args.name.format(date=today, stem=stem, tile=args.tile), "status": "pending"})
    t0 = time.time()

    def ocr(sh: dict, rotations: str) -> bool:
        if args.skip_ocr:
            return next(sh["run"].glob("*_tiles.json"), None) is not None
        cmd = [sys.executable, SCRIPTS / "fim_tile_ocr.py", sh["image"], "--tile", args.tile, "--rotations", rotations,
               "--max-new-tokens", args.max_new_tokens, "--preset", args.preset, "--resume", "-o", sh["run"]]
        if args.crop:
            cmd += ["--crop", args.crop]
        return run(cmd)

    def trace(sh: dict) -> bool:
        ok = run([sys.executable, SCRIPTS / "fim_blocks.py", sh["run"], *args.blocks_arg])
        if args.areas:
            ok = run([sys.executable, SCRIPTS / "fim_areas.py", sh["run"]]) and ok
        return ok

    def fit(sh: dict, near: list[Path] | None = None) -> bool:
        cmd = [sys.executable, SCRIPTS / "fim_georef.py", sh["run"], "--streets", args.streets]
        if args.alias:
            cmd += ["--alias", args.alias]
        if args.year:
            cmd += ["--year", args.year]
        if near:
            cmd += ["--near", *near, "--fuzzy", "--min-labels", args.min_labels_near]
        cmd += args.georef_arg
        return run(cmd) and placed(sh["run"])

    # pass 1
    for sh in sheets:
        print(f"\n################ {sh['stem']}  {stamp()}  -> {sh['run']}", flush=True)
        if not ocr(sh, args.rotations):
            sh["status"] = "OCR failed"; print(f"!!! {sh['stem']}: OCR failed", flush=True); continue
        if not trace(sh):
            print(f"--- {sh['stem']}: block tracing failed; fitting anyway", flush=True)
        sh["status"] = "placed" if fit(sh) else "not placed (pass 1)"
        print(f"### {sh['stem']}: {sh['status']}  ({(time.time() - t0) / 60:.0f} min so far)", flush=True)

    # pass 2: the sheets that could not be placed, helped by the ones that could. Only meaningful when the call named
    # several sheets of one book: with a single sheet there is no neighbour, and pass 2 is not attempted.
    weak = [s for s in sheets if s["status"] == "not placed (pass 1)"]
    if weak and len(sheets) < 2:
        print(f"\n--- {weak[0]['stem']}: not placed, and no other sheet was given to lean on (pass 2 needs several sheets of one book)", flush=True)
        weak[0]["status"] = "NOT PLACED"; weak = []
    for sh in weak:
        near = [s["run"] for s in sheets if s["status"] == "placed" and s is not sh]
        if not near:
            print(f"\n--- {sh['stem']}: no other sheet was placed, so nothing to lean on; skipping pass 2", flush=True)
            sh["status"] = "NOT PLACED"; continue
        print(f"\n################ {sh['stem']}  pass 2  {stamp()}  near {[n.name for n in near]}", flush=True)
        if fit(sh, near):
            sh["status"] = "placed (pass 2: --near --fuzzy)"
        elif args.fallback_rotations and not args.skip_ocr:
            print(f"--- {sh['stem']}: still not placed; OCR with views {args.fallback_rotations}", flush=True)
            if ocr(sh, args.fallback_rotations) and (trace(sh) or True) and fit(sh, near):
                sh["status"] = f"placed (pass 2: rotations {args.fallback_rotations}, --near --fuzzy)"
            else:
                sh["status"] = "NOT PLACED"
        else:
            sh["status"] = "NOT PLACED"
        print(f"### {sh['stem']}: {sh['status']}", flush=True)

    # summary
    print(f"\n################ summary  {stamp()}  total {(time.time() - t0) / 60:.0f} min", flush=True)
    log.note(sheets=[{"stem": sh["stem"], "run_dir": rel(sh["run"]), "status": sh["status"]} for sh in sheets],
             n_placed=sum(1 for sh in sheets if sh["status"].startswith("placed")), n_placed_pass1=sum(1 for sh in sheets if sh["status"] == "placed"),
             n_placed_pass2=sum(1 for sh in sheets if sh["status"].startswith("placed (pass 2")), n_not_placed=sum(1 for sh in sheets if sh["status"] == "NOT PLACED"),
             n_ocr_failed=sum(1 for sh in sheets if sh["status"] == "OCR failed"), total_min=round((time.time() - t0) / 60, 1))
    print(f"{'sheet':<8} {'status':<48} {'labels':>6} {'RMS m':>6} {'m/px':>7} {'rot deg':>8} {'transform':<10} alias candidates")
    for sh in sheets:
        g = next(sh["run"].glob("*_georef.json"), None) if sh["run"].exists() else None
        if g and sh["status"].startswith("placed"):
            d = json.loads(g.read_text())
            sug = ", ".join(f"{s['label']}->{s['modern']}" for s in (d.get("alias_suggestions") or [])[:4])
            print(f"{sh['stem']:<8} {sh['status']:<48} {d['n_labels']:>6} {d['rms_m']:>6.1f} {d['scale_m_per_px']['x']:>7.4f} {d['rotation_deg']:>8.2f} {d.get('transform', '?'):<10} {sug}")
        else:
            print(f"{sh['stem']:<8} {sh['status']:<48}")
    if args.merge:
        good = [sh["run"] for sh in sheets if sh["status"].startswith("placed")]
        what = args.merge_what or ("blocks,outlines,page,street_names,areas" if args.areas else "blocks,outlines,page,street_names")
        if good:
            run([sys.executable, SCRIPTS / "fim_merge.py", *good, "-o", args.merge, "--what", what])
        else:
            print("nothing to merge: no sheet was placed")
    run([sys.executable, SCRIPTS / "fim_run_history.py"])


if __name__ == "__main__":
    main()
