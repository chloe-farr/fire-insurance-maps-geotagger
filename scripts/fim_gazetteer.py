#!/usr/bin/env python3
"""
Build the 1895 lookup tables from Surya OCR 2 output (runs/surya/<run>/inside-front-cover-*_surya2.json):

  streets_1895.csv   street, side, house_numbers, sheets      (index-to-streets; ditto marks expanded)
  blocks_1895.csv    block_number, sheet_1891_edition, sheet_old_edition   (block-numbers table)

These are the georeferencing scaffold: a block polygon's number -> its sheet(s); a street label -> the sheets
it appears on. Rows are merged across the per-column crops and the full-page crop, preferring the row variant
that kept the sheet column (the col1 crop dropped it on sub-rows).

    python3 scripts/fim_gazetteer.py runs/surya/2026-09-10_ocr2_fullpage
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def cells_of(html: str) -> list[list[str]]:
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", html, re.S):
        cells = [re.sub(r"<[^>]+>", " ", c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        cells = [re.sub(r"\s+", " ", c.replace("&amp;", "&")).strip() for c in cells]
        rows.append(cells)
    return rows


def clean_name(s: str) -> str:
    s = re.sub(r"[.… ]{2,}.*$", "", s)  # drop the dotted leader and anything after
    return s.strip(" .,:;").strip()


def clean_side(s: str) -> str:
    s = clean_name(s.strip(' "“”\''))  # ditto marks ride along in the side cell: '" " West Side'
    s = re.sub(r"[,\s]*\bNos?\.?\s*$", "", s)  # "East Side, Nos" -> "East Side"
    return s.strip(' .,:;"“”')


OPPOSITE_SIDE = {"East Side": "West Side", "West Side": "East Side", "North Side": "South Side", "South Side": "North Side"}


def range_start(house: str) -> int | None:
    m = re.match(r"\d+", house or "")
    return int(m.group()) if m else None


def infer_side_flips(records: list[dict]) -> list[dict]:
    """The printed index lists one side's house-number ranges, then the other side's, and the only marker of the switch is a
    'West Side' label that Surya OCR 2 drops in most reads (verified on Blanchard, 1895 index col1). When a street's ranges
    restart from a low number under the same side label, the rows from there on belong to the opposite side."""
    out: list[dict] = []
    prev_key = None; prev_start = None; prev_label = None; flipped_side = None
    for r in records:
        key = (r["source"], r["street"].lower())
        if key != prev_key:
            prev_key, prev_start, prev_label, flipped_side = key, None, None, None
        start = range_start(r["house_numbers"])
        side = r["side"]
        if side != prev_label:
            flipped_side = None; prev_start = None  # an explicit (new) label was read: trust it, restart the counter
        elif flipped_side is not None:
            side = flipped_side  # still inside the un-labelled second half
        elif start is not None and prev_start is not None and start < prev_start and side in OPPOSITE_SIDE:
            flipped_side = OPPOSITE_SIDE[side]; side = flipped_side
        prev_label = r["side"]
        if start is not None:
            prev_start = start
        out.append({**r, "side": side})
    return out


def resolve_variants(records: list[dict]) -> list[dict]:
    """Two sources reading one printed row differently ('194-263' vs '194-268', '18-66' vs '18 1/2-66'): same street,
    side and sheet, same starting number -> keep the column-crop read (about twice the pixels per glyph of the whole-cover
    scan). A header-only row (side + sheet, no range) whose sheet also appears on a ranged row of that street+side is the
    range's own header line and is dropped."""
    def quality(r: dict) -> tuple:
        return ("-col" in r["source"], len(r["house_numbers"]))
    best: dict[tuple, dict] = {}
    for r in records:
        k = (r["street"].lower(), r["side"].lower(), r["sheets"], range_start(r["house_numbers"]))
        if k not in best or quality(r) > quality(best[k]):
            best[k] = r
    kept = list(best.values())
    ranged = {(r["street"].lower(), r["side"].lower(), r["sheets"]) for r in kept if r["house_numbers"]}
    return [r for r in kept if r["house_numbers"] or (r["street"].lower(), r["side"].lower(), r["sheets"]) not in ranged]


def drop_header_only(records: list[dict]) -> list[dict]:
    """'Blanchard | East Side | | ' is the header line whose range and sheet were read into the rows beneath it."""
    informative = {(r["street"].lower()) for r in records if r["house_numbers"] or r["sheets"]}
    return [r for r in records if r["house_numbers"] or r["sheets"] or r["street"].lower() not in informative]


def is_ditto(s: str) -> bool:
    return bool(re.fullmatch(r'[\s"“”“”\'.]*', s)) and any(ch in s for ch in '"“”')


SHEET_RE = re.compile(r"^\s*\d{1,2}(\s*,\s*\d{1,2})*\s*$")
EMBEDDED_RANGE_RE = re.compile(r"(\d+\s*(?:1/2|½)?\s*-\s*\d*\s*(?:1/2|½)?)\s*[.\s]*$")
RANGE_RE = re.compile(r"^\s*\"?\s*\d+\s*(1/2|½)?\s*-\s*\d*\s*(1/2|½)?\s*[.\s]*$")


VALID_RANGE_RE = re.compile(r"^\d+( 1/2)?-(\d+( 1/2)?)?$")


def norm_range(s: str) -> str:
    s = s.strip('"“” ').replace("½", " 1/2")
    s = re.sub(r"[.\s]+$", "", s)
    s = re.sub(r"\s*-\s*", "-", re.sub(r"\s+", " ", s)).strip()
    return s if VALID_RANGE_RE.match(s) else ""  # '18-1-66' (misread ½) -> unusable, let a better source supply the row


def parse_streets(json_paths: list[Path], restrict_to: set[str] | None = None) -> list[dict]:
    """restrict_to: only accept streets in this set (used for the whole-cover scan, which also holds the
    'specials' list — churches, hotels, firms — that must not leak into the street table)."""
    out: dict[tuple, dict] = {}
    ordered: list[dict] = []
    for jp in json_paths:
        d = json.loads(jp.read_text())
        rows = [r for b in d["blocks"] for r in cells_of(b["html"])]
        cur_street = cur_side = None
        for r in rows:
            r = [c for c in r]
            if len(r) == 1 and re.fullmatch(r"[A-Z]", r[0].strip()):
                continue  # letter header
            if not r:
                continue
            # normalise to (name, side, range, sheets)
            name = r[0]
            ditto_name = is_ditto(name) or name.strip().startswith(('"', "“"))
            if ditto_name:
                name = cur_street
            else:
                name = clean_name(name)
                if name:
                    cur_street = name; cur_side = None
            if restrict_to is not None and (not name or name.lower() not in restrict_to):
                continue
            rest = r[1:]
            side = house = sheets = None
            if ditto_name:
                side = cur_side
                m = re.search(r"([A-Za-z][A-Za-z ]*Side[A-Za-z ,]*)", r[0])  # e.g. '" ... West Side, "' embedded in the ditto cell
                if m:
                    side = clean_side(m.group(1)); cur_side = side
            for c in rest:
                cc = c.strip()
                if cc and not is_ditto(cc):
                    cc = re.sub(r'^[\s"“”\']+', "", cc)  # '" " 70-124...' -> '70-124...'
                if not cc:
                    continue
                if SHEET_RE.match(cc):
                    sheets = re.sub(r"\s+", "", cc).replace(",", ", ")
                elif RANGE_RE.match(cc) or re.match(r"^\"?\s*\d+.*-", cc):
                    house = norm_range(cc)
                elif is_ditto(cc):
                    side = cur_side
                elif re.search(r"[A-Za-z]", cc):
                    m = EMBEDDED_RANGE_RE.search(cc)  # "East Side, Nos. 2- 26....." -> side + range
                    if m:
                        house = norm_range(m.group(1))
                        cc = cc[: m.start()]
                    if re.search(r"[A-Za-z]{3,}", cc.replace("Nos", "")):
                        side = clean_side(cc); cur_side = side
                    elif house is not None:
                        side = cur_side
            if house is None and sheets is None and side and re.match(r"^\d", side):
                sheets, side = side, None
            if not name:
                continue
            ordered.append({"street": name, "side": side or "", "house_numbers": house or "", "sheets": sheets or "", "source": jp.name})
    for rec in infer_side_flips(fold_shifted_sheets(ordered)):
        key = (rec["street"].lower(), rec["side"].lower(), rec["house_numbers"].lower())
        prev = out.get(key)
        if prev is None or (not prev["sheets"] and rec["sheets"]):
            out[key] = rec
    return sorted(out.values(), key=lambda x: (x["street"].lower(), x["side"], x["house_numbers"]))


def fold_shifted_sheets(records: list[dict]) -> list[dict]:
    """Column crops read 'Quadra | East Side | | 24' then '" | " | Nos. | 24-68' — the sheet belongs to the range row.
    Records arrive in reading order per source; fold such a header-only row into the range row that follows it."""
    out: list[dict] = []
    i = 0
    while i < len(records):
        a = records[i]
        b = records[i + 1] if i + 1 < len(records) else None
        if (b is not None and a["source"] == b["source"] and a["street"] == b["street"]
                and a["sheets"] and not a["house_numbers"] and b["house_numbers"] and not b["sheets"]
                and (b["side"] in ("", a["side"]))):
            out.append({**b, "side": a["side"] or b["side"], "sheets": a["sheets"]})
            i += 2
            continue
        out.append(a); i += 1
    return out


def parse_blocks(json_paths: list[Path]) -> list[dict]:
    out: dict[str, dict] = {}
    for jp in json_paths:
        d = json.loads(jp.read_text())
        for b in d["blocks"]:
            for r in cells_of(b["html"]):
                vals = [c for c in r if c]
                # rows come as triples (block, 1891 sheet, old sheet), possibly two triples side by side
                nums = [v for v in vals if re.fullmatch(r"\d+(½|1/2)?[a-z]?|-|—", v)]
                if len(nums) not in (2, 3, 4, 6):
                    continue
                step = 3 if len(nums) % 3 == 0 else 2
                for i in range(0, len(nums), step):
                    trip = nums[i:i + step]
                    if len(trip) < 2:
                        continue
                    blk = trip[0]
                    rec = {"block_number": blk, "sheet_1891_edition": trip[1], "sheet_old_edition": trip[2] if len(trip) > 2 else "", "source": jp.name}
                    if blk not in out or (not out[blk]["sheet_old_edition"] and rec["sheet_old_edition"]):
                        out[blk] = rec
    return sorted(out.values(), key=lambda x: (int(re.match(r"\d+", x["block_number"]).group()), x["block_number"]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="Surya OCR 2 run dir")
    ap.add_argument("-o", "--output-dir", type=Path, default=None, help="Default: the run dir")
    args = ap.parse_args()
    run = args.run.expanduser().resolve(); out = (args.output_dir or run).resolve(); out.mkdir(parents=True, exist_ok=True)

    street_srcs = sorted(run.glob("inside-front-cover-index-to-streets*_surya2.json"))
    cover_srcs = sorted(run.glob("inside-front-cover-index_surya2.json"))
    block_srcs = sorted(run.glob("inside-front-cover-block-numbers*_surya2.json"))
    streets = parse_streets(street_srcs)
    names = {s["street"].lower() for s in streets}
    # the whole-cover scan recovers sheet numbers the col1 crop dropped on sub-rows; take only known streets from it
    extra = parse_streets(cover_srcs, restrict_to=names)
    merged = {(s["street"].lower(), s["side"].lower(), s["house_numbers"].lower()): s for s in streets}
    for e in extra:
        k = (e["street"].lower(), e["side"].lower(), e["house_numbers"].lower())
        if k not in merged or (not merged[k]["sheets"] and e["sheets"]):
            merged[k] = e
    streets = drop_header_only(resolve_variants(merged.values()))
    streets.sort(key=lambda x: (x["street"].lower(), x["side"], range_start(x["house_numbers"]) or 0, x["house_numbers"]))
    blocks = parse_blocks(block_srcs)
    with open(out / "streets_1895.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["street", "side", "house_numbers", "sheets", "source"]); w.writeheader(); w.writerows(streets)
    with open(out / "blocks_1895.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["block_number", "sheet_1891_edition", "sheet_old_edition", "source"]); w.writeheader(); w.writerows(blocks)
    n_sheet = sum(1 for s in streets if s["sheets"])
    print(f"streets_1895.csv: {len(streets)} rows ({n_sheet} with sheets) from {len(street_srcs)} files")
    print(f"blocks_1895.csv:  {len(blocks)} blocks from {len(block_srcs)} files")
    for s in streets[:8]: print("  ", s["street"], "|", s["side"], "|", s["house_numbers"], "|", s["sheets"])
    for b in blocks[:5]: print("  block", b["block_number"], "-> 1891 sheet", b["sheet_1891_edition"], "| old", b["sheet_old_edition"])


if __name__ == "__main__":
    main()
