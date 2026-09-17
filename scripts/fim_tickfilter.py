#!/usr/bin/env python3
"""
Strip HunyuanOCR "ruler noise" from a *_content.txt before overlaying or using the coordinates.

On sheets that still show the scan ruler / Kodak step wedge, HunyuanOCR reads a few real tick labels and then keeps
counting: 1,2,3…123 with boxes extrapolated along a straight line, off the ruler, across the map, and past the image
edge (y runs to 1000 and wraps back to ~100). p06b_rot112: 175 of 190 elements are such ticks. Two rules:

  range   coordinate outside [0,1000], or x2<x1 / y2<y1 (the wrapped boxes)
  run     >= --min-run consecutive elements whose text is a bare integer and increases by exactly 1 each step
          (block/lot numbers on the map are single tokens, so they survive; a street of consecutive house numbers
          would not — check the report, raise --min-run, or use --keep to whitelist values)

Writes <stem>_filtered_content.txt in the same `text(x1,y1),(x2,y2)` format, copies <stem>_metadata.json to
<stem>_filtered_metadata.json (overlay_boxes.py derives the metadata path from the `_content.txt` suffix), and writes
<stem>_filtered_report.json (what was dropped and why). Nothing is modified in place.

    python3 scripts/fim_tickfilter.py runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot112_content.txt
    scripts/fim_overlay.sh <stem>_resized.png <stem>_filtered_content.txt runs/hunyuan/single_page/overlays/filtered
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Same pattern as ~/projects/hunyuan/overlay_boxes.py (_SPOTTING_BOX_PATTERN).
BOX = re.compile(r"([^(]*?)\((\d+),(\d+)\),\((\d+),(\d+)\)", re.DOTALL)
NORM_MAX = 1000


def parse(content: str) -> list[dict]:
    out = []
    for i, m in enumerate(BOX.finditer(content)):
        text = m.group(1).strip()
        x1, y1, x2, y2 = (int(v) for v in m.groups()[1:])
        out.append({"i": i, "text": text, "box": [x1, y1, x2, y2], "raw": m.group(0)})
    return out


def flag_range(el: dict) -> bool:
    x1, y1, x2, y2 = el["box"]
    if any(v < 0 or v > NORM_MAX for v in el["box"]):
        return True
    return x2 < x1 or y2 < y1


def find_runs(els: list[dict], min_run: int) -> list[tuple[int, int]]:
    """(start_index, end_index_inclusive) over positions in `els` of counting runs."""
    runs, start = [], None
    prev_val = None
    for pos, el in enumerate(els):
        val = int(el["text"]) if el["text"].isdigit() else None
        if val is not None and prev_val is not None and val == prev_val + 1:
            if start is None:
                start = pos - 1
        else:
            if start is not None and pos - start >= min_run:
                runs.append((start, pos - 1))
            start = None
        prev_val = val
    if start is not None and len(els) - start >= min_run:
        runs.append((start, len(els) - 1))
    return runs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("content", type=Path, help="<stem>_content.txt from fim_hunyuan.py / fim_tile_ocr.py")
    ap.add_argument("--min-run", type=int, default=5, help="shortest +1 counting run to drop (default 5)")
    ap.add_argument("--keep", default="", help="comma-separated integer texts never dropped by the run rule")
    ap.add_argument("--no-range", action="store_true", help="disable the out-of-range / inverted-box rule")
    ap.add_argument("-o", "--output", type=Path,
                    help="default <stem>_filtered_content.txt beside the input (keep the _content.txt suffix)")
    args = ap.parse_args()

    content = args.content.read_text()
    els = parse(content)
    if not els:
        print(f"no `text(x1,y1),(x2,y2)` elements found in {args.content}", file=sys.stderr)
        return 1

    keep = {k.strip() for k in args.keep.split(",") if k.strip()}
    reason: dict[int, str] = {}
    runs_report = []
    for s, e in find_runs(els, args.min_run):
        runs_report.append({
            "first": els[s]["text"], "last": els[e]["text"], "count": e - s + 1,
            "first_box": els[s]["box"], "last_box": els[e]["box"],
        })
        for el in els[s:e + 1]:
            if el["text"] not in keep:
                reason[el["i"]] = "run"
    if not args.no_range:
        for el in els:
            if flag_range(el):
                reason[el["i"]] = "range" if el["i"] not in reason else "run+range"

    kept = [el for el in els if el["i"] not in reason]
    dropped = [el for el in els if el["i"] in reason]

    out_txt = args.output or args.content.with_name(args.content.name.replace("_content.txt", "_filtered_content.txt"))
    if out_txt == args.content:
        out_txt = args.content.with_name(args.content.stem + "_filtered_content.txt")
    out_txt.write_text("".join(el["raw"] for el in kept))
    meta_src = args.content.with_name(args.content.name.replace("_content.txt", "_metadata.json"))
    if meta_src != args.content and meta_src.is_file() and out_txt.name.endswith("_content.txt"):
        meta_dst = out_txt.with_name(out_txt.name.replace("_content.txt", "_metadata.json"))
        meta_dst.write_bytes(meta_src.read_bytes())
    out_json = out_txt.with_name(out_txt.name.replace("_content.txt", "_report.json") if out_txt.name.endswith("_content.txt") else out_txt.stem + "_report.json")
    out_json.write_text(json.dumps({
        "source": str(args.content), "min_run": args.min_run, "elements": len(els),
        "kept": len(kept), "dropped": len(dropped), "runs": runs_report,
        "dropped_elements": [{"text": el["text"], "box": el["box"], "reason": reason[el["i"]]} for el in dropped],
        "kept_texts": [el["text"] for el in kept],
    }, indent=1))

    by_reason: dict[str, int] = {}
    for r in reason.values():
        by_reason[r] = by_reason.get(r, 0) + 1
    print(f"{args.content.name}: {len(els)} elements -> kept {len(kept)}, dropped {len(dropped)} {by_reason}")
    for r in runs_report:
        print(f"  run {r['first']}..{r['last']} ({r['count']} boxes) from {r['first_box']} to {r['last_box']}")
    print(f"  kept: {', '.join(el['text'] for el in kept)}")
    print(f"  -> {out_txt}\n  -> {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
