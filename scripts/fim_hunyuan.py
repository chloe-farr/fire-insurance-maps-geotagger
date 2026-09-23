#!/usr/bin/env python3
"""
HunyuanOCR one or more fire insurance sheets and write the same artifact triple the earlier
ad-hoc runs produced (see runs/hunyuan/):

    <out>/<stem>_resized.png    image actually fed to the model (longest edge <= --max-edge)
    <out>/<stem>_content.txt    raw model text, e.g. JOHNSON(529,32),(651,42)... (coords 0-1000)
    <out>/<stem>_metadata.json  prompt, sizes, scale hints, token counts, timing

Replaces the hard-coded ``~/projects/hunyuan/hunyuan_transformers.py`` for this dataset. Model
needs a Python with transformers>=5.13 (see README, Setup); re-execs into .venv or $HUNYUAN_PY if this one lacks it.

    python3 scripts/fim_hunyuan.py data/1895_p06b_rotations/fireinsurance_victoria_1895_p06b_rot000_cropped.png \
        --preset text_coords
    python3 scripts/fim_hunyuan.py data/1895/p25.jpg --prompt "..." --max-edge 2048 -o runs/hunyuan/2026-09-10_p25

Then draw boxes:  scripts/fim_overlay.sh <out>/<stem>_resized.png <out>/<stem>_content.txt
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "configs" / "prompts"
DEFAULT_MODEL = "tencent/HunyuanOCR"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hunyuan_compat import ensure_hunyuan_python as _ensure_hunyuan_python, hunyuan_infer_one, load_pil, resize_max_edge  # noqa: E402


def load_preset(name: str) -> str:
    """A preset name (stem of a file in configs/prompts/) or a path to any prompt text file."""
    given = Path(name).expanduser()
    path = given if given.is_file() else PROMPTS_DIR / f"{name}.txt"
    if not path.is_file():
        avail = ", ".join(sorted(p.stem for p in PROMPTS_DIR.glob("*.txt")))
        sys.exit(f"error: no preset {name!r} in {PROMPTS_DIR} (have: {avail})")
    return path.read_text(encoding="utf-8").strip()


def main() -> None:
    _ensure_hunyuan_python()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path, help="Image or PDF (first page) paths")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--preset", help=f"Prompt preset name from {PROMPTS_DIR.relative_to(PROJECT_ROOT)}/, or a path to a prompt .txt file")
    g.add_argument("--prompt", help="Literal prompt text")
    ap.add_argument("-o", "--output-dir", type=Path, default=None,
                    help="Default: runs/hunyuan/<YYYY-MM-DD>_<preset|custom>/")
    ap.add_argument("--max-edge", type=int, default=1536,
                    help="Resize so the longest edge <= this before inference (default 1536, as in prior runs)")
    ap.add_argument("--max-new-tokens", type=int, default=16384)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--revision", default=None, help="Hub revision (default: pinned pre-reformat commit, see _hunyuan_compat.py)")
    ap.add_argument("--attn", default="sdpa", help="attn_implementation: sdpa (default) or eager")
    args = ap.parse_args()

    prompt = load_preset(args.preset) if args.preset else args.prompt.strip()
    tag = args.preset or "custom"
    out_dir = args.output_dir or (PROJECT_ROOT / "runs" / "hunyuan" / f"{datetime.now():%Y-%m-%d}_{tag}")
    out_dir.mkdir(parents=True, exist_ok=True)

    images = [p.expanduser().resolve() for p in args.images]
    missing = [p for p in images if not p.is_file()]
    if missing:
        sys.exit("error: not found: " + ", ".join(map(str, missing)))

    from _hunyuan_compat import DEFAULT_REVISION, load_hunyuan

    print(f"Loading {args.model} (attn={args.attn}) ...", flush=True)
    model, processor = load_hunyuan(args.model, args.attn, args.revision or DEFAULT_REVISION)

    for img_path in images:
        stem = img_path.stem
        pil = load_pil(img_path)
        orig_size = pil.size
        pil, _ = resize_max_edge(pil, args.max_edge)
        resized_path = out_dir / f"{stem}_resized.png"
        pil.save(resized_path)
        print(f"[{stem}] {orig_size[0]}x{orig_size[1]} -> {pil.size[0]}x{pil.size[1]}", flush=True)

        text, meta = hunyuan_infer_one(
            model=model, processor=processor, image_pil=pil, image_path=resized_path,
            user_prompt=prompt, max_new_tokens=args.max_new_tokens,
        )
        (out_dir / f"{stem}_content.txt").write_text(text, encoding="utf-8")

        # Same keys as the legacy hunyuan_transformers.py metadata so overlay_boxes / old tooling still read it.
        record = {
            "processed_width": meta["processed_width"],
            "processed_height": meta["processed_height"],
            "saved_width": pil.size[0],
            "saved_height": pil.size[1],
            "scale_x": meta["scale_x"],
            "scale_y": meta["scale_y"],
            "context_prompt": prompt,
            "model_name_or_path": args.model, "model_revision": args.revision or DEFAULT_REVISION,
            "input_tokens": meta["input_tokens"],
            "output_tokens": meta["output_tokens"],
            "total_tokens": meta["total_tokens"],
            # additions
            "source_image": str(img_path),
            "source_width": orig_size[0],
            "source_height": orig_size[1],
            "max_edge": args.max_edge,
            "max_new_tokens": args.max_new_tokens,
            "attn_implementation": args.attn,
            "prompt_preset": args.preset,
            "run_utc": datetime.now(timezone.utc).isoformat(),
            "compute": meta.get("compute"),
        }
        (out_dir / f"{stem}_metadata.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"[{stem}] {meta['output_tokens']} output tokens, {len(text)} chars -> {out_dir}", flush=True)

    print("\nOverlay boxes with:\n  scripts/fim_overlay.sh <stem>_resized.png <stem>_content.txt")


if __name__ == "__main__":
    main()
