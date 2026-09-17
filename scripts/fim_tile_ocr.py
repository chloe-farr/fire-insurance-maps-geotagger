#!/usr/bin/env python3
"""
Tile a full fire insurance sheet, HunyuanOCR each tile, and stitch the word boxes back into
sheet pixel coordinates.

Why: whole sheets fed at <=1536 px either collapse (a few bytes back) or hit the 16k-token cap
with the lower half unread (see docs/run_history.md). A tile sees far less text at far higher
resolution, so it finishes well inside the cap.

Pipeline
  1. load sheet, downscale so the longest edge is --work-max-edge (default 4096; 0 = native)
  2. overlapping tile grid (--tile, --overlap); tiles that are almost pure background are skipped (--min-ink)
  3. per tile: save PNG, HunyuanOCR with --preset/--prompt, save *_content.txt + *_metadata.json
     (same schema as fim_hunyuan.py so scripts/fim_overlay.sh works on any single tile)
  4. parse word(x1,y1),(x2,y2) (0-1000 on the tile) -> tile px -> sheet px (work image and source image);
     a word repeated 5+ times in a row (the model looping after hitting the cap) is kept once
  5. dedupe tokens that two tiles both read in the overlap band (same text, IoU > --dedupe-iou)
  6. write <stem>_tiles.json (plan, per-tile stats, all tokens), <stem>_tokens.csv, <stem>_tile_overlay.jpg

    python3 scripts/fim_tile_ocr.py data/1895/p06b.jpg --dry-run           # plan + tile PNGs + grid overlay, no model
    python3 scripts/fim_tile_ocr.py data/1895/p06b.jpg --tiles 1,1 1,2     # a couple of tiles to sanity-check
    python3 scripts/fim_tile_ocr.py data/1895/p06b.jpg                     # whole sheet (--resume skips finished tiles)

Needs a Python with transformers>=5.13 (see README, Setup); re-execs into .venv or $HUNYUAN_PY if this one lacks it.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None  # 7800x8400 scans trip the decompression-bomb guard

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "configs" / "prompts"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hunyuan_compat import ensure_hunyuan_python as _ensure_hunyuan_python, extract_elements, hunyuan_infer_one, load_pil  # noqa: E402

DEFAULT_MODEL = "tencent/HunyuanOCR"

# --------------------------------------------------------------------------- tiling
def tile_starts(length: int, tile: int, min_overlap: int) -> list[int]:
    """Start offsets so that [start, start+tile) tiles cover [0, length) with at least `min_overlap` px shared
    between neighbours. Uses the fewest tiles that allow that, then spreads them evenly, so every neighbour pair
    shares the same overlap (instead of one fat overlap where the last tile is pushed flush to the edge)."""
    if length <= tile:
        return [0]
    n = math.ceil((length - min_overlap) / (tile - min_overlap))
    stride = (length - tile) / (n - 1)
    return [round(i * stride) for i in range(n)]


def plan_tiles(w: int, h: int, tile: int, overlap: int) -> list[dict[str, int]]:
    plan = []
    for r, y0 in enumerate(tile_starts(h, tile, overlap)):
        for c, x0 in enumerate(tile_starts(w, tile, overlap)):
            plan.append({"r": r, "c": c, "x0": x0, "y0": y0, "x1": min(x0 + tile, w), "y1": min(y0 + tile, h)})
    return plan


def ink_fraction(tile_img: Image.Image, dark_below: int = 160) -> float:
    """Share of pixels darker than `dark_below` (0-255 gray). Linework/text on these sheets is near-black;
    the cream paper and pink/yellow building fills are not, so this separates content tiles from margins."""
    g = tile_img.convert("L")
    if max(g.size) > 512:  # cheap estimate is enough
        g = g.resize((max(1, g.width // 4), max(1, g.height // 4)))
    hist = g.histogram()
    dark = sum(hist[:dark_below])
    return dark / (g.width * g.height)


# --------------------------------------------------------------------------- rotated views
def rotated_view(work: Image.Image, t: dict[str, int], angle: int) -> tuple[Image.Image, dict[str, Any]]:
    """The tile's footprint rotated by `angle` (CCW) about its centre, same scale and size. Built from a √2
    square around the tile so the corners are neighbouring map rather than white fill. Returns the view and the
    geometry needed to map its coordinates back (see view_to_work)."""
    side = max(t["x1"] - t["x0"], t["y1"] - t["y0"])
    S = math.ceil(side * math.sqrt(2)) + 2
    cx, cy = (t["x0"] + t["x1"]) / 2.0, (t["y0"] + t["y1"]) / 2.0
    sx0, sy0 = round(cx - S / 2), round(cy - S / 2)
    square = Image.new("RGB", (S, S), (255, 255, 255))
    # PIL pads out-of-bounds crops with black; paste only the in-bounds part so sheet edges stay white
    ix0, iy0 = max(sx0, 0), max(sy0, 0)
    ix1, iy1 = min(sx0 + S, work.width), min(sy0 + S, work.height)
    if ix1 > ix0 and iy1 > iy0:
        square.paste(work.crop((ix0, iy0, ix1, iy1)), (ix0 - sx0, iy0 - sy0))
    rot = square.rotate(angle, expand=False, fillcolor=(255, 255, 255), resample=Image.Resampling.BICUBIC)
    off = (S - side) // 2
    return rot.crop((off, off, off + side, off + side)), {"angle": angle, "S": S, "sx0": sx0, "sy0": sy0, "off": off, "side": side}


def view_to_work(x: float, y: float, g: dict[str, Any]) -> tuple[float, float]:
    """Inverse of rotated_view for one point: view px -> work-image px. PIL rotates CCW on screen, which in
    y-down coordinates is x' = x cos + y sin, y' = -x sin + y cos about the centre; invert that."""
    th = math.radians(g["angle"])
    c = g["S"] / 2.0
    dx, dy = (x + g["off"]) - c, (y + g["off"]) - c
    return c + dx * math.cos(th) - dy * math.sin(th) + g["sx0"], c + dx * math.sin(th) + dy * math.cos(th) + g["sy0"]


# --------------------------------------------------------------------------- tokens
def parse_tile_tokens(content: str, t: dict[str, int], work_scale: float, geom: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """0-1000 tile coords -> work-image px -> source px."""
    coords, texts = extract_elements(content, 1.0, 1.0)
    tw, th = t["x1"] - t["x0"], t["y1"] - t["y0"]
    out = []
    for (x1, y1, x2, y2), text in zip(coords, texts):
        text = text.strip()
        if not text:
            continue
        clip = lambda v: min(1000, max(0, v))  # noqa: E731 — model occasionally emits >1000 while spamming
        x1, y1, x2, y2 = clip(x1), clip(y1), clip(x2), clip(y2)
        poly = None
        if geom is None or geom["angle"] % 360 == 0:
            wx1 = t["x0"] + x1 / 1000.0 * tw
            wy1 = t["y0"] + y1 / 1000.0 * th
            wx2 = t["x0"] + x2 / 1000.0 * tw
            wy2 = t["y0"] + y2 / 1000.0 * th
        else:
            # the box is axis-aligned in the rotated view; map its 4 corners back and take their extent
            vs = geom["side"]
            corners = [(x1 / 1000.0 * vs, y1 / 1000.0 * vs), (x2 / 1000.0 * vs, y1 / 1000.0 * vs),
                       (x2 / 1000.0 * vs, y2 / 1000.0 * vs), (x1 / 1000.0 * vs, y2 / 1000.0 * vs)]
            poly = [view_to_work(px, py, geom) for px, py in corners]
            cxw = sum(q[0] for q in poly) / 4; cyw = sum(q[1] for q in poly) / 4
            if not (t["x0"] <= cxw <= t["x1"] and t["y0"] <= cyw <= t["y1"]):
                continue  # corner content belonging to a neighbouring tile's footprint; that tile reads it itself
            wx1, wx2 = min(q[0] for q in poly), max(q[0] for q in poly)
            wy1, wy2 = min(q[1] for q in poly), max(q[1] for q in poly)
        out.append({
            "text": text,
            "tile": f"r{t['r']}c{t['c']}" + (f"@{geom['angle']}" if geom and geom["angle"] % 360 else ""),
            "rotation": geom["angle"] % 360 if geom else 0,
            "polygon": [[round(q[0]), round(q[1])] for q in poly] if poly else None,
            "bbox_norm1000_tile": [x1, y1, x2, y2],
            "bbox_xyxy": [round(wx1), round(wy1), round(wx2), round(wy2)],
            "bbox_xyxy_source": [round(wx1 / work_scale), round(wy1 / work_scale), round(wx2 / work_scale), round(wy2 / work_scale)],
            "edge_margin_px": round(min(wx1 - t["x0"], wy1 - t["y0"], t["x1"] - wx2, t["y1"] - wy2)),
            "dup_of": None,
        })
    return out


def drop_runaway(toks: list[dict[str, Any]], min_run: int = 5) -> tuple[list[dict[str, Any]], int]:
    """Drop the tail of a repetition loop. When a tile hits the token cap the model often emits one word over and over,
    either at a fixed box ("BROAD(0,184),(47,197)" x 200) or marching along an edge ("M(696,0),(707,8)M(707,0),(718,8)...").
    A run of >= min_run consecutive tokens with identical text keeps only its first token. Returns (tokens, n dropped).
    Lot numbers repeat on a sheet too, but never back to back in reading order, so real text is not touched."""
    keep: list[dict[str, Any]] = []
    i, dropped = 0, 0
    while i < len(toks):
        j = i
        while j < len(toks) and toks[j]["text"] == toks[i]["text"]:
            j += 1
        if j - i >= min_run:
            keep.append(toks[i]); dropped += j - i - 1
        else:
            keep.extend(toks[i:j])
        i = j
    return keep, dropped


def iou(a: list[int], b: list[int]) -> float:
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area = lambda r: max(0, r[2] - r[0]) * max(0, r[3] - r[1])  # noqa: E731
    return inter / float(area(a) + area(b) - inter or 1)


def containment(inner: list[int], outer: list[int]) -> float:
    """Share of `inner`'s area that lies inside `outer`."""
    ix1, iy1, ix2, iy2 = max(inner[0], outer[0]), max(inner[1], outer[1]), min(inner[2], outer[2]), min(inner[3], outer[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    a = max(1, (inner[2] - inner[0]) * (inner[3] - inner[1]))
    return (ix2 - ix1) * (iy2 - iy1) / a


def _centre(tok: dict[str, Any]) -> tuple[float, float]:
    if tok.get("polygon"):
        return sum(q[0] for q in tok["polygon"]) / 4.0, sum(q[1] for q in tok["polygon"]) / 4.0
    b = tok["bbox_xyxy"]
    return (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0


def _short_side(tok: dict[str, Any]) -> float:
    if tok.get("polygon"):
        q = tok["polygon"]
        e1 = math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]); e2 = math.hypot(q[2][0] - q[1][0], q[2][1] - q[1][1])
        return max(4.0, min(e1, e2))
    b = tok["bbox_xyxy"]
    return max(4.0, min(b[2] - b[0], b[3] - b[1]))


def _same_place(a: dict[str, Any], b: dict[str, Any], iou_thresh: float) -> bool:
    """Same physical text? IoU of the axis boxes (fine for upright reads) OR centres closer than one text
    height (needed for rotated-view reads, whose axis box is the inflated extent of a tilted quad)."""
    if iou(a["bbox_xyxy"], b["bbox_xyxy"]) >= iou_thresh:
        return True
    (ax, ay), (bx, by) = _centre(a), _centre(b)
    return math.hypot(ax - bx, ay - by) <= 0.8 * max(_short_side(a), _short_side(b))


def _view_rank(tok: dict[str, Any]) -> tuple:
    """Preference when two reads compete: upright view first, then farther from a tile edge."""
    return (tok.get("rotation", 0) != 0, -tok["edge_margin_px"], tok["tile"])


def dedupe(tokens: list[dict[str, Any]], iou_thresh: float) -> tuple[int, int]:
    """Collapse multiple reads of the same physical text across tiles/views/passes.

    1. exact duplicates: same text, same place (see _same_place) -> keep the upright / most-interior copy, dup_of -> it
    2. edge fragments: a shorter token whose text is contained in a longer kept token and whose centre lies inside
       that token's box ("OHNSON" -> JOHNSON) -> fragment=True, dup_of -> the whole word
    3. conflicts: different text at the same place (IoU >= 0.5), e.g. a rotated view misreading cursive as "Vicona"
       -> keep the upright read (else the longer), conflict=True on the loser
    Returns (exact duplicates suppressed, fragments + conflicts suppressed)."""
    tokens.sort(key=_view_rank)
    kept: list[dict[str, Any]] = []
    n_dup = 0
    for tok in tokens:
        key = tok["text"].lower()
        match = next((k for k in kept if k["tile"] != tok["tile"] and k["text"].lower() == key and _same_place(k, tok, iou_thresh)), None)
        if match is None:
            tok["id"] = len(kept)
            kept.append(tok)
        else:
            tok["dup_of"] = match["id"]
            n_dup += 1
    n_frag = 0
    for tok in kept:
        key = tok["text"].lower(); cx, cy = _centre(tok)
        for k in kept:
            if k is tok or k["dup_of"] is not None or k["tile"] == tok["tile"]:
                continue
            b = k["bbox_xyxy"]
            if len(k["text"]) > len(key) and key in k["text"].lower() and b[0] - 4 <= cx <= b[2] + 4 and b[1] - 4 <= cy <= b[3] + 4:
                tok["dup_of"] = k["id"]; tok["fragment"] = True; n_frag += 1
                break
    for tok in kept:
        if tok["dup_of"] is not None:
            continue
        for k in kept:
            if k is tok or k["dup_of"] is not None or k["tile"] == tok["tile"] or k["text"].lower() == tok["text"].lower():
                continue
            if iou(k["bbox_xyxy"], tok["bbox_xyxy"]) >= 0.5 and _view_rank(k) < _view_rank(tok):
                tok["dup_of"] = k["id"]; tok["conflict"] = True; n_frag += 1
                break
    return n_dup, n_frag


# --------------------------------------------------------------------------- overlay
def _font(size: int) -> ImageFont.ImageFont:
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if Path(p).is_file():
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_overlay(work: Image.Image, plan: list[dict], tokens: list[dict], skipped: set[str], out: Path,
                 max_edge: int = 4096, labels: bool = True, crop_box: list[int] | None = None) -> None:
    scale = min(1.0, max_edge / max(work.size))
    img = work.copy() if scale == 1.0 else work.resize((round(work.width * scale), round(work.height * scale)), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(img, "RGBA")
    f = _font(max(10, round(14 * scale * (work.width / 4096))))
    s = lambda v: round(v * scale)  # noqa: E731
    if crop_box:
        d.rectangle([s(crop_box[0]), s(crop_box[1]), s(crop_box[2]) - 1, s(crop_box[3]) - 1], outline=(0, 170, 0, 230), width=4)
    for t in plan:
        tid = f"r{t['r']}c{t['c']}"
        col = (128, 128, 128, 200) if tid in skipped else (0, 90, 255, 220)
        d.rectangle([s(t["x0"]), s(t["y0"]), s(t["x1"]) - 1, s(t["y1"]) - 1], outline=col, width=3)
        d.text((s(t["x0"]) + 6, s(t["y0"]) + 4), tid + (" (skipped)" if tid in skipped else ""), fill=col, font=f)
    for tok in tokens:
        x1, y1, x2, y2 = (s(v) for v in tok["bbox_xyxy"])
        if tok["dup_of"] is not None:
            d.rectangle([x1, y1, x2, y2], outline=(160, 160, 160, 160), width=1)
            continue
        col = (220, 0, 0, 230) if ":" not in tok["tile"] else (200, 90, 0, 230)  # orange = kept from a merged pass
        if tok.get("rotation"):
            col = (140, 0, 200, 230)  # purple = read in a rotated view
        if tok.get("polygon"):
            d.polygon([(s(q[0]), s(q[1])) for q in tok["polygon"]], outline=col, width=2)
        else:
            d.rectangle([x1, y1, x2, y2], outline=col, width=2)
        if labels:
            d.text((x1, max(0, y1 - f.size - 1)), tok["text"], fill=(0, 120, 0, 255), font=f)
    img.convert("RGB").save(out, quality=88)


# --------------------------------------------------------------------------- main
def load_preset(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.is_file():
        sys.exit(f"error: no preset {name!r} in {PROMPTS_DIR}")
    return path.read_text(encoding="utf-8").strip()


def main() -> None:
    _ensure_hunyuan_python()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--output-dir", type=Path, default=None, help="Default: runs/hunyuan/<YYYY-MM-DD>_tiles_<stem>/")
    ap.add_argument("--crop", metavar="X0,Y0,X1,Y1", default=None,
                    help="Content box in SOURCE pixels; tiling and coordinates are relative to the full sheet, but only this box is tiled. "
                         "Use it to drop the scan margin, colour bar and ruler (e.g. 1895 sheets: 300,150,7000,7980).")
    ap.add_argument("--work-max-edge", type=int, default=4096, help="Downscale the sheet to this longest edge before tiling (0 = native). Default 4096.")
    ap.add_argument("--tile", type=int, default=1536, help="Tile size in work-image px (fed to the model unresized). Default 1536.")
    ap.add_argument("--overlap", type=int, default=192, help="Minimum tile overlap in work-image px (default 192, ~2 text heights at 4096); actual overlap is spread evenly.")
    ap.add_argument("--shift", metavar="DX,DY", default=None,
                    help="Shift the whole tile grid by DX,DY work px (clipped to the image). Use ~half a stride for a second pass "
                         "so words that sat on a tile edge in pass 1 are seen whole.")
    ap.add_argument("--merge", nargs="*", default=None, metavar="TILES_JSON",
                    help="Union the kept tokens of earlier passes (their <stem>_tiles.json) into this run before dedupe.")
    ap.add_argument("--rotations", default="0", metavar="DEG,DEG,...",
                    help="OCR each tile at these rotations (degrees, CCW) and union the results. HunyuanOCR reads text only when it is "
                         "within ~20-30 deg of horizontal/vertical (docs/run_history.md, rotation probe), so 0,30,60 covers every text "
                         "orientation. Rotated views are cut from a sqrt(2) square around the tile so corners show real map, not white.")
    ap.add_argument("--surya-lines", type=Path, default=None, metavar="LINES_JSON",
                    help="Output of fim_surya_detect.py for the same sheet: tag each token with the Surya line it falls in "
                         "(surya_line / surya_conf columns) as an independent geometric check. Tokens with none are worth a look.")
    ap.add_argument("--min-ink", type=float, default=0.004, help="Skip tiles whose dark-pixel fraction is below this (default 0.004). 0 = never skip.")
    ap.add_argument("--tiles", nargs="*", default=None, metavar="R,C", help="Only these tiles, e.g. --tiles 0,0 1,2")
    ap.add_argument("--max-tiles", type=int, default=None, help="Stop after N processed tiles (testing).")
    ap.add_argument("--dry-run", action="store_true", help="Plan, save tile PNGs and the grid overlay; no model.")
    ap.add_argument("--resume", action="store_true", help="Reuse tiles that already have *_content.txt in the output dir.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--preset", default="text_coords")
    g.add_argument("--prompt")
    ap.add_argument("--max-new-tokens", type=int, default=8192)
    ap.add_argument("--dedupe-iou", type=float, default=0.4)
    ap.add_argument("--no-labels", action="store_true", help="Overlay boxes only, no text labels.")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--revision", default=None, help="Hub revision (default: pinned pre-reformat commit, see _hunyuan_compat.py)")
    ap.add_argument("--attn", default="eager")
    args = ap.parse_args()

    src = args.image.expanduser().resolve()
    if not src.is_file():
        sys.exit(f"error: not found: {src}")
    stem = src.stem
    out_dir = args.output_dir or (PROJECT_ROOT / "runs" / "hunyuan" / f"{datetime.now():%Y-%m-%d}_tiles_{stem}")
    tiles_dir = out_dir / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)
    prompt = args.prompt.strip() if args.prompt else load_preset(args.preset)

    # 1. work image
    sheet = load_pil(src)
    sw, sh = sheet.size
    work_scale = 1.0
    if args.work_max_edge and max(sw, sh) > args.work_max_edge:
        work_scale = args.work_max_edge / max(sw, sh)
        work = sheet.resize((round(sw * work_scale), round(sh * work_scale)), Image.Resampling.LANCZOS)
    else:
        work = sheet
    ww, wh = work.size
    print(f"{src.name}: source {sw}x{sh} -> work {ww}x{wh} (scale {work_scale:.4f})", flush=True)

    # 2. plan (over the content box if --crop, offsets keep coordinates in full-sheet space)
    crop_box = None
    if args.crop:
        cx0, cy0, cx1, cy1 = (int(v) for v in args.crop.split(","))
        crop_box = [round(cx0 * work_scale), round(cy0 * work_scale), round(cx1 * work_scale), round(cy1 * work_scale)]
        bx0, by0 = crop_box[0], crop_box[1]
        plan = plan_tiles(crop_box[2] - bx0, crop_box[3] - by0, args.tile, args.overlap)
        for t in plan:
            t["x0"] += bx0; t["x1"] += bx0; t["y0"] += by0; t["y1"] += by0
        print(f"crop (source px) {args.crop} -> work px {crop_box}", flush=True)
    else:
        plan = plan_tiles(ww, wh, args.tile, args.overlap)
    shift = None
    if args.shift:
        # Re-plan over the content box minus the shift, so tile edges move but no tile leaves the box
        # (a plain translate would slide the last column/row into the colour bar or off the image).
        dx, dy = (int(v) for v in args.shift.split(","))
        shift = [dx, dy]
        bx0, by0, bx1, by1 = crop_box if crop_box else [0, 0, ww, wh]
        bx0, by0 = bx0 + dx, by0 + dy
        plan = plan_tiles(bx1 - bx0, by1 - by0, args.tile, args.overlap)
        for t in plan:
            t["x0"] += bx0; t["x1"] += bx0; t["y0"] += by0; t["y1"] += by0
        print(f"grid origin shifted by {shift} work px (tiles stay inside the content box)", flush=True)
    wanted = {tuple(int(v) for v in s.split(",")) for s in args.tiles} if args.tiles else None
    skipped: set[str] = set()
    tile_stats: dict[str, dict[str, Any]] = {}
    for t in plan:
        tid = f"r{t['r']}c{t['c']}"
        crop = work.crop((t["x0"], t["y0"], t["x1"], t["y1"]))
        ink = ink_fraction(crop)
        tile_stats[tid] = {**t, "ink_fraction": round(ink, 5), "png": f"tiles/{stem}_{tid}.png"}
        # Always re-cut: a stale PNG from a run with different --crop/--tile geometry would silently
        # shift every coordinate this tile contributes.
        crop.save(tiles_dir / f"{stem}_{tid}.png")
        if wanted is not None and (t["r"], t["c"]) not in wanted:
            skipped.add(tid); tile_stats[tid]["status"] = "not_selected"
        elif args.min_ink and ink < args.min_ink:
            skipped.add(tid); tile_stats[tid]["status"] = "skipped_blank"
        else:
            tile_stats[tid]["status"] = "pending"
    todo = [t for t in plan if f"r{t['r']}c{t['c']}" not in skipped]
    if args.max_tiles:
        for t in todo[args.max_tiles:]:
            tid = f"r{t['r']}c{t['c']}"; skipped.add(tid); tile_stats[tid]["status"] = "not_selected"
        todo = todo[: args.max_tiles]
    rows, cols = plan[-1]["r"] + 1, plan[-1]["c"] + 1
    print(f"grid {rows}x{cols} = {len(plan)} tiles of {args.tile}px, overlap {args.overlap}; "
          f"{len(todo)} to OCR, {sum(1 for v in tile_stats.values() if v['status']=='skipped_blank')} blank-skipped", flush=True)
    for tid, v in tile_stats.items():
        print(f"  {tid}: ({v['x0']},{v['y0']})-({v['x1']},{v['y1']}) ink={v['ink_fraction']:.4f} {v['status']}")

    tokens: list[dict[str, Any]] = []
    merged_from: list[str] = []
    if not args.dry_run and todo:
        # 3. model
        rotations = [int(a) % 360 for a in args.rotations.split(",")]
        need_model = [(t, a) for t in todo for a in rotations
                      if not (args.resume and (tiles_dir / f"{stem}_r{t['r']}c{t['c']}{'' if a == 0 else f'_rot{a:03d}'}_content.txt").exists())]
        model = processor = None
        if need_model:
            from _hunyuan_compat import DEFAULT_REVISION, load_hunyuan
            print(f"Loading {args.model} (attn={args.attn}) ...", flush=True)
            model, processor = load_hunyuan(args.model, args.attn, args.revision or DEFAULT_REVISION)
        jobs = [(t, a) for t in todo for a in rotations]
        for i, (t, a) in enumerate(jobs, 1):
            tid = f"r{t['r']}c{t['c']}"
            sfx = "" if a == 0 else f"_rot{a:03d}"
            png = tiles_dir / f"{stem}_{tid}{sfx}.png"
            content_path = tiles_dir / f"{stem}_{tid}{sfx}_content.txt"
            meta_path = tiles_dir / f"{stem}_{tid}{sfx}_metadata.json"
            geom = None
            if a != 0:
                view, geom = rotated_view(work, t, a)
                view.save(png)
            prior = json.loads(meta_path.read_text()) if (args.resume and meta_path.exists()) else None
            same_geom = prior is not None and all(prior.get("tile", {}).get(k) == t[k] for k in ("x0", "y0", "x1", "y1"))
            if same_geom and content_path.exists():
                content = content_path.read_text(encoding="utf-8")
                meta = prior
                print(f"[{i}/{len(jobs)}] {tid}{sfx}: resumed ({len(content)} chars)", flush=True)
            else:
                if model is None:  # --resume found a geometry mismatch after we decided no model was needed
                    from _hunyuan_compat import DEFAULT_REVISION, load_hunyuan
                    print(f"Loading {args.model} (attn={args.attn}) ...", flush=True)
                    model, processor = load_hunyuan(args.model, args.attn, args.revision or DEFAULT_REVISION)
                crop = Image.open(png).convert("RGB")
                content, m = hunyuan_infer_one(model=model, processor=processor, image_pil=crop, image_path=png,
                                               user_prompt=prompt, max_new_tokens=args.max_new_tokens)
                content_path.write_text(content, encoding="utf-8")
                meta = {
                    "processed_width": m["processed_width"], "processed_height": m["processed_height"],
                    "saved_width": crop.width, "saved_height": crop.height,
                    "scale_x": m["scale_x"], "scale_y": m["scale_y"],
                    "context_prompt": prompt, "model_name_or_path": args.model, "model_revision": args.revision or DEFAULT_REVISION,
                    "input_tokens": m["input_tokens"], "output_tokens": m["output_tokens"], "total_tokens": m["total_tokens"],
                    "tile": {**t, "id": tid}, "rotation_deg": a, "source_image": str(src), "work_scale": work_scale,
                    "max_new_tokens": args.max_new_tokens, "attn_implementation": args.attn,
                    "run_utc": datetime.now(timezone.utc).isoformat(), "compute": m.get("compute"),
                }
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                secs = (m.get("compute") or {}).get("generate_elapsed_seconds")
                print(f"[{i}/{len(jobs)}] {tid}{sfx}: {m['output_tokens']} tok, {len(content)} chars"
                      f"{' (HIT CAP)' if m['output_tokens'] >= args.max_new_tokens else ''}"
                      f"{f', {secs:.0f}s' if secs else ''}", flush=True)
            # 4. tokens
            toks, n_run = drop_runaway(parse_tile_tokens(content, t, work_scale, geom))
            if n_run:
                print(f"    {tid}{sfx}: dropped {n_run} tokens from repetition loops (the same word {5}+ times in a row)", flush=True)
            tokens.extend(toks)
            st = tile_stats[tid]
            st.setdefault("rotations", {})[str(a)] = {
                "n_tokens": len(toks), "runaway_dropped": n_run, "content_chars": len(content), "output_tokens": meta.get("output_tokens"),
                "hit_cap": bool(meta.get("output_tokens", 0) >= args.max_new_tokens), "content": f"tiles/{stem}_{tid}{sfx}_content.txt"}
            st["status"] = "ok"
            st["n_tokens"] = st.get("n_tokens", 0) + len(toks) if a != 0 else len(toks)
            if a == 0:
                st.update({"content_chars": len(content), "output_tokens": meta.get("output_tokens"), "runaway_dropped": n_run,
                           "hit_cap": bool(meta.get("output_tokens", 0) >= args.max_new_tokens),
                           "content": f"tiles/{stem}_{tid}_content.txt"})
        # 5. union earlier passes, then dedupe across all of them
        merged_from = []
        for mpath in (args.merge or []):
            mp = Path(mpath).expanduser().resolve()
            mdoc = json.loads(mp.read_text())
            label = mp.parent.name
            n_in = 0
            for k in mdoc.get("tokens", []):
                if k.get("dup_of") is not None:
                    continue
                k = {**k, "tile": f"{label}:{k['tile']}", "dup_of": None, "fragment": False}
                k.pop("id", None)
                tokens.append(k); n_in += 1
            merged_from.append(str(mp)); print(f"merged {n_in} kept tokens from {mp.relative_to(PROJECT_ROOT) if mp.is_relative_to(PROJECT_ROOT) else mp}", flush=True)
        n_dup, n_frag = dedupe(tokens, args.dedupe_iou)
        if args.surya_lines:
            lines = json.loads(args.surya_lines.expanduser().read_text()).get("lines", [])
            n_conf = 0
            for tok in tokens:
                cx = (tok["bbox_xyxy"][0] + tok["bbox_xyxy"][2]) / 2; cy = (tok["bbox_xyxy"][1] + tok["bbox_xyxy"][3]) / 2
                hit = next((l for l in lines if l["bbox_xyxy"][0] - 4 <= cx <= l["bbox_xyxy"][2] + 4 and l["bbox_xyxy"][1] - 4 <= cy <= l["bbox_xyxy"][3] + 4), None)
                tok["surya_line"] = hit["id"] if hit else None
                tok["surya_conf"] = hit.get("confidence") if hit else None
                n_conf += hit is not None and tok["dup_of"] is None
            print(f"surya check: {n_conf} of {sum(1 for k in tokens if k['dup_of'] is None)} kept tokens lie in a Surya line box", flush=True)
        tokens.sort(key=lambda k: (k["dup_of"] is not None, k["bbox_xyxy"][1], k["bbox_xyxy"][0]))
        print(f"tokens: {len(tokens)} parsed, {n_dup} duplicates + {n_frag} fragments/conflicts suppressed, "
              f"{len(tokens) - n_dup - n_frag} kept", flush=True)

    # 6. outputs
    doc = {
        "source_image": str(src), "source_size": {"w": sw, "h": sh},
        "work_size": {"w": ww, "h": wh}, "work_scale": work_scale,
        "crop_source_px": args.crop, "crop_work_px": crop_box, "rotations_deg": [int(a) % 360 for a in args.rotations.split(",")], "shift_work_px": shift, "merged_from": merged_from, "surya_lines": str(args.surya_lines) if args.surya_lines else None, "tile_px": args.tile, "overlap_px": args.overlap, "grid": {"rows": rows, "cols": cols},
        "prompt": prompt, "model": args.model, "max_new_tokens": args.max_new_tokens,
        "min_ink": args.min_ink, "dedupe_iou": args.dedupe_iou, "dry_run": args.dry_run,
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "coordinate_note": "bbox_xyxy is in work-image pixels (top-left origin); bbox_xyxy_source divides by work_scale "
                           "to give pixels on the original scan. bbox_norm1000_tile is the raw model output on its tile.",
        "tiles": tile_stats,
        "tokens": tokens,
    }
    (out_dir / f"{stem}_tiles.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    if tokens:
        with open(out_dir / f"{stem}_tokens.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "text", "x1", "y1", "x2", "y2", "src_x1", "src_y1", "src_x2", "src_y2", "tile", "dup_of", "fragment", "surya_line", "surya_conf", "rotation", "conflict"])
            for k in tokens:
                w.writerow([k.get("id", ""), k["text"], *k["bbox_xyxy"], *k["bbox_xyxy_source"], k["tile"], "" if k["dup_of"] is None else k["dup_of"], "1" if k.get("fragment") else "", k.get("surya_line", ""), k.get("surya_conf", ""), k.get("rotation", 0), "1" if k.get("conflict") else ""])
    draw_overlay(work, plan, tokens, skipped, out_dir / f"{stem}_tile_overlay.jpg", labels=not args.no_labels, crop_box=crop_box)
    print(f"wrote {out_dir}/{stem}_tiles.json, _tokens.csv, _tile_overlay.jpg")


if __name__ == "__main__":
    main()
