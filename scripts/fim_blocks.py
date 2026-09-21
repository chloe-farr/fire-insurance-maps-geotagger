#!/usr/bin/env python3
"""
Block-level GeoJSON with street labels, from a fim_tile_ocr.py run.

Blocks are the closed shapes of linework between street corridors. Recover them without any model:
  1. ink mask of the work image (dark pixels) — token boxes are NOT blanked: lot numbers sit on the lot lines
  2. seal hairline gaps, pinch off necks (--neck-px: the gap in a dashed or faded frontage line that lets a block
     interior leak into the street is a neck, a street is not), then classify white space: street space starts from the
     regions on the content border and the ones larger than any block (street network, harbour, margins) — and, when
     the sheet is georeferenced, from the regions a modern centreline runs through — and spreads to the pinched-off
     pieces that are open towards it (a severed piece of street corridor is open across its whole width; a block
     interior only along its gap). Everything else is enclosed: lots, alleys, courtyards, undivided block interiors
     -> fill them
  3. filled regions + their lines = solid blocks; a morphological opening (--open-px) drops lone strokes
     (shoreline, frame, dashed lines) so blocks don't chain together; trace each component -> polygon
  4. block number = largest-print numeric token inside the polygon (the bold block labels are ~2× lot-number height);
     'BLOCK 50' read as one token counts as the numeral 50
  5. street labels = alphabetic tokens within --street-reach px of the polygon, with distance, bearing from the
     block centroid and compass side -> the block's neighbouring streets

Two ways to run it:
  python3 scripts/fim_blocks.py <run>            no georeference needed: white regions on the border or larger than a
                                                 block are street, the rest is enclosed (no neck carving unless --neck-px
                                                 is given: without centrelines a severed piece of a dense downtown street
                                                 corridor looks like a block interior)
  python3 scripts/fim_blocks.py <run> --georef   the sheet's <stem>_georef.json exists: the street regions are carved at
                                                 their necks and the modern centrelines say which pieces are street, so
                                                 the open interiors of residential blocks with dashed frontage lines come
                                                 out as blocks. fim_georef.py does exactly this itself after its fit
                                                 (--retrace seeded), so a batch run needs nothing extra.

Scope: blocks drawn as closed outlines come out with number, lots and streets; residential blocks whose lot lines are
dashed and whose interiors are open come out once the necks are pinched. Wharf-side blocks whose lot lines stop at the
street with no frontage line at all (107, 16½, 15½ on 6b) are open to the street along a whole side and are NOT
recovered; close them with --close-lines (segments in source px along the missing frontage).

Output <run>/<stem>_blocks_px.geojson (FeatureCollection; coordinates in SOURCE-scan PIXELS, origin top-left, y down —
not a map: fim_georef.py turns it into <stem>_blocks_wgs84.geojson), <stem>_blocks.csv, <stem>_blocks_overlay.jpg.

    python3 scripts/fim_blocks.py runs/hunyuan/2026-09-10_tiles_p06b_rot
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fim_runlog import Stage, px_outputs_summary  # noqa: E402

SIDES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def side_of(bearing_deg: float) -> str:
    """Compass side for a bearing measured clockwise from north (image y is down, so north = -y)."""
    return SIDES[int(((bearing_deg + 22.5) % 360) // 45)]


def bearing(cx: float, cy: float, px: float, py: float) -> float:
    return (math.degrees(math.atan2(px - cx, -(py - cy))) + 360.0) % 360.0


# Colour words a printed key uses, as broad hue bands (degrees, HSV 0-360; a band may wrap). Language-level, deliberately
# wide: scans differ in colour balance, and a key transcribed from text ("red brick, grey stone") has no fill to measure.
# 'grey' is the exception: little chroma but darker than the paper (see material_of in trace()).
COLOUR_WORDS = {
    "yellow": (35, 75), "gelb": (35, 75), "jaune": (35, 75),
    "orange": (15, 40), "brown": (10, 45), "braun": (10, 45), "brun": (10, 45),
    "pink": (320, 20), "red": (330, 25), "rot": (330, 25), "rouge": (330, 25), "rose": (320, 20), "rosa": (320, 20),
    "green": (80, 170), "gruen": (80, 170), "grün": (80, 170), "vert": (80, 170),
    "blue": (180, 260), "blau": (180, 260), "bleu": (180, 260),
    "purple": (260, 320), "violet": (260, 320), "violett": (260, 320),
    "grey": None, "gray": None, "grau": None, "gris": None,
}

NUM_RE = re.compile(r"(?:BL(?:OC)?K\.?\s+)?(\d+(?:½|1/2)?)", re.I)  # '17', '16½', and the fused label 'BLOCK 50'


def floors_of(numerals: list[str]) -> float | None:
    """--floors single-numeral-1-3 (Sanborn convention, opt-in): a single numeral inside a building outline with a value
    from 1 to 3 inclusive is the number of floors ('1', '2', '1½' -> 1.5, '2½' -> 2.5, '3'). Anything else — no numeral,
    several, or a value outside that range (a lot number, a year) — is None. Off by default: on Goad plans the numeral
    inside a footprint is not reliably the storey count, so 'floors' stays null for a person to fill in."""
    if len(numerals) != 1:
        return None
    m = re.fullmatch(r"(\d+)(½|1/2)?", numerals[0])
    if not m:
        return None
    v = int(m.group(1)) + (0.5 if m.group(2) else 0.0)
    return v if 1 <= v <= 3 else None


def numeral(t: dict) -> str | None:
    """The numeral a token reads as, or None: bare numbers and 'BLOCK 50'-style fused block labels (-> '50')."""
    m = NUM_RE.fullmatch(t["text"].strip())
    return m.group(1) if m else None


def separate_necks(white: np.ndarray, r: int) -> tuple[np.ndarray, int, np.ndarray]:
    """Label the white mask so that regions joined only through a passage narrower than 2r px become separate labels.
    Erode by r (the passage vanishes, wide regions keep a core), label the cores, grow each label back inside the
    original white (geodesic dilation, so a label never crosses ink), then give the white that no core reached — regions
    thinner than 2r everywhere: a narrow lot, a margin strip, the gap between tramway rails — labels of their own.
    Returns (labels, n, has_core) with labels/n as connectedComponents gives them and has_core[label] False for the
    thin leftovers."""
    core = cv2.erode(white, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    n, lab = cv2.connectedComponents(core, connectivity=4)
    lab = lab.astype(np.float32)
    k = np.ones((3, 3), np.uint8)
    for _ in range(r + 2):
        grown = cv2.dilate(lab, k)
        new = (lab == 0) & (white > 0) & (grown > 0)
        if not new.any():
            break
        lab[new] = grown[new]
    lab = lab.astype(np.int32)
    rest = ((white > 0) & (lab == 0)).astype(np.uint8)
    n2, lab2 = cv2.connectedComponents(rest, connectivity=4)
    lab[lab2 > 0] = lab2[lab2 > 0] + (n - 1)
    has_core = np.zeros(n + n2 - 1, bool); has_core[1:n] = True
    return lab, n + n2 - 1, has_core


def classify_white(white: np.ndarray, box: list[int], args: argparse.Namespace, street_paint: np.ndarray | None) -> tuple[np.ndarray, dict]:
    """Split the white space of the sealed ink mask into street space and enclosed regions. Returns (enclosed mask, notes).

    First the plain regions: the ones on the content border (unless small enough to be a block the crop cuts through)
    and the ones larger than any block are street space — the street network, the harbour, the margins; everything else
    is enclosed (lots, alleys, courtyards). Then, with --neck-px, each street region is carved at its necks and its pieces
    are sorted again: the largest piece, the pieces on the border and the pieces a modern centreline runs through (when
    the sheet is georeferenced) stay street; a thin leftover that touches street space joins it; a piece with a core joins
    when it is open towards street space along more than --open-max of its boundary (a severed piece of corridor); what
    remains — open to the street only along the gap it leaked through — is an enclosed block interior. Pieces of an
    enclosed region are never touched."""
    area_box = (box[2] - box[0]) * (box[3] - box[1])
    b = args.seal + 2
    band = np.zeros_like(white)
    band[box[1]:box[1] + b, box[0]:box[2]] = 1; band[box[3] - b:box[3], box[0]:box[2]] = 1
    band[box[1]:box[3], box[0]:box[0] + b] = 1; band[box[1]:box[3], box[2] - b:box[2]] = 1
    # 1. plain regions
    np_, pl = cv2.connectedComponents(white, connectivity=4)
    pareas = np.bincount(pl.ravel(), minlength=np_)
    p_border = np.bincount(pl[band > 0], minlength=np_) > 0
    p_street = (p_border & (pareas > args.lot_max * area_box)) | (pareas > args.max_area * area_box); p_street[0] = True
    notes = {"white_regions": int(np_ - 1), "street_regions": int(p_street.sum()) - 1}
    if args.neck_px <= 0:
        enclosed = ~p_street
        notes.update({"after_necks": int(np_ - 1), "enclosed": int(enclosed.sum()), "street": int(p_street.sum()) - 1,
                      "seeds_border_or_oversize": 0, "seeds_centreline": 0, "spread": 0, "recovered": 0})
        return enclosed[pl].astype(np.uint8), notes, np.zeros_like(white)
    # 2. carve the street regions at their necks
    wl, nw, has_core = separate_necks(white, args.neck_px)
    areas = np.bincount(wl.ravel(), minlength=nw)
    parent = np.zeros(nw, np.int64)
    first = np.unique(wl, return_index=True)[1]
    parent[np.unique(wl)] = pl.ravel()[first]
    cand = p_street[parent]; cand[0] = False  # pieces of street regions: street unless they turn out enclosed
    on_border = np.bincount(wl[band > 0], minlength=nw) > 0
    largest = np.zeros(nw, bool)
    for pid in np.flatnonzero(p_street[1:]) + 1:
        kids = np.flatnonzero(parent == pid)
        if len(kids):
            largest[kids[np.argmax(areas[kids])]] = True
    street = cand & (on_border | largest | (areas > args.max_area * area_box))
    n_seed = int(street.sum())
    n_paint = 0
    if street_paint is not None:
        painted = np.bincount(wl[street_paint > 0], minlength=nw)
        seeded = cand & ~street & (painted >= args.seed_px)
        n_paint = int(seeded.sum()); street |= seeded
    street[0] = True
    # boundary of each piece: pixels with a 4-neighbour outside it; where that neighbour is another white piece a neck
    # was cut open — shared boundary length per pair
    bnd = np.zeros(nw, np.int64); pa, pb = [], []
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb = np.roll(wl, (dy, dx), axis=(0, 1))
        diff = (wl > 0) & (nb != wl)
        bnd += np.bincount(wl[diff], minlength=nw)
        o = diff & (nb > 0); pa.append(wl[o]); pb.append(nb[o])
    pa = np.concatenate(pa).astype(np.int64); pb = np.concatenate(pb).astype(np.int64)
    n_spread = 0
    if len(pa):
        keys, shared = np.unique(pa * nw + pb, return_counts=True)
        adj_a, adj_b = keys // nw, keys % nw
        while True:
            m = street[adj_b] & ~street[adj_a] & cand[adj_a]
            to_street = np.bincount(adj_a[m], weights=shared[m], minlength=nw)
            new = cand & ~street & ((~has_core & (to_street > 0)) | (to_street > args.open_max * np.maximum(bnd, 1)))
            if not new.any():
                break
            street |= new; n_spread += int(new.sum())
    enclosed = ~street; enclosed[0] = False
    recovered = cand & enclosed
    notes.update({"after_necks": int(nw - 1), "enclosed": int(enclosed.sum()), "street": int(street.sum()) - 1,
                  "seeds_border_or_oversize": n_seed, "seeds_centreline": n_paint, "spread": n_spread,
                  "recovered": int(recovered.sum()), "recovered_area_frac": round(float(areas[recovered].sum()) / area_box, 4)})
    return enclosed[wl].astype(np.uint8), notes, recovered[wl].astype(np.uint8)


def paint_segments(segments_source_px: np.ndarray, ws: float, shape: tuple[int, int], thickness: int = 2) -> np.ndarray:
    """Rasterise (n,2,2) segments given in source px onto a work-size mask."""
    H, W = shape
    mask = np.zeros((H, W), np.uint8)
    for (x1, y1), (x2, y2) in segments_source_px * ws:
        if max(x1, x2) < 0 or min(x1, x2) > W or max(y1, y2) < 0 or min(y1, y2) > H:
            continue
        cv2.line(mask, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))), 1, thickness)
    return mask


def segments_from_georef(run: Path, stem: str) -> np.ndarray | None:
    """Every modern centreline segment of the layer a sheet was georeferenced against, in source px (from
    <run>/<stem>_georef.json). None when the sheet is not georeferenced."""
    path = run / f"{stem}_georef.json"
    if not path.exists():
        return None
    from fim_georef import load_streets, apply  # local import: fim_georef imports this module
    g = json.loads(path.read_text())
    m = g["affine_map_to_source_px"]
    A_inv = np.array([[m["a11"], m["a12"], m["tx"]], [m["a21"], m["a22"], m["ty"]]])
    streets_path = Path(g["streets"])
    if not streets_path.is_absolute() and not streets_path.exists():
        streets_path = Path(__file__).resolve().parent.parent / streets_path
    streets, _, _ = load_streets(streets_path, None, None)
    segs = [s for k, s in streets.items() if k.strip() and len(s)]
    if not segs:
        return None
    allseg = np.concatenate(segs)  # (n,2,2) map
    return apply(A_inv, allseg.reshape(-1, 2)).reshape(-1, 2, 2)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="fim_tile_ocr.py output dir (needs <stem>_tiles.json)")
    ap.add_argument("--georef", action="store_true", help="seed the street space with the modern centrelines of <run>/<stem>_georef.json (the sheet must have been georeferenced by fim_georef.py); without it only the border and oversize regions seed it")
    ap.add_argument("--blank-tokens", action="store_true", help="Cut OCR token boxes out of the ink before segmenting (breaks enclosure on these plans; here for experiments)")
    ap.add_argument("--seal", type=int, default=3, help="Dilate ink by this many work px to close hairline gaps before flood-classifying white space (default 3)")
    ap.add_argument("--neck-px", type=int, default=None, help="Carve the street regions at passages narrower than 2x this many work px before classifying their pieces: the gap in a dashed or faded frontage line through which a block interior leaks into the street. Default 16 with --georef (the modern centrelines then say which pieces are street), 0 = off without it, because without that evidence a severed piece of a dense downtown street corridor looks like a block interior and gets filled. Set it explicitly to carve an un-georeferenced residential sheet anyway")
    ap.add_argument("--open-max", type=float, default=0.10, help="A pinched-off region joins the street space when more than this fraction of its boundary is open (a neck, not linework) towards street space, spreading until nothing changes (default 0.10): a block interior is open only along its gap and stays enclosed, a severed piece of street corridor is open across its whole width and rejoins the street")
    ap.add_argument("--seed-px", type=int, default=20, help="with --georef: a white region with at least this many px of modern centreline drawn through it is street space (default 20)")
    ap.add_argument("--lot-max", type=float, default=0.05, help="White regions on the content border are street space unless they are at most this fraction of the content box — a block the crop cuts through (default 0.05)")
    ap.add_argument("--open-px", type=int, default=10, help="Opening radius (work px) applied to the filled mask to drop lone strokes: frame, shoreline, dashed lines, a double tramway line (~16-20 px once sealed, which otherwise chains the blocks along it). Must exceed the thickest such stroke and stay below the narrowest block (default 10)")
    ap.add_argument("--dark", type=int, default=160, help="Gray level below which a pixel is ink (default 160)")
    ap.add_argument("--min-area", type=float, default=0.0015, help="Min block area as a fraction of the content box (default 0.0015)")
    ap.add_argument("--max-area", type=float, default=0.2, help="Max block area fraction (default 0.2): white regions larger than this are street space and solid components larger than this are the margin/border. A large residential block is ~0.12 of a 1895 Victoria sheet")
    ap.add_argument("--street-reach", type=float, default=170.0, help="Max distance (work px) from a block edge to a street label that counts as adjacent (default 170 ≈ 2 street widths)")
    ap.add_argument("--bold-stroke", type=float, default=9.0, help="Numerals with strokes at least this thick (work px) are block numbers (default 9; lot numbers are ~4–6, block numbers 11+)")
    ap.add_argument("--number-reach", type=float, default=80.0, help="Blocks without a bold number inside take the nearest one within this many work px (an alley's width, not a street's), flagged inferred (default 80)")
    ap.add_argument("--close-frontages", action="store_true", help="EXPERIMENTAL: reconstruct missing street-frontage lines from rows of un-enclosed lot numbers. Off by default — house numbers often sit in the street corridor, which fools it (6b: cut blocks 16 and 15).")
    ap.add_argument("--close-lines", nargs="*", default=None, metavar="X1,Y1,X2,Y2",
                    help="Segments in SOURCE px drawn into the ink before segmentation, to close blocks the plan leaves open (wharf lots with no frontage line). A few per sheet; recorded in the GeoJSON.")
    ap.add_argument("--frontage-reach", type=float, default=450.0, help="Un-enclosed lot numbers are grouped with the nearest block numeral within this many work px (default 450)")
    ap.add_argument("--simplify", type=float, default=3.0, help="Polygon simplification tolerance (work px)")
    ap.add_argument("--buildings", choices=["enclosed", "off"], default="enclosed", help="'enclosed' (default): every enclosed white region inside a traced block becomes a footprint in <stem>_buildings_px.geojson, linked to its block, carrying only the OCR tokens inside it (numerals and words, split by regex) — nothing is inferred about what the shape is. 'off': no buildings file")
    ap.add_argument("--building-min", type=float, default=0.00008, help="smallest footprint kept, as a fraction of the content box (default 0.00008 ~ a 10 ft shed on a 50 ft/in sheet)")
    ap.add_argument("--building-max-share", type=float, default=0.6, help="an enclosed region covering more than this share of its block is the block's own open ground, not a footprint (default 0.6)")
    ap.add_argument("--floors", choices=["off", "single-numeral-1-3"], default="off", help="how the 'floors' field of a footprint is filled. 'off' (default): always null, left for a person (Goad plans). 'single-numeral-1-3': when exactly one numeral lies inside the outline and reads 1 to 3 inclusive (1½ -> 1.5) it is the number of floors — the Sanborn convention")
    ap.add_argument("--legend", type=Path, default=None, help="the plan's colour key as a config (configs/legend/<edition>.json: min_chroma, materials with hue ranges, the meaning of 'untinted'): each outline's measured wash (wash_rgb, wash_chroma — always recorded) is looked up in it and the key's own words become 'material'. Without a legend nothing is read into the colour")
    ap.add_argument("-o", "--output-dir", type=Path, default=None, help="Default: the run dir")
    return ap


def default_args(run: Path, **overrides) -> argparse.Namespace:
    """The CLI defaults as a namespace, for callers (fim_georef.py) that trace without a command line."""
    args = build_parser().parse_args([str(run)])
    for k, v in overrides.items():
        setattr(args, k, v)
    if args.neck_px is None:
        args.neck_px = 16 if args.georef else 0
    return args


def trace(args: argparse.Namespace, street_segments_source_px: np.ndarray | None = None) -> dict:
    """Trace the blocks of a run and write <stem>_blocks_px.geojson / .csv / _overlay.jpg. Returns the FeatureCollection."""
    run = args.run.expanduser().resolve()
    doc = json.loads(next(run.glob("*_tiles.json")).read_text())
    stem = Path(doc["source_image"]).stem
    out = (args.output_dir or run).resolve(); out.mkdir(parents=True, exist_ok=True)
    ws = doc["work_scale"]
    sheet = Image.open(doc["source_image"]).convert("RGB")
    work = sheet if ws == 1.0 else sheet.resize((doc["work_size"]["w"], doc["work_size"]["h"]), Image.Resampling.LANCZOS)
    W, H = work.size
    box = doc.get("crop_work_px") or [0, 0, W, H]
    tokens = [t for t in doc["tokens"] if t["dup_of"] is None]

    # 1. ink mask
    gray = np.asarray(work.convert("L"))
    ink = (gray < args.dark).astype(np.uint8)
    content = np.zeros_like(ink); content[box[1]:box[3], box[0]:box[2]] = 1
    ink &= content
    if args.blank_tokens:  # off by default: lot numbers sit on lot boundaries, so cutting their boxes opens the lots to the street
        for t in tokens:
            x1, y1, x2, y2 = t["bbox_xyxy"]; pad = 3
            ink[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad] = 0
    area_box = (box[2] - box[0]) * (box[3] - box[1])

    # 1a. manual closing segments (source px -> work px)
    manual_lines = []
    for seg in (args.close_lines or []):
        x1, y1, x2, y2 = (int(v) for v in seg.split(","))
        p1 = (round(x1 * ws), round(y1 * ws)); p2 = (round(x2 * ws), round(y2 * ws))
        cv2.line(ink, p1, p2, 1, thickness=3)
        manual_lines.append({"source_px": [[x1, y1], [x2, y2]], "work_px": [p1, p2]})
    if manual_lines:
        print(f"drew {len(manual_lines)} manual closing segment(s)", flush=True)

    # 1b. open frontages. Wharf-side blocks are drawn with lot lines that stop at the street with no frontage line,
    #     so their lots are open to the street corridor. Their house numbers sit in a straight row along that frontage:
    #     take lot numbers whose surrounding white belongs to the open (street/water) component, group them by nearest
    #     block numeral, find collinear rows (RANSAC), and keep the row whose line — once drawn into the ink — actually
    #     encloses the block numeral. On with --close-frontages.
    frontage_lines = []
    if args.close_frontages:
        seal_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * args.seal + 1, 2 * args.seal + 1))

        def white_components(ink_img):
            s = cv2.dilate(ink_img, seal_k)
            w = ((1 - s) & content).astype(np.uint8)
            n_, l_, st_, _ = cv2.connectedComponentsWithStats(w, connectivity=4)
            return l_, st_[:, cv2.CC_STAT_AREA]

        pl, parea = white_components(ink)
        big_white = {i for i in range(1, len(parea)) if parea[i] > args.lot_max * area_box}
        num_all = [t for t in tokens if numeral(t) and not t.get("rotation")]
        hts = [t["bbox_xyxy"][3] - t["bbox_xyxy"][1] for t in num_all] or [20]
        mh = statistics.median(hts)

        def _stroke(t):
            x1, y1, x2, y2 = t["bbox_xyxy"]; sub = (gray[y1:y2, x1:x2] < args.dark).astype(np.uint8)
            return 2.0 * float(cv2.distanceTransform(sub, cv2.DIST_L2, 3).max()) if sub.any() else 0.0

        def ring_label(t, lab_img):
            """Majority white-component label in a ring just outside the token box (the lot interior it sits in)."""
            x1, y1, x2, y2 = t["bbox_xyxy"]; r = 8
            ring = lab_img[max(0, y1 - r):y2 + r, max(0, x1 - r):x2 + r].copy()
            ring[r:r + (y2 - y1), r:r + (x2 - x1)] = 0
            vals = ring[ring > 0]
            return int(np.bincount(vals).argmax()) if vals.size else 0

        def tok_centre(t):
            b = t["bbox_xyxy"]; return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

        bolds = [t for t in num_all if (t["bbox_xyxy"][3] - t["bbox_xyxy"][1]) >= 1.3 * mh and _stroke(t) >= args.bold_stroke]
        groups: dict[int, list] = {}
        for t in num_all:
            if t in bolds or ring_label(t, pl) not in big_white:
                continue
            cx_, cy_ = tok_centre(t)
            dists = [(math.hypot(cx_ - bx, cy_ - by), k) for k, (bx, by) in enumerate(map(tok_centre, bolds))]
            if dists and min(dists)[0] <= args.frontage_reach:
                groups.setdefault(min(dists)[1], []).append((cx_, cy_))

        def collinear_rows(pts, tol=20.0, min_pts=4, max_rows=3):
            """Greedy RANSAC over point pairs: largest collinear subsets first."""
            rows = []; rest = list(pts)
            while len(rest) >= min_pts and len(rows) < max_rows:
                best = None
                for i in range(len(rest)):
                    for j in range(i + 1, len(rest)):
                        (x1, y1), (x2, y2) = rest[i], rest[j]
                        L = math.hypot(x2 - x1, y2 - y1)
                        if L < 40:
                            continue
                        nx, ny = -(y2 - y1) / L, (x2 - x1) / L
                        inl = [q for q in rest if abs((q[0] - x1) * nx + (q[1] - y1) * ny) <= tol]
                        if best is None or len(inl) > len(best):
                            best = inl
                if best is None or len(best) < min_pts:
                    break
                rows.append(best); rest = [q for q in rest if q not in best]
            return rows

        for k, pts in groups.items():
            bx, by = tok_centre(bolds[k]); bxi, byi = int(bx), int(by)
            if pl[byi, bxi] and pl[byi, bxi] not in big_white:
                continue  # this block is already enclosed
            best = None
            for row in collinear_rows(pts):
                arr = np.array(row, dtype=np.float32)
                vx, vy, x0, y0 = cv2.fitLine(arr, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
                proj = [((px - x0) * vx + (py - y0) * vy) for px, py in row]
                lo, hi = min(proj) - 60, max(proj) + 60
                p1 = (int(x0 + vx * lo), int(y0 + vy * lo)); p2 = (int(x0 + vx * hi), int(y0 + vy * hi))
                trial = ink.copy(); cv2.line(trial, p1, p2, 1, thickness=3)
                tl, ta = white_components(trial)
                lab = tl[byi, bxi]
                if lab == 0:
                    # numeral centre on ink: sample the ring instead
                    lab = ring_label(bolds[k], tl)
                if lab and ta[lab] <= args.lot_max * area_box:
                    score = ta[lab]
                    if best is None or score > best[0]:
                        best = (score, p1, p2, len(row))
            if best:
                cv2.line(ink, best[1], best[2], 1, thickness=3)
                frontage_lines.append({"block_number": numeral(bolds[k]), "n_lot_numbers": best[3], "line_work_px": [best[1], best[2]],
                                       "enclosed_area_frac": round(float(best[0]) / area_box, 4)})
        if frontage_lines:
            print("closed open frontages:", ", ".join(f"{f['block_number']} ({f['n_lot_numbers']} lot nos, encloses {f['enclosed_area_frac']:.3f})" for f in frontage_lines), flush=True)
        else:
            print("no open frontages closed", flush=True)

    # 2. enclosure: seal hairline gaps, pinch off necks, classify white space into street space and enclosed regions
    sealed = cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * args.seal + 1, 2 * args.seal + 1)))
    white = ((1 - sealed) & content).astype(np.uint8)
    paint = paint_segments(street_segments_source_px, ws, (H, W)) & content if street_segments_source_px is not None else None
    enclosed, notes, open_interior = classify_white(white, box, args, paint)
    print(f"white space: {notes['white_regions']} regions, {notes['street_regions']} of them street (border or oversize); carved at necks narrower than "
          f"{2 * args.neck_px} px into {notes['after_necks']} pieces: {notes['seeds_border_or_oversize']} anchor the street (largest piece, border, oversize), "
          f"{notes['seeds_centreline']} hold a modern centreline, {notes['spread']} joined them, {notes['recovered']} pieces of street regions are enclosed block "
          f"interiors ({notes.get('recovered_area_frac', 0):.1%} of the sheet)", flush=True)
    # 3. a block = its lots + the lines around them; an opening wider than a line drops lone strokes
    #    (shoreline, dashed lines, the frame) that would otherwise chain blocks together.
    solid = (enclosed | sealed) & content
    solid = cv2.morphologyEx(solid, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * args.open_px + 1, 2 * args.open_px + 1)))
    n, labels, stats, cents = cv2.connectedComponentsWithStats(solid, connectivity=8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * args.seal + 1, 2 * args.seal + 1))  # undo the seal when tracing

    # token classes
    numeric = [t for t in tokens if numeral(t) and not t.get("rotation")]  # rotated-view boxes are inflated extents
    heights = [t["bbox_xyxy"][3] - t["bbox_xyxy"][1] for t in numeric] or [20]
    med_h = statistics.median(heights)
    corners = [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]

    def stroke_px(t) -> float:
        """Thickest stroke inside the token box (2× the distance-transform peak). On 6b block numerals are 11–21 px,
        lot numbers 3–6 px, so this separates them where height cannot (tilted lot numbers have tall boxes)."""
        x1, y1, x2, y2 = t["bbox_xyxy"]
        sub = (gray[y1:y2, x1:x2] < args.dark).astype(np.uint8)
        if not sub.any():
            return 0.0
        return 2.0 * float(cv2.distanceTransform(sub, cv2.DIST_L2, 3).max())

    def is_bold(t):  # block numbers: heavy print, well away from the sheet-number corners
        b = t["bbox_xyxy"]; cx_, cy_ = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        return ((b[3] - b[1]) >= 1.3 * med_h and stroke_px(t) >= args.bold_stroke
                and all(math.hypot(cx_ - x, cy_ - y) > 150 for x, y in corners))

    bold_all = [t for t in numeric if is_bold(t)]
    streets = [t for t in tokens if re.search(r"[A-Za-z]{3,}", t["text"]) and not t.get("conflict")]

    def centre(t):
        b = t["bbox_xyxy"]; return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

    # 3-5. per component
    features, rows, polys = [], [], []
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < args.min_area * area_box or area > args.max_area * area_box:
            continue
        comp = (labels == i).astype(np.uint8)
        comp = cv2.erode(comp, k)  # undo the seal
        cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        cnt = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(cnt) < args.min_area * area_box * 0.5:
            continue
        cnt = cv2.approxPolyDP(cnt, args.simplify, True)
        poly = [(float(p[0][0]), float(p[0][1])) for p in cnt]
        if len(poly) < 3:
            continue
        bx, by, bw, bh = cv2.boundingRect(cnt)
        touches_edge = bx <= box[0] + 6 or by <= box[1] + 6 or bx + bw >= box[2] - 6 or by + bh >= box[3] - 6
        if touches_edge and (max(bw, bh) / max(1, min(bw, bh)) > 4 or cv2.contourArea(cnt) / (bw * bh) < 0.35):
            continue  # frame line / margin strip, not a block
        m = cv2.moments(cnt); cx, cy = m["m10"] / max(m["m00"], 1), m["m01"] / max(m["m00"], 1)

        inside = [t for t in numeric if cv2.pointPolygonTest(cnt, centre(t), False) >= 0]
        big = [t for t in inside if is_bold(t)]
        inferred = False
        if big:
            block_no = numeral(max(big, key=lambda t: t["bbox_xyxy"][3] - t["bbox_xyxy"][1]))
        else:
            # a block split by an alley keeps its number in one half; take the nearest bold number within reach
            cand = [(-cv2.pointPolygonTest(cnt, centre(t), True), t) for t in bold_all]
            cand = [(dd, t) for dd, t in cand if dd <= args.number_reach]
            block_no = numeral(min(cand, key=lambda c: c[0])[1]) if cand else None
            inferred = block_no is not None
        lots = sorted({numeral(t) for t in inside if t not in big}, key=lambda s: (len(s), s))

        near = []
        for t in streets:
            px, py = centre(t)
            d = -cv2.pointPolygonTest(cnt, (px, py), True)  # positive = outside, in px
            if 0 <= d <= args.street_reach:
                b = bearing(cx, cy, px, py)
                near.append({"name": t["text"], "distance_px": round(d), "bearing_deg": round(b), "side": side_of(b),
                             "label_bbox_source": t["bbox_xyxy_source"], "rotation_view": t.get("rotation", 0)})
        near.sort(key=lambda s: s["distance_px"])
        seen = set(); near = [s for s in near if not (s["name"].lower() in seen or seen.add(s["name"].lower()))]

        fid = len(features)
        polys.append((cnt, block_no, near))
        features.append({
            "type": "Feature",
            "id": fid,
            "geometry": {"type": "Polygon", "coordinates": [[[round(x / ws), round(y / ws)] for x, y in poly] + [[round(poly[0][0] / ws), round(poly[0][1] / ws)]]]},
            "properties": {
                "sheet": stem, "block_id": f"{stem}:block:{block_no if block_no and not inferred else f'fid{fid}'}",
                "block_number": block_no, "block_number_inferred": inferred, "lot_numbers": lots,
                "streets": near, "street_names": [s["name"] for s in near],
                "area_source_px2": round(cv2.contourArea(cnt) / ws / ws),
                "centroid_source_px": [round(cx / ws), round(cy / ws)],
            },
        })
        rows.append([fid, (block_no or "") + ("*" if inferred else ""), "; ".join(f"{s['name']} ({s['side']}, {s['distance_px']}px)" for s in near), " ".join(lots)])

    # 6. buildings: the enclosed white regions inside each block, each linked to its block by block_id. Attributes are
    #    only what the OCR read inside the outline — numerals and words, split by regex — nothing is inferred about
    #    what the shape is (on a Goad/Sanborn plan the numeral inside a footprint is its storey count; that reading is
    #    the consumer's).
    buildings = []
    if args.buildings != "off" and polys:
        legend = json.loads(args.legend.read_text()) if args.legend else None
        rgb = np.asarray(work)
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2Lab).astype(np.float32)
        chroma = np.hypot(lab[..., 1] - 128.0, lab[..., 2] - 128.0)
        paper = float(np.median(chroma[(white > 0) & (content > 0)])) if (white & content).any() else 0.0

        paper_L = float(np.median(lab[..., 0][(white > 0) & (content > 0)])) if (white & content).any() else 0.0

        def material_of(hue: float, ch: float, dL: float):
            """The key's own word for this wash. A material names its colour with a word (COLOUR_WORDS -> broad hue band)
            or an exact 'hue_deg' range; the wash must exceed the key's min_chroma, else it is the key's 'untinted';
            'grey' is a wash with little chroma but darker than the paper. None without a legend, or when no entry fits."""
            if legend is None:
                return None
            entries = legend.get("materials", [])
            if ch < legend.get("min_chroma", 4.0):
                grey = next((e for e in entries if e.get("colour", "").lower() in COLOUR_WORDS and COLOUR_WORDS[e["colour"].lower()] is None), None)
                if grey is not None and dL < -legend.get("grey_min_darker", 8.0):
                    return grey["name"]
                return legend.get("untinted")
            for e in entries:
                band = e.get("hue_deg") or COLOUR_WORDS.get(e.get("colour", "").lower())
                if not band:
                    continue
                lo, hi = band
                if (lo <= hue <= hi) if lo <= hi else (hue >= lo or hue <= hi):
                    return e["name"]
            return None

        nreg, reg, rstats, rcent = cv2.connectedComponentsWithStats(enclosed, connectivity=4)
        block_cnts = [(j, c) for j, (c, _, _) in enumerate(polys)]
        block_area = [cv2.contourArea(c) for c, _, _ in polys]

        def region_at(t):
            """Enclosed-region label a token sits in: the majority label in a small window around its centre (the centre
            pixel itself is ink)."""
            b = t["bbox_xyxy"]; cx_, cy_ = int((b[0] + b[2]) / 2), int((b[1] + b[3]) / 2)
            r_ = reg[max(0, cy_ - 8):cy_ + 9, max(0, cx_ - 8):cx_ + 9]
            v = r_[r_ > 0]
            return int(np.bincount(v).argmax()) if v.size else 0

        tok_region: dict[int, list] = {}
        for t in tokens:
            tok_region.setdefault(region_at(t), []).append(t)
        word_re = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
        for i in range(1, nreg):
            a_ = rstats[i, cv2.CC_STAT_AREA]
            if a_ < args.building_min * area_box:
                continue
            cx_, cy_ = rcent[i]
            j = next((j_ for j_, c in block_cnts if cv2.pointPolygonTest(c, (float(cx_), float(cy_)), False) >= 0), None)
            if j is None or a_ > args.building_max_share * block_area[j]:
                continue
            comp = (reg == i).astype(np.uint8)
            if open_interior[comp > 0].mean() > 0.5:
                continue  # the open interior of a residential block recovered at its necks, not an outline on the plan
            comp = cv2.dilate(comp, k)  # back out to the drawn line (the white was measured inside the sealed ink)
            cnts_, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cnts_:
                continue
            c_ = cv2.approxPolyDP(max(cnts_, key=cv2.contourArea), args.simplify, True)
            if len(c_) < 3:
                continue
            m_ = reg == i
            ch = float(chroma[m_].mean() - paper)
            dL = float(lab[..., 0][m_].mean() - paper_L)
            col = rgb[m_].mean(0)
            hue = float(cv2.cvtColor(np.uint8([[col]]), cv2.COLOR_RGB2HSV)[0, 0, 0]) * 2.0
            inside_t = sorted(tok_region.get(i, []), key=lambda t: (t["bbox_xyxy"][1], t["bbox_xyxy"][0]))
            texts = [t["text"] for t in inside_t]
            numerals = [numeral(t) for t in inside_t if numeral(t) and not t.get("rotation")]
            words = [t["text"] for t in inside_t if word_re.search(t["text"])]
            bid = len(buildings)
            ring_ = [[round(float(p_[0][0]) / ws), round(float(p_[0][1]) / ws)] for p_ in c_]
            buildings.append({"type": "Feature", "id": bid,
                              "geometry": {"type": "Polygon", "coordinates": [ring_ + [ring_[0]]]},
                              "properties": {"sheet": stem, "building_id": f"{features[j]['properties']['block_id']}:bldg{bid}",
                                             "block_id": features[j]["properties"]["block_id"], "block_fid": j, "block_number": features[j]["properties"]["block_number"],
                                             "text_inside": texts, "numerals_inside": numerals, "words_inside": words, "floors": floors_of(numerals) if args.floors == "single-numeral-1-3" else None,
                                             "wash_rgb": [int(v) for v in col], "wash_chroma": round(ch, 1), "wash_lightness_delta": round(dL, 1), "hue_deg": round(hue), "material": material_of(hue, ch, dL),
                                             "area_source_px2": round(float(cv2.contourArea(c_)) / ws / ws), "centroid_source_px": [round(float(cx_) / ws), round(float(cy_) / ws)]}})
        for j, f_ in enumerate(features):
            f_["properties"]["n_enclosed"] = sum(1 for b in buildings if b["properties"]["block_fid"] == j)
        bfc = {"type": "FeatureCollection",
               "crs_note": "Coordinates are pixels on the source scan (origin top-left, y down); fim_georef.py writes <stem>_buildings_wgs84.geojson",
               "note": "enclosed outlines inside the traced blocks (building footprints, yards, courtyards — the plan's linework, not classified); "
                       "text_inside = OCR tokens whose centre lies inside, in reading order; numerals_inside / words_inside = the same split by regex; "
                       "floors = null unless --floors single-numeral-1-3 (Sanborn): then the single numeral inside when it reads 1 to 3 inclusive (1½ -> 1.5); a field for a person to fill otherwise; "
                       "wash_rgb / wash_chroma / wash_lightness_delta / hue_deg = the measured colour inside the outline relative to the paper; material = that colour looked up in the key given with --legend (colour words or calibrated hue ranges), else null; "
                       "block_id links to <stem>_blocks_px.geojson",
               "paper_chroma": round(paper, 1), "paper_lightness": round(paper_L, 1), "legend": str(args.legend) if args.legend else None,
               "source_image": doc["source_image"], "source_size": doc["source_size"], "from_run": str(run),
               "params": {"building_min_frac": args.building_min, "building_max_share": args.building_max_share, "floors": args.floors},
               "generated_utc": datetime.now(timezone.utc).isoformat(), "features": buildings}
        (out / f"{stem}_buildings_px.geojson").write_text(json.dumps(bfc, indent=1, ensure_ascii=False))
        mats = {}
        for b in buildings:
            mats[b["properties"]["material"]] = mats.get(b["properties"]["material"], 0) + 1
        floors_note = (f"{sum(1 for b in buildings if b['properties']['floors'] is not None)} with floors read from a single 1-3 numeral" if args.floors != "off" else "floors left null")
        key_note = ("; by the key: " + ", ".join(f"{v} {k}" for k, v in mats.items())) if legend else "; no --legend, colour recorded but not read"
        print(f"{len(buildings)} enclosed outlines inside blocks -> {out}/{stem}_buildings_px.geojson ({sum(1 for b in buildings if b['properties']['numerals_inside'])} with a numeral inside, "
              f"{floors_note}, {sum(1 for b in buildings if b['properties']['words_inside'])} with words; paper chroma {paper:.1f}{key_note})", flush=True)

    fc = {"type": "FeatureCollection",
          "crs_note": "Coordinates are pixels on the source scan (origin top-left, y down). Not georeferenced: apply the sheet's GCP transform to get geographic coordinates.",
          "source_image": doc["source_image"], "source_size": doc["source_size"], "from_run": str(run),
          "params": {"bold_stroke_px": args.bold_stroke, "number_reach_px": args.number_reach, "seal_px": args.seal, "neck_px": args.neck_px, "open_max": args.open_max,
                     "seed_px": args.seed_px, "lot_max_frac": args.lot_max, "open_px": args.open_px, "dark": args.dark, "min_area_frac": args.min_area, "max_area_frac": args.max_area,
                     "street_reach_work_px": args.street_reach},
          "street_seeds": "modern centrelines of the sheet's georeference" if street_segments_source_px is not None else "border and oversize regions only (sheet not georeferenced when traced)",
          "white_space": notes,
          "frontage_lines_added": frontage_lines, "manual_close_lines": manual_lines, "generated_utc": datetime.now(timezone.utc).isoformat(), "features": features}
    (out / f"{stem}_blocks_px.geojson").write_text(json.dumps(fc, indent=1))
    with open(out / f"{stem}_blocks.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["id", "block_number", "streets (side, distance)", "lot_numbers"]); w.writerows(rows)

    # overlay
    img = work.copy(); d = ImageDraw.Draw(img, "RGBA")
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26); f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        f = f2 = ImageFont.load_default()
    palette = [(220, 40, 40), (40, 120, 220), (30, 160, 60), (200, 120, 0), (140, 0, 200), (0, 150, 150)]
    for j, (cnt, block_no, near) in enumerate(polys):
        block_no = rows[j][1] if rows[j][1] else None
        col = palette[j % len(palette)]
        pts = [(int(p[0][0]), int(p[0][1])) for p in cnt]
        d.polygon(pts, outline=col + (255,), fill=col + (28,), width=4)
        m = cv2.moments(cnt); cx, cy = int(m["m10"] / max(m["m00"], 1)), int(m["m01"] / max(m["m00"], 1))
        d.text((cx - 12, cy - 14), f"#{j} {block_no or '?'}", fill=col + (255,), font=f)  # '*' = inferred from nearest bold number
        d.text((cx - 12, cy + 14), ", ".join(f"{s['name']}·{s['side']}" for s in near[:4]), fill=(0, 0, 0, 255), font=f2)
    for b in buildings:
        pts_ = [(int(x * ws), int(y * ws)) for x, y in b["geometry"]["coordinates"][0]]
        d.polygon(pts_, outline=(200, 0, 120, 230), width=2)
    for fl in frontage_lines:
        d.line([tuple(fl["line_work_px"][0]), tuple(fl["line_work_px"][1])], fill=(255, 0, 255, 255), width=5)
    for ml in manual_lines:
        d.line([tuple(ml["work_px"][0]), tuple(ml["work_px"][1])], fill=(255, 140, 0, 255), width=5)
    img.save(out / f"{stem}_blocks_overlay.jpg", quality=88)
    print(f"{len(features)} blocks -> {out}/{stem}_blocks_px.geojson (scan pixels, not a map), _blocks.csv, _blocks_overlay.jpg")
    for r in rows:
        print(f"  block #{r[0]:<3} number={r[1]!s:6} streets: {r[2] or '-'}   lots: {r[3][:60]}")
    return fc


def main() -> None:
    args = build_parser().parse_args()
    if args.neck_px is None:
        args.neck_px = 16 if args.georef else 0
    run = args.run.expanduser().resolve()
    tiles = next(run.glob("*_tiles.json"), None)
    if tiles is None:
        raise SystemExit(f"{run}: no <stem>_tiles.json (run fim_tile_ocr.py first)")
    stem = Path(json.loads(tiles.read_text())["source_image"]).stem
    # run log (scripts/fim_runlog.py): seeds, parameters, block / footprint counts, white-space notes, seconds
    params = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items() if k not in ("run", "output_dir")}
    with Stage(run, "blocks", sheet=stem, georef_seeded=bool(args.georef), neck_px=args.neck_px, params=params) as log:
        segs = None
        if args.georef:
            segs = segments_from_georef(run, stem)
            if segs is None:
                raise SystemExit(f"--georef: no {stem}_georef.json in {run} — run fim_georef.py first, or trace without --georef")
            print(f"street seeds: {len(segs)} modern centreline segments from {stem}_georef.json", flush=True)
            log.note(n_street_seed_segments=len(segs))
        fc = trace(args, segs)
        log.note(white_space=fc.get("white_space"), n_frontage_lines_added=len(fc.get("frontage_lines_added") or []),
                 n_manual_close_lines=len(fc.get("manual_close_lines") or []), **px_outputs_summary((args.output_dir or run), stem))


if __name__ == "__main__":
    main()
