#!/usr/bin/env python3
"""
Regenerate docs/run_history.md from everything under runs/.

Reads HunyuanOCR *_metadata.json / *_content.txt (single-image runs), <stem>_tiles.json (tiled runs from
fim_tile_ocr.py) and Chandra chandra_run.log / *_metadata.json. No model, no GPU; run it after any new run:

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


def surya(out: list[str]) -> None:
    base = RUNS / "surya"
    if not base.exists():
        return
    out.append("\n## Surya text-line detection (`surya.detection`, no vLLM) — runs/surya/\n")
    out.append("Line polygons only (no text). Run under a surya ≥0.22 interpreter — the shared /opt/venvs/vllm build (0.20) returns flat heatmaps. See `scripts/fim_surya_detect.py`.\n")
    out.append("| run dir | source | tiles | detect s | polygons kept | horizontal / vertical / rotated | median box h×w (work px) |")
    out.append("|---|---|---|---|---|---|---|")
    import statistics as st
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        for j in sorted(d.glob("*_surya_lines.json")):
            doc = json.loads(j.read_text()); L = doc.get("lines", [])
            h = doc.get("orientation_histogram", {})
            hs = [l["bbox_xyxy"][3] - l["bbox_xyxy"][1] for l in L] or [0]; ws = [l["bbox_xyxy"][2] - l["bbox_xyxy"][0] for l in L] or [0]
            out.append(f"| `{d.name}` | `{Path(doc['source_image']).name}` | {doc.get('n_tiles', 1)} | {doc.get('detect_seconds')} | {len(L)} | "
                       f"{h.get('~0° (horizontal)', '?')} / {h.get('~90° (vertical)', '?')} / {h.get('other (rotated)', '?')} | {st.median(hs):.0f}×{st.median(ws):.0f} |")


def surya_ocr2(out: list[str]) -> None:
    base = RUNS / "surya"
    runs = sorted(j for j in base.glob("*/*_surya2.json")) if base.exists() else []
    if not runs:
        return
    out.append("\n## Surya OCR 2 (`datalab-to/surya-ocr-2` via local vLLM) — block-level layout + HTML\n")
    out.append("| run dir | image | blocks | labels | table rows | text chars | s |")
    out.append("|---|---|---|---|---|---|---|")
    for j in runs:
        d = json.loads(j.read_text()); labels = {}
        for b in d["blocks"]:
            labels[b["label"]] = labels.get(b["label"], 0) + 1
        rows = sum(b["html"].count("<tr") for b in d["blocks"]); chars = sum(len(b["text"]) for b in d["blocks"])
        out.append(f"| `{j.parent.name}` | `{Path(d['source_image']).name}` | {d['n_blocks']} | {', '.join(f'{k}×{v}' for k, v in sorted(labels.items()))} | {rows} | {chars:,} | {d['seconds']} |")


def chandra(out: list[str]) -> None:
    base = RUNS / "chandra"
    if not base.exists():
        return
    out.append("\n## Chandra (`datalab-to/chandra`, hf method, custom prompts) — runs/chandra/\n")
    out.append("| run dir | date (UTC) | input | elapsed | prompt | output |")
    out.append("|---|---|---|---|---|---|")
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        logs = sorted(d.rglob("chandra_run.log"))
        mds = [p for p in d.rglob("*.md") if p.stat().st_size > 0]
        desc = "; ".join(f"`{md.relative_to(d)}` ({len(md.read_text(errors='replace')):,} chars)" for md in mds) or "(empty .md)"
        if not logs:
            meta = next(d.rglob("*_metadata.json"), None)
            tok = json.loads(meta.read_text()).get("total_token_count") if meta else ""
            out.append(f"| `{d.name}` | — (no log; pre-`--prompt` CLI) | `{d.name}` | — | ? ({tok} tokens) | {desc} |")
            continue
        for lg in logs:
            for b in re.split(r"={60}\nChandra OCR Run\n={60}\n", lg.read_text(errors="replace"))[1:]:
                date_ = re.search(r"^Date: (.+)$", b, re.M)
                inp = re.search(r"^Input path: (.+)$", b, re.M)
                el = re.search(r"^Elapsed: ([\d:.]+)", b, re.M)
                pr = re.search(r"^Prompt:\n(.+?)\n-{60}", b, re.S | re.M)
                prompt = pr.group(1).strip().replace("\n", " ") if pr else ""
                nested = "" if lg.parent == d else f" (nested `{lg.relative_to(d).parent}`)"
                out.append(f"| `{d.name}`{nested} | {date_.group(1)[:16] if date_ else ''} | `{Path(inp.group(1)).name if inp else ''}` | "
                           f"{el.group(1)[:7] if el else '—'} | {prompt[:110]}{'…' if len(prompt) > 110 else ''} | {desc} |")


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
    surya(out)
    surya_ocr2(out)
    chandra(out)
    out.append("\n### Notes\n")
    out.append("- `fireinsurance_victoria_1885_Index_table_col1` was run three times with progressively more explicit column definitions; only the last output survives (the CLI overwrites).")
    out.append("- `fireinsurance_victoria_1895_p06b_rot000` (Chandra) has nested output dirs from Chandra being pointed at its own output folder; the useful transcript is the top-level `.md`.")
    out.append("- `fireinsurance_victoria_1895_p25_rot000.md` (Chandra) degenerates into repeated `100' = N'` scale lines (runaway generation).")
    out.append("- Single-image HunyuanOCR runs of whole sheets either collapse or hit the cap; tiling (`fim_tile_ocr.py`) is the fix — see the tiled sections above.")
    out.append("- `single_page/overlays/` counts only overlays drawn with the current norm1000 tool (2026-09-10 on). Older ones normalised x by the max emitted coordinate (or 1500) and sit ~20% too far right; they are in `overlays/stale_old_tool/` (README there) and are not counted.")
    out.append("- `p06b_rot112` (1024×990, 2690 tok) is `ok` only in the sense that it terminated: 175 of its 190 elements are ruler-tick counting runs (1–20, 1–46, 15–123, the last wrapping past y=1000). `scripts/fim_tickfilter.py` strips them; 15 real labels remain.")
    text = "\n".join(out) + "\n"
    if args.stdout:
        print(text)
    else:
        (ROOT / "docs" / "run_history.md").write_text(text, encoding="utf-8")
        print(f"wrote docs/run_history.md ({len(text):,} chars)")


if __name__ == "__main__":
    main()
