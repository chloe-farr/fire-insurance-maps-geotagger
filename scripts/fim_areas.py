#!/usr/bin/env python3
"""
Colour-wash areas from a sheet: regions identified by a colour fill rather than an outline (a key plan's per-sheet
tints; on detailed sheets, the material colours). Companion to fim_blocks.py, same output schema, so fim_georef.py and
fim_viewer.py take the result directly.

  1. estimate the paper colour (median Lab of bright, low-chroma pixels); smooth the image so faint washes survive
  2. wash = bright pixels whose chroma distance from the paper exceeds --min-chroma (Lab units)
  3. tints: the direction of each wash pixel's colour from the paper (angle in the Lab a/b plane) is histogrammed; each
     peak is one tint (pink, yellow, pale blue... named from the angle for readability only). No fixed hue ranges: a
     "blue" wash on cream paper is merely less yellow than the paper and has almost no HSV saturation.
  4. per tint: close gaps of --merge-px (street lines drawn across a tinted area) so an area is one polygon, fill holes,
     trace; drop small components, and components that hold no numerals and either touch the content border or are thin
     (page stains, the water tint along shorelines)
  5. numerals inside from the tile run's tokens: the tallest one, if clearly taller than the rest, is the area's number
     (on a key plan, the sheet number); alphabetic tokens within --street-reach px are recorded as nearby text

Output <run>/<stem>_areas_px.geojson (source-scan pixels, NOT a map — fim_georef.py places it), _areas.csv,
_areas_overlay.jpg.

    python3 scripts/fim_areas.py runs/hunyuan/<run>
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

DRAW = {"pink": (170, 120, 230), "yellow": (60, 200, 230), "green": (90, 190, 90), "blue": (230, 160, 70), "purple": (200, 90, 200), "other": (128, 128, 128)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="fim_tile_ocr.py output dir (needs <stem>_tiles.json for the source image, crop and tokens)")
    ap.add_argument("--work-scale", type=float, default=0.25, help="analysis resolution relative to the scan (default 0.25)")
    ap.add_argument("--min-chroma", type=float, default=3.5, help="paper-vs-wash chroma threshold in Lab units after smoothing (default 3; pale tints are ~3-4, strong ones 7-10)")
    ap.add_argument("--blur", type=int, default=15, help="Gaussian smoothing kernel in work px before thresholding (default 9)")
    ap.add_argument("--merge-px", type=int, default=12, help="close gaps up to this many work px within one tint so blocks of one tinted area separated by street lines become one polygon (default 25 ~ a street on a key plan)")
    ap.add_argument("--tint-sep", type=float, default=25.0, help="minimum angular separation (degrees, Lab a/b plane) between two tints (default 25)")
    ap.add_argument("--tint-width", type=float, default=40.0, help="a wash pixel joins a tint only if its colour direction is within this many degrees of it (default 40)")
    ap.add_argument("--max-tints", type=int, default=4, help="most tints to look for (default 4)")
    ap.add_argument("--min-area", type=float, default=0.0008, help="min component area as a fraction of the content box (default 0.0008)")
    ap.add_argument("--dark", type=int, default=110, help="gray level below which a pixel is ink (default 110)")
    ap.add_argument("--big-ratio", type=float, default=1.9, help="an upright numeral at least this many times the median numeral height is an area number (a key plan's sheet numerals are 2-2.5x its block numbers); an area holding two is split between them (default 1.9)")
    ap.add_argument("--street-reach", type=float, default=60.0, help="work px from the area edge within which alphabetic tokens are recorded as nearby text (default 60)")
    args = ap.parse_args()

    run = args.run
    tiles_path = next(run.glob("*_tiles.json"))
    stem = tiles_path.name[: -len("_tiles.json")]
    doc = json.loads(tiles_path.read_text())
    img = cv2.imread(doc["source_image"])
    if img is None:
        raise SystemExit(f"cannot read {doc['source_image']}")
    crop = doc.get("crop_source_px")
    x0, y0, x1, y1 = (int(v) for v in crop.split(",")) if crop else (0, 0, img.shape[1], img.shape[0])
    k = args.work_scale
    work = cv2.resize(img[y0:y1, x0:x1], None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    H, W = work.shape[:2]

    # 1. paper colour, smoothed Lab
    lab0 = cv2.cvtColor(work, cv2.COLOR_BGR2LAB).astype(np.float32)
    L0 = lab0[..., 0]
    bright0 = L0 > 150
    ca0 = np.sqrt((lab0[..., 1] - np.median(lab0[..., 1][bright0])) ** 2 + (lab0[..., 2] - np.median(lab0[..., 2][bright0])) ** 2)
    paper = np.median(lab0[bright0 & (ca0 < 6)].reshape(-1, 3), axis=0)
    lab = cv2.GaussianBlur(lab0, (args.blur, args.blur), 0) if args.blur > 1 else lab0
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    da, db = a - paper[1], b - paper[2]
    chroma = np.sqrt(da**2 + db**2)
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    T = args.min_chroma
    wash = (L > 140) & (chroma > T)

    # 2./3. tints = clusters of the strong-wash pixels' colour offset from the paper (k-means in the Lab a/b plane; k chosen
    # by the silhouette of a subsample). Weak-wash pixels then join the nearest tint if their colour direction agrees.
    strong = (L > 140) & (chroma > max(5.0, 1.6 * T))
    pts = np.stack([da[strong], db[strong]], 1).astype(np.float32)
    rng = np.random.default_rng(0)
    sub = pts[rng.choice(len(pts), min(len(pts), 20000), replace=False)]
    best_k, best_score, best_centres = 1, -1.0, np.array([[pts[:, 0].mean(), pts[:, 1].mean()]], np.float32)
    for kk in range(2, args.max_tints + 1):
        _, lbl, cen = cv2.kmeans(sub, kk, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.1), 5, cv2.KMEANS_PP_CENTERS)
        lbl = lbl.ravel()
        if min(np.bincount(lbl, minlength=kk)) < 0.03 * len(sub):
            continue
        # silhouette on a small subsample
        idx = rng.choice(len(sub), min(len(sub), 1500), replace=False)
        X, y = sub[idx], lbl[idx]
        D = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
        sil = []
        for i in range(len(X)):
            same = y == y[i]
            a_ = D[i][same & (np.arange(len(X)) != i)].mean() if same.sum() > 1 else 0
            b_ = min(D[i][y == c].mean() for c in range(kk) if c != y[i] and (y == c).any())
            sil.append((b_ - a_) / max(a_, b_, 1e-9))
        score = float(np.mean(sil))
        # tints must also be angularly distinct
        angs = np.degrees(np.arctan2(cen[:, 1], cen[:, 0]))
        sep = min(min(abs(angs[i] - angs[j]), 360 - abs(angs[i] - angs[j])) for i in range(kk) for j in range(i + 1, kk))
        if score > best_score and sep >= args.tint_sep:
            best_k, best_score, best_centres = kk, score, cen
    centres = best_centres
    peak_deg = [int(round((math.degrees(math.atan2(c[1], c[0])) + 360) % 360)) for c in centres]

    def tint_name(deg: float) -> str:  # readability only; the clustering itself is data-driven
        if deg <= 35 or deg >= 325: return "pink"          # +a
        if 35 < deg <= 130: return "yellow"                 # +b
        if 130 < deg <= 200: return "green"                 # -a, +b
        if 200 < deg <= 300: return "blue"                  # -b (less yellow than the paper)
        return "purple"
    names = [tint_name(d) for d in peak_deg]
    for n_ in set(names):
        idx = [i for i, x in enumerate(names) if x == n_]
        if len(idx) > 1:
            for j, i in enumerate(idx):
                names[i] = f"{n_}{j + 1}"
    share = np.bincount(np.linalg.norm(pts[:, None, :] - centres[None], axis=2).argmin(1), minlength=len(centres)) / len(pts)
    print(f"{stem}: work {W}x{H} @ {k}; paper Lab {paper.round(1).tolist()}; chroma > {T}; {len(centres)} tints (silhouette {best_score:.2f}): " + ", ".join(f"{n} @ {d} deg, offset a{c[0]:+.1f} b{c[1]:+.1f} ({sh:.0%} of strong wash)" for n, d, c, sh in zip(names, peak_deg, centres, share)))
    ang = (np.degrees(np.arctan2(db, da)) + 360) % 360
    diffs = np.stack([np.minimum(np.abs(ang - d), 360 - np.abs(ang - d)) for d in peak_deg])  # (k,H,W)
    tint_of = diffs.argmin(0)
    wash = wash & (diffs.min(0) <= args.tint_width)  # a weak-wash pixel must point roughly at one of the tints

    # 4. per tint: merge across street lines, fill, trace
    tokens = [t for t in doc["tokens"] if t.get("dup_of") is None and not t.get("fragment") and not t.get("conflict")]
    num_tok = [t for t in tokens if re.fullmatch(r"\d{1,3}[½¼¾]?", t["text"])]
    alpha_tok = [t for t in tokens if re.search(r"[A-Za-z]{3,}", t["text"])]

    def text_height(t) -> float:
        """True text height in source px: a word read in a rotated view has an inflated axis-aligned box, so use its polygon."""
        poly = t.get("polygon_source") or t.get("polygon")
        if poly and len(poly) >= 4:
            P_ = np.array(poly, float)
            if "polygon_source" not in t and doc.get("work_scale"):
                P_ = P_ / doc["work_scale"]
            e = [np.linalg.norm(P_[(i + 1) % 4] - P_[i]) for i in range(4)]
            return float(min(e[0], e[1]))
        bx1, by1, bx2, by2 = t["bbox_xyxy_source"]
        return float(by2 - by1)

    def to_work(bbox):  # source px -> work px
        bx1, by1, bx2, by2 = bbox
        return ((bx1 + bx2) / 2 - x0) * k, ((by1 + by2) / 2 - y0) * k, (by2 - by1) * k

    # big numerals (a key plan's sheet numbers): at least --big-ratio x the median numeral height. Only upright reads are
    # used when the run had rotated views: a numeral read in a rotated view carries an inflated box and is often a misread.
    heights = np.array([text_height(t) for t in num_tok]) if num_tok else np.array([40.0])
    med_h = float(np.median(heights))
    upright = [t for t in num_tok if not t.get("rotation")]
    pool = upright if (upright and any(t.get("rotation") for t in num_tok)) else num_tok
    big_tok = [t for t in pool if text_height(t) >= args.big_ratio * med_h]
    print(f"numerals: {len(num_tok)} ({len(upright)} upright), median text height {med_h:.0f} px; {len(big_tok)} big (>= {args.big_ratio} x, upright): {sorted(t['text'] for t in big_tok)}")

    min_area = args.min_area * W * H
    features, rows = [], []
    overlay = work.copy()
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV).astype(np.float32)
    dropped = {"small": 0, "border_no_numerals": 0, "thin_no_numerals": 0}
    for ti, (tname, tdeg) in enumerate(zip(names, peak_deg)):
        m = ((wash) & (tint_of == ti)).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        if args.merge_px > 0:
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * args.merge_px + 1,) * 2))
        n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] < min_area:
                dropped["small"] += 1
                continue
            comp_all = (labels == i)
            # big numerals inside this component -> one part per numeral (nearest-numeral partition of the component)
            bigs_in = []
            for t in big_tok:
                tx, ty, _ = to_work(t["bbox_xyxy_source"])
                if 0 <= int(ty) < H and 0 <= int(tx) < W and comp_all[int(ty), int(tx)]:
                    bigs_in.append((t["text"], tx, ty))
            parts = []
            if len(bigs_in) >= 2:
                ys, xs = np.nonzero(comp_all)
                d = np.stack([(xs - bx_) ** 2 + (ys - by_) ** 2 for _, bx_, by_ in bigs_in])
                owner = d.argmin(0)
                for j, (txt, _, _) in enumerate(bigs_in):
                    pm = np.zeros((H, W), np.uint8); pm[ys[owner == j], xs[owner == j]] = 255
                    parts.append((pm, txt))
            else:
                parts.append((comp_all.astype(np.uint8) * 255, bigs_in[0][0] if bigs_in else None))
            for comp, big_number in parts:
                cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not cnts:
                    continue
                c = max(cnts, key=cv2.contourArea)
                c = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2).astype(float)
                if len(c) < 4 or cv2.contourArea(c.astype(np.float32)) < min_area:
                    continue
                self_area = {"comp": comp}
                cnt32 = c.astype(np.float32).reshape(-1, 1, 2)
                area_work = float(cv2.contourArea(cnt32))
                compact = 4 * math.pi * area_work / max(cv2.arcLength(cnt32, True) ** 2, 1e-9)
                bx, by, bw, bh = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
                touches = bx <= 2 or by <= 2 or bx + bw >= W - 2 or by + bh >= H - 2
                inside = []
                for t in num_tok:
                    tx, ty, _ = to_work(t["bbox_xyxy_source"])
                    if cv2.pointPolygonTest(cnt32, (tx, ty), False) > 0:
                        inside.append((text_height(t), t["text"]))
                if not inside and touches:
                    dropped["border_no_numerals"] += 1
                    continue
                if not inside and compact < 0.25:
                    dropped["thin_no_numerals"] += 1
                    continue
                inside.sort()
                number = big_number  # the big numeral inside, when there is one; else none (block numbers are not area numbers)
                others = [txt for h, txt in inside if txt != number]
                near = []
                for t in alpha_tok:
                    tx, ty, _ = to_work(t["bbox_xyxy_source"])
                    d = -cv2.pointPolygonTest(cnt32, (tx, ty), True)
                    if d <= args.street_reach:
                        near.append({"name": t["text"], "distance_px": round(d / k), "label_bbox_source": t["bbox_xyxy_source"], "rotation_view": t.get("rotation", 0)})
                sel = comp > 0
                ring_src = [[round(px / k + x0), round(py / k + y0)] for px, py in c]
                ring_src.append(ring_src[0])
                cen = c.mean(0)
                props = {"sheet": stem, "kind": "wash_area", "colour": tname, "lab_angle_deg": tdeg, "median_lab": [round(float(np.median(lab0[..., j][sel]))) for j in range(3)],
                         "block_number": number, "block_number_inferred": False, "number_is_big_numeral": number is not None, "lot_numbers": others, "numbers_inside": others, "streets": near,
                         "street_names": sorted({x["name"] for x in near}), "area_source_px2": int(area_work / (k * k)), "compactness": round(compact, 3),
                         "touches_content_border": bool(touches), "centroid_source_px": [round(cen[0] / k + x0), round(cen[1] / k + y0)]}
                features.append({"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": [ring_src]}})
                props["split_by_numerals"] = len(bigs_in) >= 2
                rows.append([number or "", tname, tdeg, props["area_source_px2"], round(compact, 3), len(others), " ".join(props["street_names"])])
                col = DRAW.get(re.sub(r"\d+$", "", tname), DRAW["other"])
                cv2.polylines(overlay, [c.astype(np.int32)], True, col, 3)
                cv2.putText(overlay, f"{number or '?'} {tname}", (int(cen[0]) - 20, int(cen[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(overlay, f"{number or '?'} {tname}", (int(cen[0]) - 20, int(cen[1])), cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2, cv2.LINE_AA)
    print(f"dropped: {dropped}")

    fc = {"type": "FeatureCollection", "crs_note": "Coordinates are pixels on the source scan (origin top-left, y down). Not a map: fim_georef.py places it.",
          "source_image": doc["source_image"], "source_size": doc["source_size"], "from_run": str(run), "params": vars(args) | {"run": str(run)},
          "paper_lab": paper.round(1).tolist(), "chroma_threshold": T, "tints": [{"name": n, "lab_angle_deg": d, "offset_ab": [float(c[0]), float(c[1])]} for n, d, c in zip(names, peak_deg, centres)], "generated_utc": datetime.now(timezone.utc).isoformat(), "features": features}
    (run / f"{stem}_areas_px.geojson").write_text(json.dumps(fc, indent=1, default=float))
    with open(run / f"{stem}_areas.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["number", "colour", "lab_angle_deg", "area_source_px2", "compactness", "numerals_inside", "nearby_text"])
        w.writerows(rows)
    cv2.imwrite(str(run / f"{stem}_areas_overlay.jpg"), overlay, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"{len(features)} wash areas -> {run}/{stem}_areas_px.geojson (scan pixels), _areas.csv, _areas_overlay.jpg")
    for r in sorted(rows, key=lambda r: -r[3]):
        print(f"  {str(r[0]) or '?':>4s} {r[1]:8s} area {r[3]:>9d} compact {r[4]:.2f} numerals {r[5]:3d}  {r[6][:70]}")


if __name__ == "__main__":
    main()
