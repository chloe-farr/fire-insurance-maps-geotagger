#!/usr/bin/env python3
"""
Regenerate docs/run_history.md from everything under runs/.

Reads HunyuanOCR *_metadata.json / *_content.txt (single-image runs), <stem>_tiles.json (tiled runs from
fim_tile_ocr.py). No model, no GPU; run it after any new run:

    python3 scripts/fim_run_history.py            # writes docs/run_history.md
    python3 scripts/fim_run_history.py --stdout   # print instead
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"


def verdict(nbytes: int, out_tok: int | None, cap: int) -> str:
    if nbytes < 3000:
        return "collapsed"
    if out_tok is not None and out_tok >= cap:
        return "runaway/cap"
    return "ok"


def hunyuan_single(d: Path, out: list[str]) -> list[tuple]:
    rows = []
    for meta in sorted(d.glob("*_metadata.json")):
        stem = meta.name[: -len("_metadata.json")]
        m = json.loads(meta.read_text())
        content = d / f"{stem}_content.txt"
        nbytes = content.stat().st_size if content.exists() else 0
        ov = list((d / "overlays").glob(f"{stem}_resized_overlay_v*.png")) if (d / "overlays").exists() else []
        cap = m.get("max_new_tokens", 16384)
        rows.append((stem, f"{m.get('saved_width')}×{m.get('saved_height')}", m.get("input_tokens"), m.get("output_tokens"),
                     nbytes, len(ov), verdict(nbytes, m.get("output_tokens"), cap), m.get("context_prompt", "")))
    if not rows:
        return rows
    out.append(f"\n### {d.relative_to(ROOT)}\n")
    prompts = sorted({r[7] for r in rows})
    out.append("Prompts used: " + "; ".join(f"“{p[:70]}{'…' if len(p) > 70 else ''}”" for p in prompts) + "\n")
    out.append("| stem | fed size | in tok | out tok | content bytes | overlays | verdict |")
    out.append("|---|---|---|---|---|---|---|")
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r[:7]) + " |")
    return rows


def hunyuan_tiled(d: Path, doc_path: Path, out: list[str]) -> None:
    doc = json.loads(doc_path.read_text())
    tiles = doc["tiles"]
    toks = doc.get("tokens", [])
    kept = [t for t in toks if t.get("dup_of") is None]
    done = [v for v in tiles.values() if v.get("status") == "ok"]
    rots = doc.get("rotations_deg") or [0]
    out.append(f"\n### {d.relative_to(ROOT)} — tiled ({doc['grid']['rows']}×{doc['grid']['cols']}, rotations {rots}, "
               f"{doc['tile_px']} px tiles, ≥{doc['overlap_px']} px overlap, work {doc['work_size']['w']}×{doc['work_size']['h']} @ {doc['work_scale']:.3f})\n")
    out.append(f"Source `{Path(doc['source_image']).name}` {doc['source_size']['w']}×{doc['source_size']['h']}; crop {doc.get('crop_source_px') or '—'}; "
               f"prompt “{doc['prompt'][:70]}{'…' if len(doc['prompt']) > 70 else ''}”; cap {doc['max_new_tokens']} tok/tile. "
               f"**{len(done)}/{len(tiles)} tiles OCR'd, {len(toks)} tokens parsed, {len(toks) - len(kept)} overlap duplicates removed, {len(kept)} kept.**\n")
    out.append("| tile | box (work px) | ink | out tok | chars | tokens | cap hit |")
    out.append("|---|---|---|---|---|---|---|")
    for tid, v in tiles.items():
        if v.get("status") != "ok":
            out.append(f"| {tid} | ({v['x0']},{v['y0']})–({v['x1']},{v['y1']}) | {v['ink_fraction']:.3f} | — | — | — | {v.get('status')} |")
            continue
        out.append(f"| {tid} | ({v['x0']},{v['y0']})–({v['x1']},{v['y1']}) | {v['ink_fraction']:.3f} | {v.get('output_tokens')} | "
                   f"{v.get('content_chars')} | {v.get('n_tokens')} | {'**yes**' if v.get('hit_cap') else 'no'} |")
    words = [t["text"] for t in kept if re.search(r"[A-Za-z]{3,}", t["text"])]
    if words:
        out.append("\nAlphabetic tokens kept (dedupe check by eye): " + ", ".join(sorted(set(words), key=str.lower)[:80]) + ("…" if len(set(words)) > 80 else ""))


def rotation_table(rows: list[tuple], out: list[str]) -> None:
    by: dict[str, list] = {}
    for r in rows:
        mm = re.match(r"fireinsurance_victoria_1895_(p\d+b?)_rot(\d+)(_cropped)?", r[0])
        if mm:
            by.setdefault(mm.group(1), []).append((int(mm.group(2)), mm.group(3) or "", r[4]))
    if not by:
        return
    out.append("\n### Rotation sensitivity (single-image runs)\n")
    out.append("Same sheet, HunyuanOCR at different page rotations; content bytes ≈ how much of the page was read.\n")
    out.append("| sheet | rotation → content bytes |")
    out.append("|---|---|")
    for sheet, lst in sorted(by.items()):
        out.append(f"| {sheet} | " + ", ".join(f"{a}°{c}: {b:,}" for a, c, b in sorted(lst)) + " |")


def rotprobes(out: list[str]) -> None:
    probes = sorted(RUNS.glob("hunyuan/*rotprobe*/rotprobe.md"))
    if not probes:
        return
    out.append("\n## HunyuanOCR rotation probes (`scripts/fim_rotation_probe.py`)\n")
    for md in probes:
        body = md.read_text().split("\n", 1)[1]  # drop the H1, keep table + summary
        out.append(f"\n### {md.parent.relative_to(ROOT)}\n" + body.strip() + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    out = ["# Run history\n",
           f"Generated {date.today().isoformat()} by `scripts/fim_run_history.py` from `runs/`. Re-run it after adding runs.\n",
           "\n## HunyuanOCR (`tencent/HunyuanOCR`)\n",
           "`verdict`: **collapsed** = < 3 KB returned (orientation defeated the model); **runaway/cap** = hit `max_new_tokens`, "
           "tail is repetition; **ok** = plausible transcript. Tiled runs list per-tile stats instead.\n"]
    single_rows: list[tuple] = []
    hy = RUNS / "hunyuan"
    if hy.exists():
        for d in sorted(p for p in hy.iterdir() if p.is_dir()):
            tiles_json = list(d.glob("*_tiles.json"))
            if tiles_json:
                hunyuan_tiled(d, tiles_json[0], out)
            else:
                single_rows += hunyuan_single(d, out)
    rotation_table(single_rows, out)
    rotprobes(out)
    out.append("\n### Notes\n")
    out.append("- Single-image HunyuanOCR runs of whole sheets either collapse or hit the cap; tiling (`fim_tile_ocr.py`) is the fix — see the tiled sections above.")
    out.append("- `single_page/overlays/` counts only overlays drawn with the current norm1000 tool (2026-09-10 on). Older ones normalised x by the max emitted coordinate (or 1500) and sit ~20% too far right; they are in `overlays/stale_old_tool/` (README there) and are not counted.")
    out.append("- `p06b_rot112` (1024×990, 2690 tok) is `ok` only in the sense that it terminated: 175 of its 190 elements are ruler-tick counting runs (1–20, 1–46, 15–123, the last wrapping past y=1000). `scripts/fim_tickfilter.py` strips them; 15 real labels remain.")
    text = "\n".join(out) + "\n"
    if args.stdout:
        print(text)
    else:
        (ROOT / "docs").mkdir(exist_ok=True)
        (ROOT / "docs" / "run_history.md").write_text(text, encoding="utf-8")
        print(f"wrote docs/run_history.md ({len(text):,} chars)")


if __name__ == "__main__":
    main()
