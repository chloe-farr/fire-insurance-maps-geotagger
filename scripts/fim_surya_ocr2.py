#!/usr/bin/env python3
"""
Surya OCR 2 (datalab-to/surya-ocr-2) on images, via a LOCAL vLLM server (the shared /opt/venvs/vllm setup:
`start_vllm datalab-to/surya-ocr-2`, http://127.0.0.1:8000/v1). Block-level output: layout blocks with polygon,
label, reading order and HTML text — no word coordinates.

    python3 scripts/fim_surya_ocr2.py data/1885/fireinsurance_victoria_1885_Index_col1.jpg data/1895/p06b.jpg
    -> runs/surya/<date>_ocr2/<stem>_surya2.json  <stem>_surya2.html  <stem>_surya2_overlay.jpg

Runs under SURYA_PY (default /opt/venvs/vllm/bin/python, surya-ocr 0.20 — the client the quickstart pairs with this
server); re-execs itself. --max-edge downsizes big sheets first (default 4096).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SURYA_PY = Path(os.environ.get("SURYA_PY", "/opt/venvs/vllm/bin/python"))
EXTRA = PROJECT_ROOT / ".surya-extra"
SERVER = os.environ.get("SURYA_INFERENCE_URL", "http://127.0.0.1:8000/v1")
os.environ.setdefault("SURYA_INFERENCE_URL", SERVER)
os.environ.setdefault("SURYA_INFERENCE_BACKEND", "vllm")

try:
    import surya  # noqa: F401
except ImportError:
    if SURYA_PY.is_file() and os.environ.get("FIM_SURYA_REEXEC") != "1":
        os.environ["FIM_SURYA_REEXEC"] = "1"
        os.environ["PYTHONPATH"] = str(EXTRA) + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
        os.execv(str(SURYA_PY), [str(SURYA_PY), *sys.argv])
    raise

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("-o", "--output-dir", type=Path, default=None)
    ap.add_argument("--max-edge", type=int, default=4096)
    args = ap.parse_args()
    out = args.output_dir or (PROJECT_ROOT / "runs" / "surya" / f"{datetime.now():%Y-%m-%d}_ocr2")
    out.mkdir(parents=True, exist_ok=True)

    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor
    t0 = time.perf_counter()
    rec = RecognitionPredictor(SuryaInferenceManager())
    print(f"client ready ({time.perf_counter() - t0:.1f}s), server {SERVER}", flush=True)

    for src in args.images:
        src = src.expanduser().resolve()
        img = Image.open(src).convert("RGB"); sw, sh = img.size
        scale = 1.0
        if args.max_edge and max(img.size) > args.max_edge:
            scale = args.max_edge / max(img.size)
            img = img.resize((round(sw * scale), round(sh * scale)), Image.Resampling.LANCZOS)
        t1 = time.perf_counter()
        res = rec([img])[0]
        secs = time.perf_counter() - t1
        blocks = []
        for b in sorted(res.blocks, key=lambda b: getattr(b, "reading_order", 0)):
            poly = [[round(x / scale), round(y / scale)] for x, y in b.polygon]
            html = getattr(b, "html", "") or ""
            blocks.append({"reading_order": b.reading_order, "label": b.label, "raw_label": getattr(b, "raw_label", ""),
                           "polygon_source_px": poly, "bbox_source_px": [round(v / scale) for v in b.bbox],
                           "skipped": getattr(b, "skipped", False), "error": getattr(b, "error", False),
                           "html": html, "text": re.sub(r"<[^>]+>", " ", html).strip()})
        doc = {"source_image": str(src), "source_size": {"w": sw, "h": sh}, "fed_scale": scale, "server": SERVER,
               "model": "datalab-to/surya-ocr-2", "seconds": round(secs, 1), "run_utc": datetime.now(timezone.utc).isoformat(),
               "n_blocks": len(blocks), "blocks": blocks}
        stem = src.stem
        (out / f"{stem}_surya2.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
        (out / f"{stem}_surya2.html").write_text("\n".join(f"<!-- {b['reading_order']} {b['label']} -->\n{b['html']}" for b in blocks))
        ov = img.copy(); d = ImageDraw.Draw(ov, "RGBA")
        try:
            f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", max(12, round(14 * img.width / 2000)))
        except OSError:
            f = ImageFont.load_default()
        for b in blocks:
            pts = [(x * scale, y * scale) for x, y in b["polygon_source_px"]]
            col = (200, 0, 0, 220) if not b["skipped"] else (120, 120, 120, 160)
            d.polygon(pts, outline=col, width=3)
            d.text((pts[0][0] + 3, pts[0][1] + 2), f"{b['reading_order']} {b['label']}", fill=col, font=f)
        ov.save(out / f"{stem}_surya2_overlay.jpg", quality=85)
        labels = {}
        for b in blocks:
            labels[b["label"]] = labels.get(b["label"], 0) + 1
        print(f"{src.name}: {len(blocks)} blocks in {secs:.1f}s {labels}; text chars {sum(len(b['text']) for b in blocks)}", flush=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
