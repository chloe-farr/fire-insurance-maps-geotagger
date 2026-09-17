#!/usr/bin/env python3
"""
How rotation-robust is HunyuanOCR on a map tile?

For each angle in --angles: take a 1536·√2 square around the tile centre from the work image (so the corners are
real neighbouring map, not white), rotate it about its centre, centre-crop back to the tile size — every angle sees
the same pixel count at the same scale — OCR it, map every word box back into the unrotated tile frame, and score
against the upright (0°) result: which upright tokens are still
recovered, and which tokens appear only at some rotation. If recall stays high at every angle, text
orientation never needs to be detected; if it collapses at some angles, OCR each tile at the angles that
matter and union (see fim_tile_ocr.py --merge).

    python3 scripts/fim_rotation_probe.py --run runs/hunyuan/2026-09-10_tiles_p06b --tile-id r1c1
    -> runs/hunyuan/<date>_rotprobe_<stem>_<tile>/{rotprobe.json, rotprobe.md, rot_<angle>.png, rot_<angle>_content.txt}
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from PIL import Image  # noqa: E402
from _hunyuan_compat import ensure_hunyuan_python as _ensure_hunyuan_python  # noqa: E402

DEFAULT_MODEL = "tencent/HunyuanOCR"


def unrotate_point(xp: float, yp: float, angle_deg: float, rot_size: tuple[int, int], orig_size: tuple[int, int]) -> tuple[float, float]:
    """Inverse of PIL Image.rotate(angle) about the image centre: rotated-image px -> original-image px.
    PIL rotates counter-clockwise on screen; in y-down image coords that is x' = x cos + y sin, y' = -x sin + y cos
    about the centre, so the inverse is x = x' cos - y' sin, y = x' sin + y' cos. Works for expand=True and False."""
    th = math.radians(angle_deg)
    cx, cy = rot_size[0] / 2.0, rot_size[1] / 2.0
    ox, oy = orig_size[0] / 2.0, orig_size[1] / 2.0
    dx, dy = xp - cx, yp - cy
    return ox + dx * math.cos(th) - dy * math.sin(th), oy + dx * math.sin(th) + dy * math.cos(th)


def _selfcheck() -> None:
    """Assert the inverse mapping against PIL itself using a single dark pixel."""
    img = Image.new("L", (300, 200), 255)
    for x in range(227, 234):  # 7x7 dot centred on (230.5, 60.5); a lone pixel does not survive resampling
        for y in range(57, 64):
            img.putpixel((x, y), 0)
    for a in (30, 90, 137, 250):
        r = img.rotate(a, expand=True, fillcolor=255, resample=Image.Resampling.BICUBIC)
        px = r.load(); pts = [(x, y) for y in range(r.height) for x in range(r.width) if px[x, y] < 128]
        xr = sum(p[0] for p in pts) / len(pts) + 0.5; yr = sum(p[1] for p in pts) / len(pts) + 0.5
        x0, y0 = unrotate_point(xr, yr, a, r.size, img.size)
        assert abs(x0 - 230.5) < 1.5 and abs(y0 - 60.5) < 1.5, (a, x0, y0)


def main() -> None:
    _ensure_hunyuan_python()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True, help="A fim_tile_ocr.py output dir (needs <stem>_tiles.json)")
    ap.add_argument("--tile-id", required=True, help="e.g. r1c1")
    ap.add_argument("--angles", default="0,30,60,90,120,150,180,210,240,270,300,330")
    ap.add_argument("--preset", default="text_coords")
    ap.add_argument("--max-new-tokens", type=int, default=8192)
    ap.add_argument("--match-px", type=float, default=30.0, help="Centre distance (tile px) to count a token as the same as an upright one")
    ap.add_argument("-o", "--output-dir", type=Path, default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--attn", default="eager")
    args = ap.parse_args()

    _selfcheck()
    from _hunyuan_compat import DEFAULT_REVISION, extract_elements, hunyuan_infer_one, load_hunyuan

    Image.MAX_IMAGE_PIXELS = None
    run_dir = args.run.expanduser().resolve()
    doc = json.loads(next(run_dir.glob("*_tiles.json")).read_text())
    tinfo = doc["tiles"][args.tile_id]
    sheet = Image.open(doc["source_image"]).convert("RGB")
    ws = doc["work_scale"]
    work = sheet if ws == 1.0 else sheet.resize((doc["work_size"]["w"], doc["work_size"]["h"]), Image.Resampling.LANCZOS)
    tw, th_ = tinfo["x1"] - tinfo["x0"], tinfo["y1"] - tinfo["y0"]
    side = max(tw, th_)
    S = math.ceil(side * math.sqrt(2)) + 2                      # square that still covers the tile after any rotation
    cx, cy = (tinfo["x0"] + tinfo["x1"]) / 2.0, (tinfo["y0"] + tinfo["y1"]) / 2.0
    sq_box = (round(cx - S / 2), round(cy - S / 2), round(cx - S / 2) + S, round(cy - S / 2) + S)
    square = Image.new("RGB", (S, S), (255, 255, 255))
    square.paste(work.crop(sq_box), (0, 0))                     # PIL pads with black outside; paste keeps white where the sheet ends
    off = (S - side) // 2                                       # tile origin inside the square
    tile = square.crop((off, off, off + side, off + side))
    stem = Path(doc["source_image"]).stem
    out = args.output_dir or (PROJECT_ROOT / "runs" / "hunyuan" / f"{datetime.now():%Y-%m-%d}_rotprobe_{stem}_{args.tile_id}")
    out.mkdir(parents=True, exist_ok=True)
    tile.save(out / "tile_upright.png")
    prompt = (PROJECT_ROOT / "configs" / "prompts" / f"{args.preset}.txt").read_text().strip()
    angles = [int(a) for a in args.angles.split(",")]
    print(f"{stem} {args.tile_id}: tile {side}px, rotation square {S}px, centre ({cx:.0f},{cy:.0f}) work px", flush=True)

    def to_tile_frame(xr: float, yr: float, a: int) -> tuple[float, float]:
        # crop px -> square px -> unrotate about square centre -> tile px
        xs, ys = unrotate_point(xr + off, yr + off, a, (S, S), (S, S))
        return xs - off, ys - off

    model, proc = load_hunyuan(args.model, args.attn, DEFAULT_REVISION)
    per_angle: dict[int, list[dict]] = {}
    stats: dict[int, dict] = {}
    for a in angles:
        rot = square if a == 0 else square.rotate(a, expand=False, fillcolor=(255, 255, 255), resample=Image.Resampling.BICUBIC)
        img = rot.crop((off, off, off + side, off + side))
        p = out / f"rot_{a:03d}.png"; img.save(p)
        text, meta = hunyuan_infer_one(model=model, processor=proc, image_pil=img, image_path=p, user_prompt=prompt, max_new_tokens=args.max_new_tokens)
        (out / f"rot_{a:03d}_content.txt").write_text(text, encoding="utf-8")
        coords, texts = extract_elements(text, 1, 1)
        toks = []
        for (x1, y1, x2, y2), s in zip(coords, texts):
            s = s.strip()
            if not s:
                continue
            xr = (min(1000, max(0, x1)) + min(1000, max(0, x2))) / 2000.0 * img.width
            yr = (min(1000, max(0, y1)) + min(1000, max(0, y2))) / 2000.0 * img.height
            x0, y0 = to_tile_frame(xr, yr, a)
            toks.append({"text": s, "cx": round(x0, 1), "cy": round(y0, 1), "inside": 0 <= x0 <= tile.width and 0 <= y0 <= tile.height})
        per_angle[a] = toks
        secs = (meta.get("compute") or {}).get("generate_elapsed_seconds")
        stats[a] = {"canvas": list(img.size), "output_tokens": meta["output_tokens"], "hit_cap": meta["output_tokens"] >= args.max_new_tokens,
                    "seconds": round(secs or 0, 1), "n_tokens": len(toks), "n_alpha": sum(1 for t in toks if any(c.isalpha() for c in t["text"]))}
        print(f"{a:4}°: {len(toks):3} tokens ({stats[a]['n_alpha']} alphabetic), {meta['output_tokens']} out tok, {secs:.0f}s"
              f"{' HIT CAP' if stats[a]['hit_cap'] else ''}", flush=True)

    # only tokens that land inside the tile are comparable (corners show neighbouring map at non-90° angles)
    per_angle = {a: [k for k in toks if k["inside"]] for a, toks in per_angle.items()}
    base = per_angle[angles[0]]

    def match(t, pool):
        return any(k["text"].lower() == t["text"].lower() and math.hypot(k["cx"] - t["cx"], k["cy"] - t["cy"]) <= args.match_px for k in pool)

    rows = []
    for a in angles:
        toks = per_angle[a]
        recovered = sum(1 for t in base if match(t, toks))
        alpha_base = [t for t in base if any(c.isalpha() for c in t["text"])]
        rec_alpha = sum(1 for t in alpha_base if match(t, toks))
        extra = [t for t in toks if not match(t, base)]
        stats[a].update({"recall_all": round(recovered / max(1, len(base)), 3), "recall_alpha": round(rec_alpha / max(1, len(alpha_base)), 3),
                         "n_extra": len(extra), "extra_alpha": sorted({t["text"] for t in extra if any(c.isalpha() for c in t["text"])})})
        rows.append(f"| {a}° | {stats[a]['canvas'][0]}×{stats[a]['canvas'][1]} | {stats[a]['seconds']} | {stats[a]['n_tokens']} | "
                    f"{recovered}/{len(base)} ({stats[a]['recall_all']:.0%}) | {rec_alpha}/{len(alpha_base)} | {len(extra)} | "
                    f"{', '.join(stats[a]['extra_alpha'][:8])}{'…' if len(stats[a]['extra_alpha']) > 8 else ''} |")

    # words seen at ≥1 rotation that the upright pass did not produce (anywhere)
    union_extra = {}
    for a in angles[1:]:
        for t in per_angle[a]:
            if any(c.isalpha() for c in t["text"]) and not match(t, base):
                union_extra.setdefault(t["text"], []).append(a)
    md = [f"# Rotation probe — {stem} {args.tile_id}\n",
          f"Upright pass: {len(base)} tokens inside the tile. Each other row: the same {side}px view rotated about its centre (PIL, CCW; corners filled from the neighbouring map), OCR'd with `{args.preset}`, boxes mapped back; "
          f"a token counts as recovered if the same text lands within {args.match_px:.0f} px of its upright position.\n",
          "| angle | canvas | s | tokens | upright tokens recovered | alphabetic recovered | not in upright | alphabetic extras |",
          "|---|---|---|---|---|---|---|---|", *rows,
          "\nAlphabetic tokens found only when rotated (text → angles): " + (", ".join(f"{k} → {v}" for k, v in sorted(union_extra.items())) or "none")]
    (out / "rotprobe.md").write_text("\n".join(md) + "\n")
    json.dump({"run": str(run_dir), "tile_id": args.tile_id, "tile_px": side, "prompt": prompt, "angles": angles, "stats": stats, "tokens": per_angle,
               "run_utc": datetime.now(timezone.utc).isoformat()}, open(out / "rotprobe.json", "w"), indent=1)
    print("\n".join(md))


if __name__ == "__main__":
    main()
