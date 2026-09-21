#!/usr/bin/env python3
"""
Build a self-contained interactive HTML viewer of georeferenced sheets: blocks over the modern centrelines, every OCR'd
word, the page footprint, per-label residuals, a block table — one tab per sheet. Pure SVG + vanilla JS, no basemap,
no network: the modern centrelines each sheet was fitted to are drawn from the layer recorded in its <stem>_georef.json.

    python3 scripts/fim_viewer.py runs/hunyuan/<run1> runs/hunyuan/<run2> ... -o runs/viewer.html [--title "..."]

Each run dir needs the fim_georef.py outputs (<stem>_georef.json, _blocks_epsg<code>.geojson, _blocks_rejected_*,
_page_epsg<code>.geojson, _tokens_wgs84.geojson). All sheets must share one projected CRS (the layer's EPSG).
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = PROJECT_ROOT / "configs/viewer/template.html"


def canon_name(props: dict, name_field: str, type_field: str | None) -> str:
    n = (props.get(name_field) or "").strip()
    t = (props.get(type_field) or "").strip() if type_field else ""
    return (n + " " + t).strip().upper()


def load_sheet(run: Path, streets_cache: dict) -> tuple[str, dict]:
    gj = next(run.glob("*_georef.json"))
    stem = gj.name[: -len("_georef.json")]
    g = json.loads(gj.read_text())
    epsg = g["epsg"]
    blocks = json.loads((run / f"{stem}_blocks_epsg{epsg}.geojson").read_text())["features"]
    rej_p = run / f"{stem}_blocks_rejected_epsg{epsg}.geojson"
    rej = json.loads(rej_p.read_text())["features"] if rej_p.exists() else []
    page = json.loads((run / f"{stem}_page_epsg{epsg}.geojson").read_text())["features"]
    toks = json.loads((run / f"{stem}_tokens_wgs84.geojson").read_text())["features"]
    content = [f for f in page if f["properties"]["what"] == "content"][0]["geometry"]["coordinates"][0]
    C = np.array(content)
    lo, hi = C.min(0) - 80, C.max(0) + 80

    sp = Path(g["streets"])
    if sp not in streets_cache:
        sj = json.loads(sp.read_text())
        nf, tf = g["streets_fields"]["name_field"], g["streets_fields"].get("type_field")
        streets_cache[sp] = [(canon_name(f["properties"], nf, tf), np.array(f["geometry"]["coordinates"], float)[:, :2]) for f in sj["features"] if f.get("geometry") and f["geometry"]["type"] == "LineString"]
    segs, longest = [], {}
    for nm, c in streets_cache[sp]:
        if not nm:
            continue
        for a, b in zip(c[:-1], c[1:]):
            if max(a[0], b[0]) < lo[0] or min(a[0], b[0]) > hi[0] or max(a[1], b[1]) < lo[1] or min(a[1], b[1]) > hi[1]:
                continue
            segs.append([round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1)])
            L = math.hypot(*(b - a))
            inside = all(lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1] for p in (a, b))
            score = L * (2 if inside else 1)
            if score > longest.get(nm, (0,))[0]:
                longest[nm] = (score, [round((a[0] + b[0]) / 2, 1), round((a[1] + b[1]) / 2, 1)], round(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), 1))
    W = hi[0] - lo[0]
    labels = [{"n": n, "p": v[1], "a": v[2]} for n, v in longest.items() if v[0] > W / 12]

    def ring(f):
        return [[round(x, 1), round(y, 1)] for x, y in f["geometry"]["coordinates"][0]]

    B = []
    for f in blocks:
        p = f["properties"]
        B.append({"ring": ring(f), "num": p.get("block_number"), "inf": bool(p.get("block_number_inferred")), "lots": p.get("lot_numbers") or [],
                  "s1895": sorted({r["label_1895"] for r in p.get("streets_1895", [])}), "smod": [d["name"] + " (" + d["side"] + ")" for d in p.get("streets_modern", [])],
                  "other": p.get("nearby_text", []), "split": p.get("split_from"), "merged": p.get("merged_across")})
    RJ = [{"ring": ring(f), "why": f["properties"].get("rejected_because", ""), "num": f["properties"].get("block_number")} for f in rej]
    areas_p = run / f"{stem}_areas_epsg{epsg}.geojson"
    AR = []
    if areas_p.exists():
        for f in json.loads(areas_p.read_text())["features"]:
            p = f["properties"]
            AR.append({"ring": ring(f), "num": p.get("block_number"), "colour": re.sub(r"\d+$", "", p.get("colour", "other")), "n_num": len(p.get("numbers_inside") or []),
                       "s1895": p.get("street_names", []), "lab": p.get("median_lab")})
    A = g["affine_source_px_to_map"]
    M = np.array([[A["a11"], A["a12"], A["tx"]], [A["a21"], A["a22"], A["ty"]]])
    T = []
    for f in toks:
        x1, y1, x2, y2 = f["properties"]["bbox_source_px"]
        m = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], float) @ M[:, :2].T + M[:, 2]
        T.append({"t": f["properties"]["text"], "r": [[round(a, 1), round(b, 1)] for a, b in m]})
    sc = g["scale_m_per_px"]["x"]
    stated = g.get("stated_scale_ft_per_inch")
    dpi = g.get("implied_dpi_from_stated_scale")
    sheet_no = re.sub(r"^p0*", "", stem)
    return stem, {
        "title": f"Sheet {sheet_no}", "scale": (f"{stated} ft = 1 in" if stated else f"{sc:.3f} m/px"),
        "bbox": [round(v, 1) for v in (*lo, *hi)], "content": [[round(x, 1), round(y, 1)] for x, y in content],
        "fit": {"rms": round(g["rms_m"], 1), "n": g["n_labels"], "out": g["n_outliers"], "rot": round(g["rotation_deg"], 1), "scale": round(sc, 4),
                "dpi": (round(dpi) if dpi else None), "layer": Path(g["streets"]).name,
                "labels": [{"t": l["text"], "m": l["modern"][0] if l["modern"] else "", "r": l["residual_m"], "o": l.get("outlier", False)} for l in g["labels"]]},
        "segs": segs, "slabels": labels, "blocks": B, "rejected": RJ, "areas": AR, "tokens": T, "epsg": epsg,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=PROJECT_ROOT / "runs/viewer.html")
    ap.add_argument("--title", default="Georeferenced sheets")
    ap.add_argument("--subtitle", default="Fire insurance plan blocks placed by their own OCR'd street names onto modern street centrelines")
    ap.add_argument("--default", default=None, help="stem of the sheet to open first (default: the last run given)")
    args = ap.parse_args()
    cache: dict = {}
    sheets = {}
    for r in args.runs:
        stem, d = load_sheet(r, cache)
        sheets[stem] = d
        print(f"{stem}: {len(d['segs'])} centreline segments, {len(d['blocks'])} blocks, {len(d['rejected'])} rejected, {len(d['areas'])} tinted areas, {len(d['tokens'])} tokens")
    epsgs = {d["epsg"] for d in sheets.values()}
    if len(epsgs) > 1:
        raise SystemExit(f"sheets use different CRSs {epsgs}; refit them against layers in one CRS")
    html = TEMPLATE.read_text()
    html = html.replace("__TITLE__", args.title).replace("__SUBTITLE__", args.subtitle).replace("__EPSG__", str(epsgs.pop()))
    html = html.replace("__DEFAULT__", json.dumps(args.default or list(sheets)[-1]))
    html = html.replace("__DATA__", json.dumps(sheets, separators=(",", ":")).replace("</", "<\\/"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html)
    print(f"-> {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
