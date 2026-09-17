#!/usr/bin/env python3
"""
Surya text-line DETECTION only (no recognition, no vLLM server) on a sheet, to see what its line polygons
give us: coverage, orientation of rotated/vertical labels, speed. Runs under the shared /opt/venvs/vllm
python (surya-ocr 0.20); re-execs itself into it if surya is not importable.

    python3 scripts/fim_surya_detect.py data/1895/p06b.jpg --work-max-edge 4096 --crop 300,150,7000,7980
    -> <out>/<stem>_surya_lines.json  (polygons in work px + source px, angle, confidence)
       <out>/<stem>_surya_overlay.jpg
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SURYA_PY = Path(os.environ.get("SURYA_PY", "/opt/venvs/vllm/bin/python"))

# /opt/venvs/vllm lacks a few pure-python deps surya imports (platformdirs); .surya-extra/ holds symlinks to
# them so they can be prepended without exposing the rest of ~/.local (whose torch would shadow the venv's).
EXTRA = PROJECT_ROOT / ".surya-extra"

try:
    import surya  # noqa: F401
except ImportError:
    if SURYA_PY.is_file() and os.environ.get("FIM_SURYA_REEXEC") != "1":
        os.environ["FIM_SURYA_REEXEC"] = "1"
        os.environ["PYTHONPATH"] = str(EXTRA) + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
        os.execv(str(SURYA_PY), [str(SURYA_PY), *sys.argv])
    raise

from PIL import Image, ImageDraw  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def poly_angle_deg(poly: list[list[float]]) -> float:
    """Orientation of the longer side of the quad, in degrees (0 = horizontal, 90 = vertical), range [0, 180)."""
    pts = [(float(x), float(y)) for x, y in poly]
    best = (0.0, 0.0)
    for i in range(len(pts)):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
        L = math.hypot(x2 - x1, y2 - y1)
        if L > best[0]:
            best = (L, math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0)
    return round(best[1], 1)


def _kill_children() -> None:
    """surya ≥0.22 spawns `surya.detection.server` as a child process and does not stop it; it would otherwise
    sit on ~850 MB of GPU memory after we exit."""
    import signal
    import subprocess
    try:
        kids = subprocess.run(["pgrep", "-P", str(os.getpid())], capture_output=True, text=True).stdout.split()
        for pid in kids:
            os.kill(int(pid), signal.SIGTERM)
    except Exception:
        pass


def main() -> None:
    import atexit
    atexit.register(_kill_children)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--output-dir", type=Path, default=None, help="Default runs/surya/<date>_detect_<stem>/")
    ap.add_argument("--work-max-edge", type=int, default=4096, help="Downscale before detection (0 = native). Default 4096.")
    ap.add_argument("--crop", metavar="X0,Y0,X1,Y1", default=None, help="Source-px content box; detection runs on this box only.")
    ap.add_argument("--tile", type=int, default=1536, help="Detect per tile of this size (work px) instead of on the whole box; 0 = whole box. "
                                                          "The detector resizes its input to a small fixed canvas, so a whole sheet degenerates to one blob.")
    ap.add_argument("--overlap", type=int, default=192)
    args = ap.parse_args()

    src = args.image.expanduser().resolve()
    stem = src.stem
    out = args.output_dir or (PROJECT_ROOT / "runs" / "surya" / f"{datetime.now():%Y-%m-%d}_detect_{stem}")
    out.mkdir(parents=True, exist_ok=True)

    sheet = Image.open(src).convert("RGB")
    sw, sh = sheet.size
    scale = 1.0
    work = sheet
    if args.work_max_edge and max(sw, sh) > args.work_max_edge:
        scale = args.work_max_edge / max(sw, sh)
        work = sheet.resize((round(sw * scale), round(sh * scale)), Image.Resampling.LANCZOS)
    ox = oy = 0
    if args.crop:
        cx0, cy0, cx1, cy1 = (int(v) for v in args.crop.split(","))
        ox, oy = round(cx0 * scale), round(cy0 * scale)
        work_in = work.crop((ox, oy, round(cx1 * scale), round(cy1 * scale)))
    else:
        work_in = work
    print(f"{src.name}: source {sw}x{sh} -> work {work.size[0]}x{work.size[1]} (scale {scale:.4f}); detector input {work_in.size[0]}x{work_in.size[1]}", flush=True)

    from surya.detection import DetectionPredictor
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from fim_tile_ocr import plan_tiles, iou

    t0 = time.perf_counter()
    det = DetectionPredictor()
    t1 = time.perf_counter()
    if args.tile:
        plan = plan_tiles(work_in.width, work_in.height, args.tile, args.overlap)
        crops = [work_in.crop((t["x0"], t["y0"], t["x1"], t["y1"])) for t in plan]
    else:
        plan = [{"r": 0, "c": 0, "x0": 0, "y0": 0, "x1": work_in.width, "y1": work_in.height}]
        crops = [work_in]
    results = det(crops)
    t2 = time.perf_counter()
    raw = [(b, t) for res, t in zip(results, plan) for b in res.bboxes]
    print(f"model load {t1 - t0:.1f}s, detection {t2 - t1:.1f}s over {len(plan)} tile(s), {len(raw)} raw polygons", flush=True)

    lines = []
    for b, t in raw:
        poly = [[round(x + t["x0"] + ox, 1), round(y + t["y0"] + oy, 1)] for x, y in b.polygon]
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        bbox = [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]
        # a line seen by two overlapping tiles: keep the first (they are near-identical)
        if any(iou(l["bbox_xyxy"], bbox) >= 0.5 for l in lines):
            continue
        lines.append({
            "id": len(lines), "tile": f"r{t['r']}c{t['c']}", "polygon": poly, "bbox_xyxy": bbox,
            "polygon_source": [[round(x / scale), round(y / scale)] for x, y in poly],
            "bbox_xyxy_source": [round(v / scale) for v in bbox],
            "angle_deg": poly_angle_deg(poly),
            "confidence": round(b.confidence, 3) if b.confidence is not None else None,
        })
    angles = [l["angle_deg"] for l in lines]
    hist = {"~0° (horizontal)": sum(1 for a in angles if a < 15 or a > 165), "~90° (vertical)": sum(1 for a in angles if 75 <= a <= 105),
            "other (rotated)": sum(1 for a in angles if 15 <= a < 75 or 105 < a <= 165)}
    print("orientation histogram:", hist, flush=True)

    doc = {"source_image": str(src), "source_size": {"w": sw, "h": sh}, "work_scale": scale, "crop_source_px": args.crop,
           "detector": "surya text_detection (settings.DETECTOR_MODEL_CHECKPOINT)", "surya_version": getattr(__import__("surya"), "__version__", "0.20"),
           "tile_px": args.tile, "overlap_px": args.overlap, "n_tiles": len(plan), "raw_polygons": len(raw), "load_seconds": round(t1 - t0, 2), "detect_seconds": round(t2 - t1, 2), "run_utc": datetime.now(timezone.utc).isoformat(),
           "orientation_histogram": hist, "lines": lines}
    (out / f"{stem}_surya_lines.json").write_text(json.dumps(doc, indent=1))

    img = work.copy(); d = ImageDraw.Draw(img, "RGBA")
    for l in lines:
        a = l["angle_deg"]
        col = (0, 90, 255, 230) if (a < 15 or a > 165) else (220, 0, 0, 230) if 75 <= a <= 105 else (0, 160, 0, 230)
        d.polygon([tuple(p) for p in l["polygon"]], outline=col, width=3)
    img.save(out / f"{stem}_surya_overlay.jpg", quality=88)
    print(f"wrote {out}/{stem}_surya_lines.json, _surya_overlay.jpg  (blue horizontal, red vertical, green rotated)")


if __name__ == "__main__":
    main()
