#!/usr/bin/env python3
"""
Georeference a sheet from its OCR: street labels -> modern street centrelines -> affine transform -> GeoJSON.

City-agnostic. The reference layer is any GeoJSON of named centrelines in a metric CRS (make one for any bounding box
with scripts/fim_fetch_streets.py — OpenStreetMap or a municipal ArcGIS layer). No control points are clicked. Every
alphabetic token from a fim_tile_ocr.py run that names a street in that layer becomes a point-to-line constraint: the
label's centre (source-scan px) must land on that street's centreline. A coarse search over rotation (every 10 deg),
scale and translation seeds an ICP fit that alternates nearest-segment lookup with a weighted (Huber) least-squares
solve for a similarity transform (rotation x reflection, since scan y points down), then rejects labels farther than
max(--outlier-m, 3 x median) from their street — streets that moved since the plan was drawn — and solves a full
affine (paper shrink, scan skew) on the inliers. Labels along one street direction fix position across it, so ~10
labels on streets in two orientations determine 6 parameters with slack to spare.

Filtering, all data-driven: a word whose centre lies inside a traced block (fim_blocks.py) is a building label, not a
street name, and is skipped; a label that is only a street-type or direction word names no street and is skipped; a
label whose matched street meets none of the other matched streets (a water body or landmark whose name happens to be
a road elsewhere in the layer) is dropped; a label whose street has been renamed since the plan is mapped through
--alias, a JSON {label: ["NAME TYPE", ...]} kept per city/edition under configs/georef/. With --fuzzy a label one edit
away from a street name, or a 5+ letter fragment of one, also matches when exactly one street fits (OCR slips, period
spellings). After the fit, unmatched upper-case words that land on a modern centreline are listed as alias candidates.

The affine step (paper shrink, scan skew) is kept only if it is physically plausible (--max-shear-deg, --max-anisotropy);
labels on streets of one direction alone cannot fix the second scale, and then the similarity fit is kept instead.

A sheet with too few labels can borrow from its neighbours: --near RUN... takes georeferenced runs of adjacent sheets of
the same book (an atlas names them in its margins, "see sheet 4") and limits the translation search to one sheet around
their footprints, with their scale added to the seeds. With that prior four labels on two streets can place a sheet.

Intersections come from the centrelines themselves (vertices shared by differently named features) unless
--intersections supplies a layer. Names are matched after normalising the type word (Street/ST, Avenue/AVE,
Square/SQ ...), so an OSM "X Street" and a municipal STNAME "X" + STTYPE "ST" both become "X ST".

Outputs in <run>/  (<code> = the reference layer's EPSG):
  <stem>_georef.json               affine source px -> EPSG:<code> (+ inverse), per-label residuals, RMS, implied dpi
  <stem>_georef.points             QGIS Georeferencer GCP file (pixel <-> snapped centreline point) for the source image
  <stem>.jgw                       ESRI world file; copy next to <stem>.jpg and QGIS/GDAL read the scan in EPSG:<code>
  <stem>_blocks_epsg<code>.geojson fim_blocks.py polygons in the layer CRS  (needs <stem>_blocks_px.geojson in the run)
  <stem>_blocks_wgs84.geojson      same in WGS84 (standard GeoJSON)
  <stem>_tokens_wgs84.geojson      every kept OCR token as a WGS84 polygon with its text
  <stem>_areas_{epsg<code>,wgs84}.geojson   colour-wash areas, if fim_areas.py was run on the sheet
  <stem>_page_wgs84.geojson        footprint of the whole scan and of the tiled content box (also _page_epsg<code>)
  <stem>_street_names_wgs84.geojson  the street-name changes this sheet shows: labels renamed since the plan (--alias),
                                   respelled (--fuzzy), moved (fit outliers) or unmatched but lying on a modern centreline,
                                   each with the modern street's geometry on the sheet, the name on the plan, the plan
                                   year (--year) and the modern name — a log for linked data, merged across a book by fim_merge.py
  <stem>_georef_overlay.jpg        scan with modern centrelines/intersections back-projected on it — the visual check

    python3 scripts/fim_georef.py runs/<model>/<run> --streets data/modern/<city>_streets_epsg<code>.geojson \
        [--alias configs/georef/aliases_<city>_<year>.json]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fim_crs import CRS, parse_epsg  # noqa: E402
from fim_runlog import Stage, map_outputs_summary, rel, ring_centre, streets_provenance  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NAME_FIELDS = ["name", "NAME", "STNAME", "StreetName", "FULLNAME", "FULL_NAME", "ST_NAME", "STREET", "street", "STREETNAME", "ROADNAME", "RD_NAME", "LINEARNAME_FULL", "STRUCTURED_NAME_1", "FULL_STREET_NAME"]
TYPE_FIELDS = ["STTYPE", "ST_TYPE", "StreetType", "SUFFIX", "TYPE"]

TYPE_WORDS = {"ST": "ST", "STREET": "ST", "AVE": "AVE", "AV": "AVE", "AVENUE": "AVE", "SQ": "SQ", "SQUARE": "SQ", "ALLEY": "ALLEY", "ALY": "ALLEY", "LANE": "LANE", "LN": "LANE", "RD": "RD", "ROAD": "RD", "PL": "PL", "PLACE": "PL", "DR": "DR", "DRIVE": "DR", "BLVD": "BLVD", "BOULEVARD": "BLVD", "CRES": "CRES", "CRESCENT": "CRES", "TERR": "TERR", "TERRACE": "TERR", "CT": "CRT", "CRT": "CRT", "COURT": "CRT", "WAY": "WAY", "HWY": "HWY", "HIGHWAY": "HWY", "MEWS": "MEWS", "ROW": "ROW"}
DIRECTION_WORDS = {"N", "S", "E", "W", "NORTH", "SOUTH", "EAST", "WEST", "NE", "NW", "SE", "SW"}
# Type words that German/Dutch plans and OSM fuse onto the name ("Singerstraße", "Stock-im-Eisen-Platz"); the OCR reads
# them spaced, hyphenated or fused ("Singer-Strasse"), so a trailing word that ENDS in one of these is split off. Five letters
# or more only, so English names ending in -ring/-hof/-weg are left alone.
FUSED_TYPE_WORDS = {"STRASSE": "STRASSE", "STR": "STRASSE", "GASSE": "GASSE", "PLATZ": "PLATZ", "MARKT": "MARKT", "STEIG": "STEIG",
                    "ZEILE": "ZEILE", "ALLEE": "ALLEE", "BRUECKE": "BRUECKE", "BRUCKE": "BRUECKE", "PROMENADE": "PROMENADE",
                    "STRAAT": "STRAAT", "GRACHT": "GRACHT", "PLEIN": "PLEIN", "SINGEL": "SINGEL"}
TYPE_WORDS.update(FUSED_TYPE_WORDS)
_FUSED_SUFFIXES = sorted((k for k in FUSED_TYPE_WORDS if len(k) >= 5), key=len, reverse=True)


def fold(text: str) -> str:
    """ß -> ss and diacritics -> base letter, applied to labels AND layer names, so 'Singerstraße', 'SINGERSTRASSE' and the
    OCR's 'Singer-Strasse' compare equal, and 'Kärntner' matches whether the OCR kept the umlaut or not."""
    text = text.replace("ß", "ss").replace("ẞ", "SS")
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


# ----------------------------------------------------------------------------------------------------- geometry
SIDES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def side_of(bearing_deg: float) -> str:
    return SIDES[int(((bearing_deg + 22.5) % 360) // 45)]


def apply(A: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """A is 2x3 [a11 a12 tx; a21 a22 ty]; pts (n,2) source px -> (n,2) map."""
    return pts @ A[:, :2].T + A[:, 2]


def invert(A: np.ndarray) -> np.ndarray:
    Mi = np.linalg.inv(A[:, :2])
    return np.hstack([Mi, (-Mi @ A[:, 2])[:, None]])


def nearest_on_segments(p: np.ndarray, segs: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Nearest point to p on any of segs (m,2,2). Returns (point, unit normal of that segment, distance)."""
    a, b = segs[:, 0], segs[:, 1]
    ab = b - a
    L2 = np.maximum((ab**2).sum(1), 1e-9)
    u = np.clip(((p - a) * ab).sum(1) / L2, 0, 1)
    q = a + u[:, None] * ab
    d = np.linalg.norm(q - p, axis=1)
    i = int(d.argmin())
    tang = ab[i] / math.sqrt(L2[i])
    return q[i], np.array([-tang[1], tang[0]]), float(d[i])


def huber_w(r: np.ndarray, k: float) -> np.ndarray:
    a = np.abs(r)
    return np.where(a <= k, 1.0, k / np.maximum(a, 1e-9))


def solve_step(P: np.ndarray, Q: np.ndarray, Nrm: np.ndarray, w: np.ndarray, mode: str) -> np.ndarray:
    """Weighted least squares for point-to-line residuals n·(T(p) - q). Returns 2x3 affine."""
    if mode == "affine":  # theta = a11 a12 tx a21 a22 ty
        J = np.zeros((len(P), 6))
        J[:, 0] = Nrm[:, 0] * P[:, 0]
        J[:, 1] = Nrm[:, 0] * P[:, 1]
        J[:, 2] = Nrm[:, 0]
        J[:, 3] = Nrm[:, 1] * P[:, 0]
        J[:, 4] = Nrm[:, 1] * P[:, 1]
        J[:, 5] = Nrm[:, 1]
    else:  # similarity with the y flip of a scan: T(p) = [a b; b -a] p + t (rotation x reflection); theta = a b tx ty
        J = np.zeros((len(P), 4))
        J[:, 0] = Nrm[:, 0] * P[:, 0] - Nrm[:, 1] * P[:, 1]
        J[:, 1] = Nrm[:, 0] * P[:, 1] + Nrm[:, 1] * P[:, 0]
        J[:, 2] = Nrm[:, 0]
        J[:, 3] = Nrm[:, 1]
    rhs = (Nrm * Q).sum(1)
    sw = np.sqrt(w)[:, None]
    th, *_ = np.linalg.lstsq(J * sw, rhs * sw[:, 0], rcond=None)
    if mode == "affine":
        return th.reshape(2, 3)
    a, b, tx, ty = th
    return np.array([[a, b, tx], [b, -a, ty]])


def icp(P: np.ndarray, cand: list[np.ndarray], A0: np.ndarray, mode: str, iters: int = 60, huber_m: float = 6.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """P (n,2) label px; cand[i] segments (m,2,2) for label i. Returns (A, per-label distances, snapped points)."""
    A = A0.copy()
    for _ in range(iters):
        T = apply(A, P)
        Q, Nrm, d = [], [], []
        for i in range(len(P)):
            q, n, di = nearest_on_segments(T[i], cand[i])
            Q.append(q); Nrm.append(n); d.append(di)
        Q, Nrm, d = np.array(Q), np.array(Nrm), np.array(d)
        r = (Nrm * (T - Q)).sum(1)
        A_new = solve_step(P, Q, Nrm, huber_w(r, huber_m), mode)
        if np.abs(A_new - A).max() < 1e-7:
            A = A_new
            break
        A = A_new
    T = apply(A, P)
    out = [nearest_on_segments(T[i], cand[i]) for i in range(len(P))]
    return A, np.array([o[2] for o in out]), np.array([o[0] for o in out])


def label_direction(tok: dict, min_aspect: float = 2.0) -> float | None:
    """Direction of the text (deg, scan coordinates, y down, mod 180) or None if the word is too square to tell.
    A rotated-view polygon gives its long side; an upright box gives 0 (wide) or 90 (tall). Street names are printed
    along their street, so this is the street's direction on the sheet."""
    poly = tok.get("polygon")
    if poly:
        pts = np.array(poly, float)
        best, ang = 0.0, None
        for i in range(len(pts)):
            v = pts[(i + 1) % len(pts)] - pts[i]
            L = float(np.hypot(*v))
            if L > best:
                best, ang = L, math.degrees(math.atan2(v[1], v[0])) % 180
        short = min(np.hypot(*(pts[1] - pts[0])), np.hypot(*(pts[2] - pts[1])))
        return ang if short > 0 and best / short >= min_aspect else None
    x1, y1, x2, y2 = tok["bbox_xyxy"]
    w, h = x2 - x1, y2 - y1
    if w >= min_aspect * h:
        return 0.0
    if h >= min_aspect * w:
        return 90.0
    return None


def rotation_from_labels(A: np.ndarray, dirs: np.ndarray, tangents: np.ndarray, w: np.ndarray) -> float | None:
    """Rotation (deg) that lays each label's text direction along its snapped street segment: weighted median over the
    labels with a direction, taken near the current rotation of A (mod 180). None if fewer than 3 labels have one."""
    cur = math.degrees(math.atan2(A[1, 0], A[0, 0]))
    ok = ~np.isnan(dirs)
    if ok.sum() < 3:
        return None
    # scan direction d (y down) -> after the y flip F its map-angle is -d; the rotation must turn it onto the tangent
    tang_ang = np.degrees(np.arctan2(tangents[ok, 1], tangents[ok, 0]))
    rots = (tang_ang + dirs[ok] - cur + 90) % 180 - 90 + cur  # candidate within +-90 of the current rotation
    order = np.argsort(rots)
    cw = np.cumsum(w[ok][order])
    return float(rots[order][np.searchsorted(cw, cw[-1] / 2)])


def solve_fixed_rot(P: np.ndarray, Q: np.ndarray, Nrm: np.ndarray, w: np.ndarray, rot_deg: float) -> np.ndarray:
    """Weighted least squares for scale and translation with the rotation held: T(p) = s R F p + t (F = y flip)."""
    RF = similarity(1.0, rot_deg, np.zeros(2))[:, :2]
    base = P @ RF.T
    J = np.stack([(Nrm * base).sum(1), Nrm[:, 0], Nrm[:, 1]], axis=1)
    rhs = (Nrm * Q).sum(1)
    sw = np.sqrt(w)[:, None]
    sc, tx, ty = np.linalg.lstsq(J * sw, rhs * sw[:, 0], rcond=None)[0]
    return np.hstack([sc * RF, np.array([[tx], [ty]])])


def icp_label_rotation(P: np.ndarray, cand: list[np.ndarray], dirs: np.ndarray, A0: np.ndarray, iters: int = 60, huber_m: float = 6.0) -> tuple[np.ndarray, np.ndarray, np.ndarray, float | None]:
    """ICP like icp(), but the rotation comes from the labels' text directions against their snapped segments, and the
    solve is for scale + translation only. Falls back to the free similarity when too few labels have a direction.
    Returns (A, distances, snapped points, rotation used or None)."""
    A = A0.copy()
    rot_used = None
    for _ in range(iters):
        T = apply(A, P)
        Q, Nrm, d = [], [], []
        for i in range(len(P)):
            q, n, di = nearest_on_segments(T[i], cand[i])
            Q.append(q); Nrm.append(n); d.append(di)
        Q, Nrm, d = np.array(Q), np.array(Nrm), np.array(d)
        r = (Nrm * (T - Q)).sum(1)
        w = huber_w(r, huber_m)
        tang = np.stack([Nrm[:, 1], -Nrm[:, 0]], axis=1)  # segment tangent from its normal
        rot = rotation_from_labels(A, dirs, tang, w)
        if rot is None:
            return (*icp(P, cand, A0, "similarity", iters, huber_m), None)
        A_new = solve_fixed_rot(P, Q, Nrm, w, rot)
        rot_used = rot
        if np.abs(A_new - A).max() < 1e-7:
            A = A_new
            break
        A = A_new
    T = apply(A, P)
    out = [nearest_on_segments(T[i], cand[i]) for i in range(len(P))]
    return A, np.array([o[2] for o in out]), np.array([o[0] for o in out]), rot_used


def grid_cost(base: np.ndarray, grid: np.ndarray, cand: list[np.ndarray], k: float = 15.0) -> np.ndarray:
    """Huber cost for every translation in grid (G,2): label i lands at base[i] + grid. Vectorised over grid and segments."""
    total = np.zeros(len(grid))
    for i in range(len(base)):
        pts = base[i] + grid  # (G,2)
        a, b = cand[i][:, 0], cand[i][:, 1]
        ab = b - a
        L2 = np.maximum((ab**2).sum(1), 1e-9)
        u = np.clip(((pts[:, None, :] - a[None]) * ab[None]).sum(2) / L2[None], 0, 1)  # (G,m)
        q = a[None] + u[..., None] * ab[None]
        d = np.linalg.norm(q - pts[:, None, :], axis=2).min(1)
        total += np.where(d <= k, d * d, k * (2 * d - k))
    return total


def similarity(scale: float, rot_deg: float, t: np.ndarray, flip_y: bool = True) -> np.ndarray:
    """Source px (y down) -> map (y up): optional y flip, then rotate by rot_deg (CCW in map), scale, translate."""
    th = math.radians(rot_deg)
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    F = np.diag([1.0, -1.0 if flip_y else 1.0])
    M = scale * R @ F
    return np.hstack([M, t[:, None]])


# --------------------------------------------------------------------------------------------------------- data
def norm_label(text: str) -> tuple[str, str | None]:
    """'<NAME> SQUARE' -> ('<NAME>', 'SQ'); '<NAME> ST' -> ('<NAME>', 'ST'); a bare '<NAME>' -> ('<NAME>', None)."""
    words = [w for w in re.sub(r"[^A-Za-z' ]+", " ", fold(text)).upper().split() if w]
    if len(words) > 2 and words[-1] in DIRECTION_WORDS and words[-2] in TYPE_WORDS:  # "Burnside Rd E" -> Burnside Rd
        words = words[:-1]
    if not words:
        return "", None
    if words[-1] not in TYPE_WORDS:  # "SINGERSTRASSE" -> "SINGER", "STRASSE" (fused type word, see FUSED_TYPE_WORDS)
        for suf in _FUSED_SUFFIXES:
            if words[-1].endswith(suf) and len(words[-1]) - len(suf) >= 3:
                words = words[:-1] + [words[-1][: -len(suf)], suf]
                break
    typ = TYPE_WORDS.get(words[-1]) if len(words) > 1 else None
    name = " ".join(words[:-1] if typ else words)
    return name, typ


def canon(name: str, typ: str | None = None) -> str:
    """Canonical 'NAME TYPE': '<Name> Street' -> '<NAME> ST'; ('<Name>','ST') -> '<NAME> ST'; '<Name> Square' -> '<NAME> SQ'."""
    n, t = norm_label(name if typ is None else f"{name} {typ}")
    return f"{n} {t}" if t else n


def pick_field(props: dict, candidates: list[str], explicit: str | None) -> str | None:
    if explicit:
        if explicit not in props:
            raise SystemExit(f"field {explicit!r} not in the streets layer; it has {sorted(props)}")
        return explicit
    return next((c for c in candidates if c in props), None)


def load_streets(path: Path, name_field: str | None, type_field: str | None) -> tuple[dict[str, np.ndarray], int, dict]:
    """{ '<NAME> ST': segments (m,2,2) } by canonical name, the layer's EPSG, and which fields were used."""
    gj = json.loads(path.read_text())
    epsg = gj.get("epsg") or parse_epsg(gj.get("crs"))
    feats = gj["features"]
    props0 = next((f["properties"] for f in feats if f.get("properties")), {})
    nf = pick_field(props0, NAME_FIELDS, name_field)
    if nf is None:
        raise SystemExit(f"cannot find a street-name field in {path} (looked for {NAME_FIELDS}); pass --name-field")
    tf = pick_field(props0, TYPE_FIELDS, type_field) if (type_field or nf.upper() in ("STNAME", "ST_NAME")) else None
    segs: dict[str, list] = {}
    for f in feats:
        p = f.get("properties") or {}
        name = (p.get(nf) or "").strip()
        if not name or f.get("geometry") is None:
            continue
        key = canon(name, (p.get(tf) or "").strip() if tf else None)
        if not key.strip():  # a name that is only a type word or punctuation names nothing
            continue
        g = f["geometry"]
        parts = [g["coordinates"]] if g["type"] == "LineString" else (g["coordinates"] if g["type"] == "MultiLineString" else [])
        for part in parts:
            c = np.array(part, float)[:, :2]
            if len(c) >= 2:
                segs.setdefault(key, []).extend(np.stack([c[:-1], c[1:]], axis=1))
    return {k: np.array(v) for k, v in segs.items()}, epsg, {"name_field": nf, "type_field": tf}


def derive_intersections(streets: dict[str, np.ndarray], snap_m: float = 0.5) -> list[dict]:
    """Vertices shared by two or more differently named features -> [{'names': (A, B, ...), 'xy': (x, y)}]."""
    at: dict[tuple, dict] = {}
    for key, segs in streets.items():
        for v in np.unique(segs.reshape(-1, 2), axis=0):
            g = (round(v[0] / snap_m), round(v[1] / snap_m))
            d = at.setdefault(g, {"names": set(), "xy": v})
            d["names"].add(key)
    return [{"names": tuple(sorted(d["names"])), "xy": d["xy"]} for d in at.values() if len(d["names"]) >= 2]


def load_intersections(path: Path) -> list[dict]:
    """A supplied intersections layer (points with two street-name fields) -> the same shape as derive_intersections."""
    gj = json.loads(path.read_text())
    out = []
    for f in gj["features"]:
        p = f["properties"]
        n1 = p.get("StreetName1") or p.get("STREET1") or p.get("name1") or ""
        n2 = p.get("StreetName2") or p.get("STREET2") or p.get("name2") or ""
        if not n1 or not n2:
            continue
        c = f["geometry"]["coordinates"]
        xy = np.array(c[0] if f["geometry"]["type"] == "MultiPoint" else c, float)
        out.append({"names": (canon(n1), canon(n2)), "xy": xy})
    return out


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _base(k: str) -> str:
    """'DOUGLAS ST' -> 'DOUGLAS'; a key without a type word is returned as is."""
    return k.rsplit(" ", 1)[0] if k.rsplit(" ", 1)[-1] in TYPE_WORDS.values() else k


SPELL_FOLD = True  # --spelling historic (default) | exact


def spell_key(name: str) -> str:
    """Compare-key for a street name: orthographic equivalences a plan and today's layer may spell differently, applied to
    BOTH sides so the comparison is symmetric. Language-level, not a city fact: German 1901 reform TH->T (Rothenthurm ->
    Rotenturm, Karnthner -> Karntner), PH->F (Josephs -> Josefs), DT->T (Stadt/Stat), hard C->K (Carl -> Karl,
    Concordia -> Konkordia), non-initial Y->I (Freyung -> Freiung, Mayer -> Maier). English names pass through unchanged
    in effect (SEYMOUR and SEIMOUR would compare equal, which no layer needs to tell apart). Off with --spelling exact."""
    if not SPELL_FOLD:
        return name
    s = name.upper().replace("TH", "T").replace("PH", "F").replace("DT", "T")
    s = re.sub(r"C(?=[AOULR])", "K", s)
    s = re.sub(r"(?<=[A-Z])Y", "I", s)
    return s


def fuzzy_streets(label: str, streets: dict[str, np.ndarray], aliases: dict[str, list[str]]) -> tuple[list[str], str | None]:
    """A 6+ letter label one edit away from a street or alias name (two edits for names of 9+ letters), or a 5+ letter
    prefix/suffix of one missing at most two letters ('OUGLAS', 'DOUGL' -> DOUGLAS; 'BANCHARD' -> the BLANCHARD alias),
    when exactly ONE name fits.
    Returns (street keys, the name it was taken for) or ([], None)."""
    name, typ = norm_label(label)
    if len(name) < 5 or name in TYPE_WORDS or name in DIRECTION_WORDS:
        return [], None
    pool: dict[str, str] = {}  # compare-name (spelling-folded) -> string to look up with match_streets
    for k in streets:
        b = _base(k)
        if len(b) >= 5:
            pool.setdefault(spell_key(b), b)
    for k in aliases:
        b = norm_label(k)[0]
        if len(b) >= 5:
            pool[spell_key(b)] = k
    name = spell_key(name)
    cands = set()
    for c in pool:
        if c == name:
            continue
        if (c.startswith(name) or c.endswith(name)) and len(c) - len(name) <= 2:  # a fragment: OUGLAS, DOUGL -> DOUGLAS (not BRICK -> REDBRICK)
            cands.add(c)
        elif len(name) >= 6 and abs(len(c) - len(name)) <= 2 and levenshtein(name, c) <= (2 if min(len(c), len(name)) >= 9 else 1):
            cands.add(c)  # a slip: BURNETT -> BURDETT, PENWELL -> PENWILL; five-letter words (STONE/STORE) are too easy to confuse
    if len(cands) != 1:
        return [], None
    c = cands.pop()
    keys = match_streets(pool[c] + (f" {typ}" if typ and spell_key(pool[c]) == c else ""), streets, aliases)
    return keys, pool[c]


def match_streets(label: str, streets: dict[str, np.ndarray], aliases: dict[str, list[str]]) -> list[str]:
    if label.upper().strip() in aliases:
        return [k for k in aliases[label.upper().strip()] if k in streets]
    name, typ = norm_label(label)
    if not name or (typ is None and (name in TYPE_WORDS or name in DIRECTION_WORDS)) or len(name) < 3:  # a bare type word ('ALLEY', 'AVE', 'ST') names no street; '<NAME> ALLEY' does
        return []
    base = lambda k: k.rsplit(" ", 1)[0] if k.rsplit(" ", 1)[-1] in TYPE_WORDS.values() else k
    key = spell_key(name)
    hits = [k for k in streets if spell_key(base(k)) == key]
    # the layer may prefix the direction the plan suffixes ("West Cordova Street" vs "CORDOVA ST. WEST") or the plan
    # may omit it: also accept the layer name without its leading direction word; when the plan gives a direction,
    # keep only the layer streets with that direction (if any have one)
    hits += [k for k in streets if k not in hits and (lambda b: len(b) > 1 and b[0] in DIRECTION_WORDS and spell_key(" ".join(b[1:])) == key)(base(k).split())]
    words = [w for w in re.sub(r"[^A-Za-z' ]+", " ", label).upper().split() if w]
    want = words[-1] if len(words) > 2 and words[-1] in DIRECTION_WORDS else None
    if want:
        same = [k for k in hits if k.split()[0] in (want, want[0])]
        hits = same or hits
    if typ:
        typed = [k for k in hits if k.endswith(" " + typ)]
        if typed:
            return typed
    return hits


# --------------------------------------------------------------------------------------------------------- blocks
def load_block_rings(run: Path, stem: str) -> list[np.ndarray]:
    """Outer rings of the blocks fim_blocks.py traced for a sheet (<run>/<stem>_blocks_px.geojson, beside the tiles JSON),
    as float32 (n,1,2) arrays in source-scan px, ready for cv2.pointPolygonTest. [] when the tracer has not run."""
    path = run / f"{stem}_blocks_px.geojson"
    if not path.exists() and (run / f"{stem}_blocks.geojson").exists():
        path = run / f"{stem}_blocks.geojson"  # pre-2026-09-14 name
    rings: list[np.ndarray] = []
    if path.exists():
        for f in json.loads(path.read_text())["features"]:
            g = f["geometry"]
            polys = [g["coordinates"]] if g["type"] == "Polygon" else (g["coordinates"] if g["type"] == "MultiPolygon" else [])
            for poly in polys:
                rings.append(np.array(poly[0], np.float32).reshape(-1, 1, 2))
    return rings


def block_depth(block_rings: list[np.ndarray], cx: float, cy: float) -> float:
    """Signed distance (source px) from a point to the nearest traced block edge: positive = inside a block."""
    return max((cv2.pointPolygonTest(r, (float(cx), float(cy)), True) for r in block_rings), default=-1e9)


def street_candidates(tokens: list[dict], block_rings: list[np.ndarray]) -> list[dict]:
    """The tokens that can be street labels: those whose centre is NOT inside a traced block.

    Street names are printed in the street corridors; business and building labels inside the blocks ("LIME / STORE" on a
    lot is not Store St), often right along the lot frontage, so no depth margin is asked for. Blocks are under-traced
    rather than over-traced (a block polygon follows the lot lines, and the street label sits half a street away), so a
    real street label is almost never inside one. Every token is stamped in place with in_block (bool) and in_block_depth_px (signed, positive = inside), so a
    caller may also keep the full list and filter on the flag. With no rings, nothing is flagged and all tokens are returned."""
    out = []
    for t in tokens:
        x1, y1, x2, y2 = t["bbox_xyxy_source"]
        depth = block_depth(block_rings, (x1 + x2) / 2, (y1 + y2) / 2) if block_rings else -1e9
        t["in_block_depth_px"] = None if not block_rings else round(float(depth))
        t["in_block"] = bool(block_rings) and depth > 0
        if not t["in_block"]:
            out.append(t)
    return out


# --------------------------------------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="fim_tile_ocr.py output dir (needs <stem>_tiles.json; uses <stem>_blocks_px.geojson if present)")
    ap.add_argument("--streets", type=Path, required=True, help="named centrelines GeoJSON in a metric CRS with a 'crs' member (make one with scripts/fim_fetch_streets.py)")
    ap.add_argument("--epsg", type=int, default=None, help="CRS of --streets if the file has no crs member")
    ap.add_argument("--name-field", default=None, help="property holding the street name (auto: name, STNAME, StreetName, FULLNAME, ...)")
    ap.add_argument("--type-field", default=None, help="property holding a separate street type (auto: STTYPE when the name field is STNAME)")
    ap.add_argument("--intersections", type=Path, default=None, help="optional intersections GeoJSON (points with StreetName1/StreetName2); default: derived from the centrelines' shared vertices")
    ap.add_argument("--alias", type=Path, default=None, help="JSON {label: ['NAME TYPE', ...]} for streets renamed since the plan (configs/georef/aliases_<city>_<year>.json)")
    ap.add_argument("--scales", default=None, help="m/px seeds for the coarse search. Default: derived from the sheet's own 'Scale N feet to 1 inch' statement if OCR read one (200-400 dpi), else a wide log-spaced 0.03-0.5 (20-600 ft/in at ~300 dpi)")
    ap.add_argument("--rotations", default="0:360:10", help="deg seeds: list '0,90,180' or range 'start:stop:step' (default 0:360:10 — sheets are rarely north-up)")
    ap.add_argument("--radius-m", type=float, default=600.0, help="minimum candidate radius in metres around where the named streets meet (default 600; grows automatically to 0.7 x sheet diagonal x largest scale seed)")
    ap.add_argument("--outlier-px", type=float, default=60.0, help="outlier floor in SHEET pixels (default 60 — about a label's text height): on a 50 ft/in sheet that is ~3 m, on a 500 ft/in key plan ~30 m; the floor is the larger of this and --outlier-m")
    ap.add_argument("--outlier-m", type=float, default=12.0, help="after the similarity fit, labels farther than max(this, 3 x median) from their street are outliers — streets moved since the plan — and are excluded from the final fit (default 12)")
    ap.add_argument("--grid-m", type=float, default=25.0, help="translation search step in metres (default 25)")
    ap.add_argument("--min-labels", type=int, default=6, help="refuse to fit with fewer matched labels (default 6; 4 is workable with --near)")
    ap.add_argument("--lonely-m", type=float, default=300.0, help="a matched label whose modern street lies farther than this from every other matched street is dropped (default 300 m: a landmark or water body whose name is a road elsewhere in the layer)")
    ap.add_argument("--spelling", choices=["historic", "exact"], default="historic", help="'historic' (default): street names are compared after orthographic folds a plan and today's layer may differ by (TH->T, PH->F, DT->T, hard C->K, Y->I: Rothenthurm/Rotenturm, Carl/Karl, Freyung/Freiung), applied to both sides. 'exact': letters must match")
    ap.add_argument("--fuzzy", action="store_true", help="also accept a 6+ letter label one edit away from a street or alias name (two edits for 9+ letters), or a 5+ letter prefix/suffix of one missing at most two letters, when exactly one name fits: OCR slips and period spellings (BLANCHARD -> Blanshard, OUGLAS -> Douglas). Such labels are marked 'fuzzy' in the outputs and go through the same outlier test")
    ap.add_argument("--near", nargs="+", type=Path, default=None, metavar="RUN", help="georeferenced runs of neighbouring sheets of the same book (same --streets CRS): this sheet must lie within one sheet of their footprints, so the translation search is limited to that window and their scale joins the seeds; lets a sheet with few labels be placed")
    ap.add_argument("--rotation", choices=["labels", "free"], default="labels", help="'labels' (default): the sheet's rotation is set by the text direction of the street labels against their modern streets (a name is printed along its street; wide box = along x, tall box = along y, rotated views give the angle), and the labels' positions fix only scale and translation; a position-only fit is run as well and wins only if it places at least half again as many labels (the text direction is coarse on sheets whose streets run diagonally). 'free': rotation is fitted from the positions only (used automatically when fewer than 3 labels have a readable direction)")
    ap.add_argument("--year", type=int, default=None, help="year of the plan, recorded in <stem>_street_names_wgs84.geojson (default: a year in the --alias file name, else unknown)")
    ap.add_argument("--max-shear-deg", type=float, default=2.0, help="keep the affine fit only if its shear is below this (default 2 deg) ...")
    ap.add_argument("--max-anisotropy", type=float, default=0.04, help="... and its x/y scale ratio is within this of 1 (default 0.04). Paper shrink and scanner skew are far smaller; beyond these the labels constrain only one direction and the similarity fit is kept, noted as affine_rejected in <stem>_georef.json")
    ap.add_argument("--huber-m", type=float, default=6.0, help="Huber threshold in metres for the ICP weights (default 6 — about half a street width)")
    ap.add_argument("--retrace", choices=["seeded", "keep"], default="seeded", help="'seeded' (default): once the sheet is placed, trace the blocks again with fim_blocks.py using the modern centrelines as street seeds (its --georef mode), which recovers residential blocks whose dashed frontage lines let the interior leak into the street; <stem>_blocks_px.geojson/.csv/_overlay.jpg are rewritten. 'keep': use the run's existing <stem>_blocks_px.geojson as it is")
    ap.add_argument("--neck-px", type=int, default=16, help="fim_blocks.py --neck-px for the seeded re-trace (default 16 work px; keep it under half the narrowest street of the plan in work px)")
    ap.add_argument("--floors", choices=["off", "single-numeral-1-3"], default="off", help="fim_blocks.py --floors for the re-trace: 'off' (default, Goad: a person fills 'floors') or 'single-numeral-1-3' (Sanborn: the single 1-3 numeral inside a footprint is its floors)")
    ap.add_argument("--legend", type=Path, default=None, help="fim_blocks.py --legend for the re-trace: the plan's colour key as a config (configs/legend/goad_sanborn_default.json for Goad and Sanborn plans); without it the footprints' colour is recorded but not read")
    ap.add_argument("--lots", choices=["numbered", "none"], default="numbered", help="lot convention of the plan. 'numbered' (default; North American fire insurance plans): a traced polygon is a block only if it holds a bold block numeral or at least two lot numbers, so building outlines and fragments are rejected. 'none' (plans without lot subdivisions or block numbers, e.g. a European city plan): no numeral test at all — every traced polygon that passes the shape and street tests is a block, block_number is null and the numerals inside go to numbers_inside")
    ap.add_argument("--block-street-reach-m", type=float, default=16.0, help="a modern centreline within this many metres of a block polygon's edge counts as bounding it (default 16: half a 66 ft street plus fit error)")
    ap.add_argument("--overlay-px", type=int, default=2400, help="long edge of the overlay JPEG (default 2400)")
    args = ap.parse_args()
    args.scales_given = args.scales is not None
    args.scales = args.scales or "0.03,0.045,0.065,0.1,0.15,0.22,0.33,0.5,0.7"  # 20 ft/in .. 800 ft/in at ~300 dpi

    run = args.run.expanduser().resolve()
    tiles_path = next(run.glob("*_tiles.json"), None)
    if tiles_path is None:
        raise SystemExit(f"{run}: no <stem>_tiles.json (run fim_tile_ocr.py first)")
    stem = tiles_path.name[: -len("_tiles.json")]
    with Stage(run, "georef", sheet=stem) as rlog:
        georef_sheet(args, run, tiles_path, stem, rlog)


def georef_sheet(args: argparse.Namespace, run: Path, tiles_path: Path, stem: str, rlog: Stage) -> None:
    """Steps 0-5 of the module docstring for one sheet. `rlog` is the run-log record (scripts/fim_runlog.py). Its fields:
    the street layer and its provenance (source, WGS84 box, place names, area), alias file and entry count, --fuzzy, --near,
    --min-labels; n_matched (labels that went into the fit), n_matched_plain (matched by name alone: no alias entry, no
    fuzzy match — whether the sheet places without any per-city configuration), n_matched_alias, n_matched_fuzzy,
    min_labels_met_plain; the fit (transform, RMS, scale, rotation, inliers, outliers); output counts; laps_s per step;
    status placed | refused_min_labels | error."""
    doc = json.loads(tiles_path.read_text())
    global SPELL_FOLD
    SPELL_FOLD = args.spelling == "historic"
    streets, epsg, fields = load_streets(args.streets, args.name_field, args.type_field)
    epsg = args.epsg or epsg
    if not epsg:
        raise SystemExit(f"{args.streets} has no crs member; pass --epsg")
    crs = CRS(epsg)
    inter = load_intersections(args.intersections) if args.intersections else derive_intersections(streets)
    print(f"streets: {len(streets)} names, {sum(len(v) for v in streets.values())} segments, {crs.name()} (EPSG:{epsg}), name field {fields['name_field']!r}" + (f" + type field {fields['type_field']!r}" if fields["type_field"] else "") + f"; {len(inter)} intersections ({'supplied' if args.intersections else 'derived from shared vertices'})")
    aliases: dict[str, list[str]] = {}
    if args.alias:
        aliases = {k.upper(): [canon(v) for v in vs] for k, vs in json.loads(args.alias.read_text()).items() if not k.startswith("_")}
    rlog.note(streets_file=rel(args.streets), streets=streets_provenance(args.streets), epsg=epsg, crs=f"EPSG:{epsg} ({crs.name()})", streets_fields=fields,
             n_streets_names=len(streets), n_streets_segments=sum(len(v) for v in streets.values()), n_intersections=len(inter),
             intersections="supplied" if args.intersections else "derived from centreline vertices",
             alias_file=rel(args.alias) if args.alias else None, n_alias_entries=len(aliases), fuzzy=bool(args.fuzzy),
             near=[rel(r) for r in args.near] if args.near else None, n_near=len(args.near or []), min_labels=args.min_labels, lots=args.lots,
             spelling=args.spelling, rotation_mode=args.rotation, year=args.year, retrace=args.retrace, scales_given=args.scales_given)
    rlog.lap("load")

    # 0. the traced blocks, if fim_blocks.py ran on this sheet. Street names are printed in the street corridors, business
    #    and building labels inside the blocks ("LIME / STORE" on a lot is not Store St). A word whose centre lies inside
    #    a traced block is a building label and is never a fit constraint. Blocks are under-traced rather than over-traced
    #    (a missed block costs nothing here; a block merged across a narrow street is rare).
    #    (load_block_rings / street_candidates above are importable by other scripts that need the same split)
    block_rings = load_block_rings(run, stem)

    # 1. labels: kept tokens (not duplicates/fragments/conflicts) with letters, that name a modern street, outside the blocks
    tokens = [t for t in doc["tokens"] if t.get("dup_of") is None and not t.get("fragment") and not t.get("conflict")]
    if args.lots == "none" and block_rings:
        # without lot numbers or block numerals nothing tells a traced block from a compound or a water body before the
        # fit, so a word inside a traced polygon may well be the name of the street the polygon spans: keep every label
        print(f"--lots none: the {len(block_rings)} traced polygons are not used to set street labels aside as building labels")
        block_rings = []
    street_candidates(tokens, block_rings)  # stamps in_block / in_block_depth_px on every token
    labels, P, cand, skipped, building = [], [], [], [], []
    n_alpha = 0
    for t in tokens:
        if not re.search(r"[A-Za-z]{3,}", t["text"]):
            continue
        n_alpha += 1
        keys = match_streets(t["text"], streets, aliases)
        via = None
        if not keys and args.fuzzy:
            keys, via = fuzzy_streets(t["text"], streets, aliases)
        x1, y1, x2, y2 = t["bbox_xyxy_source"]
        if not keys:
            skipped.append(t["text"])
            continue
        if t["in_block"]:  # centre inside a traced block: a building label
            building.append({"text": t["text"], "modern": keys, "px": [(x1 + x2) / 2, (y1 + y2) / 2], "bbox_source": [x1, y1, x2, y2], "depth_px": t["in_block_depth_px"]})
            continue
        labels.append({"text": t["text"], "id": t.get("id"), "rotation_view": t.get("rotation", 0), "modern": keys, "fuzzy": via, "alias": t["text"].upper().strip() in aliases,
                       "px": [(x1 + x2) / 2, (y1 + y2) / 2], "bbox_source": [x1, y1, x2, y2], "text_direction_deg": label_direction(t)})
        P.append(labels[-1]["px"])
        cand.append(np.concatenate([streets[k] for k in keys]))
    if building:
        print(f"inside a traced block (building labels that happen to spell a street name; not used): " + ", ".join(f"{b['text']} ({b['depth_px']} px deep)" for b in building))
    elif not block_rings:
        print("no traced blocks in this run: labels inside blocks cannot be told from street names (run fim_blocks.py first)")
    if args.fuzzy:
        fz = [l for l in labels if l["fuzzy"]]
        print(f"fuzzy: {len(fz)} labels taken for a street name they nearly spell: " + ", ".join(f"{l['text']}~{l['fuzzy']}" for l in fz) if fz else "fuzzy: no near-miss labels")
    # the streets named on one sheet lie near each other: drop labels whose modern street is farther than --lonely-m from
    # every other matched street (a water body or landmark whose name is a road elsewhere in the layer). Until 2026-09-17
    # this asked for a shared intersection vertex instead, which on a plan with an irregular street net dropped 15
    # real labels whose neighbours the OCR had not read.
    names_of = lambda l: set(l["modern"])
    all_keys = sorted(set().union(*(names_of(l) for l in labels))) if labels else []
    gap: dict[tuple, float] = {}
    for a in all_keys:
        va = streets[a].reshape(-1, 2)
        va = va[:: max(1, len(va) // 60)]
        for b in all_keys:
            if a >= b:
                continue
            gap[(a, b)] = gap[(b, a)] = min(nearest_on_segments(v, streets[b])[2] for v in va) if len(va) else float("inf")
    def nearest_other(l):
        others = [k for k in all_keys if k not in names_of(l)]
        return min((gap[(a, b)] for a in names_of(l) for b in others), default=0.0)
    lonely = [l for l in labels if nearest_other(l) > args.lonely_m]
    if lonely:
        print(f"dropped (street farther than {args.lonely_m:.0f} m from every other named street): {[l['text'] for l in lonely]}")
        skipped += [l["text"] for l in lonely]
        keep = [i for i, l in enumerate(labels) if l not in lonely]
        labels, P, cand = [labels[i] for i in keep], [P[i] for i in keep], [cand[i] for i in keep]
    P = np.array(P, float)
    print(f"{len(labels)} street labels matched: " + ", ".join(f"{l['text']}{'~' if l.get('fuzzy') else ''}->{'/'.join(l['modern'])}" for l in labels))
    print(f"{len(skipped)} alphabetic tokens not matched to a street: {sorted(set(skipped))}")
    n_plain = sum(1 for l in labels if not l["alias"] and not l["fuzzy"])
    rlog.note(n_tokens_kept=len(tokens), n_alpha_tokens=n_alpha, n_matched=len(labels), n_matched_plain=n_plain,
             n_matched_alias=sum(1 for l in labels if l["alias"]), n_matched_fuzzy=sum(1 for l in labels if l["fuzzy"]),
             n_distinct_streets=len({k for l in labels for k in l["modern"]}), n_building_labels=len(building), n_lonely_dropped=len(lonely),
             n_unmatched_alpha=len(set(skipped)), min_labels_met=len(labels) >= args.min_labels, min_labels_met_plain=n_plain >= args.min_labels)
    rlog.lap("match")
    if len(labels) < args.min_labels:
        rlog.note(status="refused_min_labels")
        raise SystemExit(f"only {len(labels)} labels matched (< --min-labels {args.min_labels})")

    # 2. where do the named streets meet? centre + radius for candidate segments and the translation search
    #    A seed is a vertex where two matched streets with DIFFERENT stems meet: 'HILLSBOROUGH AVE' meeting
    #    'WEST HILLSBOROUGH AVE' is one avenue changing its prefix, not two streets (Tampa 1884: 13 of 27 seeds were such
    #    self-junctions along a 30 km avenue and pulled the median 5.9 km off the sheet). The centre is then the densest
    #    cluster of seeds — the spot within one sheet's reach of which the most distinct matched streets meet — not the
    #    median of all seeds, which a long arterial or a generic name matched county-wide drags away from the sheet.
    matched = {k for l in labels for k in l["modern"]}
    shown: dict[str, str] = {}  # spell-folded stem -> the layer's own spelling, for the printout
    def name_stem(k: str) -> str:  # not 'stem': that is the sheet's file stem, used throughout main()
        words = [w for i, w in enumerate(_base(k).split()) if not (i == 0 and w in DIRECTION_WORDS)]
        key = spell_key(" ".join(words))
        shown.setdefault(key, " ".join(words))
        return key
    seeds, seed_stems = [], []
    for x in inter:
        stems = {name_stem(k) for k in set(x["names"]) & matched}
        if len(stems) >= 2:
            seeds.append(x["xy"]); seed_stems.append(stems)
    sheet_diag_px = math.hypot(doc["source_size"]["w"], doc["source_size"]["h"])
    scales_pre = [float(v) for v in args.scales.split(",")]
    radius = max(args.radius_m, 0.7 * sheet_diag_px * max(scales_pre))
    if seeds:
        seeds = np.array(seeds, float)
        reach = radius / 2  # about one sheet at the largest scale seed
        best_i, best_key = 0, (-1, -1)
        for i, s in enumerate(seeds):
            near = np.linalg.norm(seeds - s, axis=1) <= reach
            key = (len(set().union(*(seed_stems[j] for j in np.flatnonzero(near)))), int(near.sum()))
            if key > best_key:
                best_i, best_key = i, key
        near = np.linalg.norm(seeds - seeds[best_i], axis=1) <= reach
        centre = np.median(seeds[near], axis=0)
        seeds = seeds[near]  # the translation window below is clipped to the seeds' extent: the cluster's, not the county's
        cluster_names = sorted(shown[k] for k in set().union(*(seed_stems[j] for j in np.flatnonzero(near))))
        print(f"seed centre: {len(seeds)} intersections of two matched streets; densest cluster holds {int(near.sum())} of them within {reach:.0f} m, "
              f"where {best_key[0]} distinct streets meet ({', '.join(cluster_names)}); {int((~near).sum())} seeds elsewhere ignored")
    else:  # fall back to the matched streets' own extent
        seeds = np.array([s.reshape(-1, 2).mean(0) for k, s in streets.items() if k in matched], float)
        centre = np.median(seeds, axis=0)
        print(f"seed centre: no intersection of two matched streets in the layer; using the median of the {len(seeds)} matched streets' centres")
    # neighbouring sheets already placed: this sheet lies within one sheet of their footprints (their scale, since a book
    # is drawn at one scale) — a far tighter window than 'somewhere around the matched streets'
    near_win, near_scale = None, None
    if args.near:
        corners, near_scales = [], []
        for r in args.near:
            gpath = next(Path(r).glob("*_georef.json"), None)
            if gpath is None:
                raise SystemExit(f"--near {r}: no *_georef.json there (georeference that sheet first)")
            g = json.loads(gpath.read_text())
            if int(g.get("epsg") or 0) != int(epsg):
                raise SystemExit(f"--near {r}: fitted in EPSG:{g.get('epsg')}, but this layer is EPSG:{epsg}")
            corners += g["page_corners_map"]["content"]
            near_scales.append((g["scale_m_per_px"]["x"] + g["scale_m_per_px"]["y"]) / 2)
        corners = np.array(corners, float)
        near_scale = float(np.median(near_scales))
        pad = np.array([doc["source_size"]["w"], doc["source_size"]["h"]], float) * near_scale
        near_win = (corners.min(0) - pad, corners.max(0) + pad)
        centre = (near_win[0] + near_win[1]) / 2
        radius = max(args.radius_m, float(np.linalg.norm(near_win[1] - near_win[0]) / 2))
        print(f"--near: {len(args.near)} placed neighbour(s) at {near_scale:.4f} m/px; this sheet is searched within one sheet of their footprints: "
              f"x {near_win[0][0]:.0f}..{near_win[1][0]:.0f}, y {near_win[0][1]:.0f}..{near_win[1][1]:.0f} m (EPSG:{epsg}), candidate radius {radius:.0f} m")
    else:
        print(f"candidate radius {radius:.0f} m around where the named streets meet (sheet diagonal {sheet_diag_px:.0f} px x largest scale seed {max(scales_pre)} m/px)")
    keep_labels, keep_P, keep_cand, dropped = [], [], [], []
    for l, p, c in zip(labels, P, cand):
        mid = c.mean(1)
        c = c[np.linalg.norm(mid - centre, axis=1) <= radius]
        if len(c):
            keep_labels.append(l); keep_P.append(p); keep_cand.append(c)
        else:
            dropped.append(l["text"])
    labels, P, cand = keep_labels, np.array(keep_P, float), keep_cand
    if dropped:
        print(f"dropped (no segment of that street within {radius:.0f} m of the sheet's streets): {dropped}")
    if len(labels) < args.min_labels:
        rlog.note(status="refused_min_labels", n_dropped_far=len(dropped), n_matched_in_reach=len(labels))
        raise SystemExit(f"only {len(labels)} labels left (< --min-labels {args.min_labels})")

    # 3. coarse search: rotation x scale x translation grid
    sheet_diag_px = math.hypot(doc["source_size"]["w"], doc["source_size"]["h"])
    if ":" in args.rotations:
        r0, r1, rs = (float(v) for v in args.rotations.split(":"))
        rots = list(np.arange(r0, r1, rs))
    else:
        rots = [float(r) for r in args.rotations.split(",")]
    scales = [float(v) for v in args.scales.split(",")]
    # the sheet usually states its own scale ("Scale 100 Feet to 1 Inch", "SCALE 50 FT = 1INCH"); with a plausible scan
    # resolution (200-400 dpi) that gives far better seeds than the default list, and lets small-scale key plans fit
    # Candidates: "SCALE:500" / "SCALE : 500 FEET = 1 INCH" (rank 0), "500 FEET = 1 INCH" (rank 1), "SHEETS 50 FEET = 1 INCH"
    # (rank 2 — a key plan quotes the OTHER sheets' scales). OCR splits and garbles these, so collect all and take the best rank's mode.
    found: list[tuple[int, int, str]] = []
    for t in doc["tokens"]:
        up = t["text"].upper()
        m = re.search(r"(?:SC)?ALE\W{0,4}(\d{2,4})\b", up)
        if m:
            found.append((0, int(m.group(1)), t["text"]))
            continue
        m = re.search(r"\b(\d{2,4})\s*(?:FT|FEET)\b\W{0,6}(?:=|TO|-)?\s*(?:1|ONE|I|L)*\s*I?N?CH", up)
        if m:
            found.append((2 if "SHEET" in up else 1, int(m.group(1)), t["text"]))
    ft_per_in, t = None, None
    if found:
        best_rank = min(f[0] for f in found)
        vals = [f for f in found if f[0] == best_rank]
        ft_per_in = max({v[1] for v in vals}, key=lambda v: sum(1 for x in vals if x[1] == v))
        t = {"text": next(v[2] for v in vals if v[1] == ft_per_in)}
    if ft_per_in and not args.scales_given:
        # added to, not instead of, the defaults: the statement OCR found may belong to an inset drawn at another scale
        stated = sorted({round(ft_per_in * 0.3048 / dpi, 4) for dpi in (200, 250, 300, 350, 400)})
        scales = sorted(set(scales) | set(stated))
        print(f"sheet states {ft_per_in} ft to the inch (token {t['text']!r}); seeds for 200-400 dpi {stated} m/px added to the defaults")
    if near_scale and not args.scales_given:
        nb = sorted({round(near_scale * f, 4) for f in (0.98, 1.0, 1.02)})
        scales = sorted(set(scales) | set(nb))
        print(f"neighbours' scale: seeds {nb} m/px added")
    # rotation prefilter: a street name is printed along its street, so at the right rotation each oriented label's text
    # direction runs along its candidate street's bearing. That needs no translation at all, so the 36 rotations are
    # scored first and only the ones the labels agree with go through the translation sweep (36 -> ~4, ~9x less work).
    dirs = np.array([np.nan if l["text_direction_deg"] is None else l["text_direction_deg"] for l in labels], float)
    n_oriented = int((~np.isnan(dirs)).sum())
    if n_oriented >= 3 and len(rots) > 4:
        bear = []
        for c in cand:
            v = c[:, 1] - c[:, 0]
            bear.append((np.degrees(np.arctan2(v[:, 1], v[:, 0])) % 180, np.hypot(v[:, 0], v[:, 1])))
        scores = []
        for rot in rots:
            n = 0
            for i in range(len(labels)):
                if np.isnan(dirs[i]):
                    continue
                want = (rot - dirs[i]) % 180  # scan direction -> map angle under the y flip and this rotation
                ang, L = bear[i]
                off = np.abs((ang - want + 90) % 180 - 90)
                n += float(L[off <= 12].sum()) >= 0.2 * float(L.sum())  # a fair share of the street runs that way
            scores.append(n)
        top = max(scores)
        kept = [r for r, n in zip(rots, scores) if n >= top - 1]
        print(f"rotation prefilter: {n_oriented} labels have a text direction; {len(kept)} of {len(rots)} rotations agree with them "
              f"({', '.join(f'{r:.0f}' for r in kept)}; best {top} labels) -> translation sweep only for those")
        rots = kept
    pc = P.mean(0)
    best = []
    n_grid = 0
    for sc in scales:
        if near_win is not None:  # the neighbours' window, whatever the scale seed
            lo, hi = near_win
            step = max(args.grid_m, float((hi - lo).max()) / 80)
            gx = np.arange(lo[0], hi[0] + 1, step)
            gy = np.arange(lo[1], hi[1] + 1, step)
        else:
            # the label centroid cannot be farther from where the named streets meet than ~half a sheet at this scale
            half = max(250.0, 0.6 * sheet_diag_px * sc)
            step = max(args.grid_m, 2 * half / 80)  # ~80 steps across the window; the ICP basin grows with the sheet too
            c0 = np.clip(centre, seeds.min(0), seeds.max(0))
            gx = np.arange(c0[0] - half, c0[0] + half + 1, step)
            gy = np.arange(c0[1] - half, c0[1] + half + 1, step)
        grid = np.array([(X, Y) for X in gx for Y in gy], float)
        n_grid = max(n_grid, len(grid))
        for rot in rots:
            M = similarity(sc, rot, np.zeros(2))[:, :2]
            base = (P - pc) @ M.T  # labels relative to their centroid; translation grid places the centroid
            cst = grid_cost(base, grid, cand)
            for j in np.argsort(cst)[:3]:
                best.append((float(cst[j]), rot, sc, np.hstack([M, (grid[j] - M @ pc)[:, None]])))
    best.sort(key=lambda b: b[0])
    print(f"coarse search: up to {n_grid} translations x {len(rots)} rotations x {len(scales)} scales; best seeds " + ", ".join(f"(rot {b[1]:.0f}, {b[2]} m/px, cost {b[0]:.0f})" for b in best[:4]))
    rlog.note(n_rotation_seeds=len(rots), n_scale_seeds=len(scales), n_translation_grid=int(n_grid), candidate_radius_m=float(radius))
    rlog.lap("coarse")

    # 4. ICP from the best seeds: similarity -> outlier rejection -> similarity -> affine (inliers only)
    #    With --rotation labels the rotation is read off the labels' text directions (a name runs along its street) and the
    #    positions fix scale + translation: a label's centre sits anywhere across a 20 m street, and on a 300 m sheet that
    #    scatter can tilt a position-only fit by several degrees.
    want_dirs = args.rotation == "labels" and n_oriented >= 3
    if args.rotation == "labels" and not want_dirs:
        print(f"rotation: only {int((~np.isnan(dirs)).sum())} labels have a readable text direction; rotation fitted from positions instead")

    def fit_sim(mask, A0_, use_dirs):
        P_, cand_ = P[mask], [c for c, ok in zip(cand, mask) if ok]
        if use_dirs:
            return icp_label_rotation(P_, cand_, dirs[mask], A0_, huber_m=args.huber_m)
        A_, d_, Q_ = icp(P_, cand_, A0_, "similarity", huber_m=args.huber_m)
        return A_, d_, Q_, None

    def run_fit(use_dirs):
        """Seeds -> similarity ICP -> outlier rounds. Returns (A, residuals, inlier mask, last threshold, log lines)."""
        log = []
        fits = []
        for c, rot, sc, A0 in best[:20]:
            A_sim, d_sim, _, _ = fit_sim(np.ones(len(P), bool), A0, use_dirs)
            fits.append((math.sqrt((np.minimum(d_sim, 3 * args.huber_m) ** 2).mean()), A_sim, d_sim, rot, sc))
        fits.sort(key=lambda f: f[0])
        _, A_sim, d_sim, rot0, sc0 = fits[0]
        log.append(f"similarity fit RMS {math.sqrt((d_sim**2).mean()):.1f} m over all {len(P)} labels" + (f" (rotation from the text direction of {int((~np.isnan(dirs)).sum())} labels)" if use_dirs else " (rotation from the label positions)"))
        d_cur, A_cur, inl, thr = d_sim, A_sim, np.ones(len(P), bool), float("nan")
        for rnd in range(6):  # tighten until the inlier set stops changing: junk words that happen to be street names fall out
            sc_cur = math.sqrt(abs(np.linalg.det(A_cur[:, :2])))  # current m/px
            floor_m = max(args.outlier_m, args.outlier_px * sc_cur)
            thr = max(floor_m, 3 * float(np.median(d_cur[inl])))
            new_inl = d_cur <= thr
            if new_inl.sum() < max(args.min_labels, 4):
                break
            changed = not np.array_equal(new_inl, inl)
            inl = new_inl
            A_cur, _, _, _ = fit_sim(inl, A_cur, use_dirs)
            T_ = apply(A_cur, P)
            d_cur = np.array([nearest_on_segments(T_[i], cand[i])[2] for i in range(len(P))])
            log.append(f"  round {rnd + 1}: threshold {thr:.1f} m (floor {floor_m:.1f}) -> {int(inl.sum())} inliers, similarity RMS {math.sqrt((d_cur[inl]**2).mean()):.1f} m")
        return A_cur, d_cur, inl, thr, log, rot0, sc0

    A_cur, d_cur, inl, thr, log, rot0, sc0 = run_fit(want_dirs)
    use_dirs = want_dirs
    if want_dirs:
        # the text direction of a label is coarse (the rotated OCR views are 30 deg apart) and on a sheet whose streets run
        # diagonally it can be off by 10-20 deg; a fit from the positions alone that places half again as many labels
        # is then the better answer. The label rotation wins ties: on a near-axis sheet the positions alone can tilt it.
        A_f, d_f, inl_f, thr_f, log_f, rot0_f, sc0_f = run_fit(False)
        if inl_f.sum() >= max(args.min_labels, math.ceil(1.5 * inl.sum())):
            print(f"rotation from the labels' text direction places {int(inl.sum())} labels, from their positions {int(inl_f.sum())}: the text direction is off on this sheet; using the positions")
            A_cur, d_cur, inl, thr, log, use_dirs, rot0, sc0 = A_f, d_f, inl_f, thr_f, log_f, False, rot0_f, sc0_f
        else:
            print(f"rotation from the labels' text direction places {int(inl.sum())} labels, from their positions alone {int(inl_f.sum())}: keeping the text direction")
    for line in log:
        print(line)
    for l, di, ok in zip(labels, d_cur, inl):
        l["outlier"] = not bool(ok)
        l["residual_similarity_m"] = round(float(di), 2)
    rotation_source = f"text direction of {int((~np.isnan(dirs[inl])).sum())} inlier labels" if use_dirs else ("label positions (the text direction placed fewer labels)" if want_dirs else "label positions")
    if use_dirs:
        print(f"rotation {math.degrees(math.atan2(A_cur[1, 0], A_cur[0, 0])):.2f} deg from the {rotation_source}")
    print(f"outliers (> {thr:.1f} m): {[l['text'] for l in labels if l['outlier']] or 'none'}")
    P_in = P[inl]
    cand_in = [c for c, ok in zip(cand, inl) if ok]
    def summarise(A_: np.ndarray):
        T_ = apply(A_, P)
        out_ = [nearest_on_segments(T_[i], cand[i]) for i in range(len(P))]
        d_ = np.array([o[2] for o in out_]); Q_ = np.array([o[0] for o in out_])
        M_ = A_[:, :2]
        sx_, sy_ = np.linalg.norm(M_[:, 0]), np.linalg.norm(M_[:, 1])
        rot_ = math.degrees(math.atan2(M_[1, 0], M_[0, 0]))
        shear_ = math.degrees(math.acos(np.clip(M_[:, 0] @ M_[:, 1] / (sx_ * sy_), -1, 1))) - 90.0
        return d_, Q_, math.sqrt((d_[inl] ** 2).mean()), sx_, sy_, rot_, shear_

    A, _, _ = icp(P_in, cand_in, A_cur, "affine", huber_m=args.huber_m)
    d, Q, rms, sx, sy, rot, shear = summarise(A)
    transform, affine_rejected = "affine", None
    aniso = abs(sx / sy - 1)
    if aniso > args.max_anisotropy or abs(shear) > args.max_shear_deg:
        # paper shrinks < 1-2% and scanners skew < 1 deg; more than that means the labels sit on streets of one direction
        # only and the second scale / the shear are unconstrained. The similarity fit (4 parameters) is the honest answer.
        affine_rejected = {"scale_m_per_px": {"x": float(sx), "y": float(sy)}, "shear_deg": float(shear), "rms_m": float(rms),
                           "why": f"x/y scale differ by {aniso:.1%} (limit {args.max_anisotropy:.0%}) or shear {shear:.2f} deg (limit {args.max_shear_deg}): "
                                  "beyond paper shrink and scan skew, so the labels constrain only one direction"}
        print(f"affine rejected: {affine_rejected['why']}; keeping the similarity fit (rotation + one scale)")
        A, transform = A_cur.copy(), "similarity"
        d, Q, rms, sx, sy, rot, shear = summarise(A)
    T = apply(A, P)
    rlog.note(transform=transform, affine_rejected=bool(affine_rejected), affine_rejected_why=(affine_rejected or {}).get("why"), rotation_source=rotation_source,
             rms_m=float(rms), median_m=float(np.median(d[inl])), max_m=float(d[inl].max()), n_inliers=int(inl.sum()), n_outliers=int((~inl).sum()), outlier_threshold_m=float(thr),
             scale_m_per_px_x=float(sx), scale_m_per_px_y=float(sy), rotation_deg=float(rot), shear_deg=float(shear),
             coarse_seed={"rotation_deg": float(rot0), "scale_m_per_px": float(sc0)}, stated_scale_ft_per_inch=ft_per_in, n_dropped_far=len(dropped))
    rlog.lap("fit")
    print(f"fit ({transform}): RMS {rms:.1f} m over {int(inl.sum())} inlier labels ({len(P)} matched); scale {sx:.4f} x {sy:.4f} m/px, rotation {rot:.2f} deg, shear {shear:.2f} deg; implied scan dpi: {15.24 / sx:.0f} if the sheet is 50 ft/in, {30.48 / sx:.0f} if 100 ft/in")
    for l, di, q in zip(labels, d, Q):
        l["residual_m"] = round(float(di), 2)
        l["snapped_map"] = [round(float(q[0]), 3), round(float(q[1]), 3)]
        print(f"  {l['text']:>16s} -> {'/'.join(l['modern']):<22s} {di:6.1f} m{'   OUTLIER (excluded from the fit)' if l['outlier'] else ''}")

    # unmatched upper-case words that land on a modern centreline once the sheet is placed: streets renamed or respelled
    # since the plan (candidates for --alias), or OCR slips. Reported for a person to confirm; never used by the fit.
    allsegs = np.concatenate(list(streets.values()))
    seg_key = np.concatenate([np.full(len(v), k, dtype=object) for k, v in streets.items()])
    skipped_set = set(skipped)
    suggestions: dict[str, dict] = {}
    for t_ in tokens:
        txt = t_["text"].strip()
        if txt not in skipped_set or re.search(r"\d", txt) or not re.fullmatch(r"[A-Z][A-Z .'&-]*", txt):
            continue
        n_, _ = norm_label(txt)
        if len(n_) < 4 or n_ in TYPE_WORDS or n_ in DIRECTION_WORDS:
            continue
        x1, y1, x2, y2 = t_["bbox_xyxy_source"]
        if t_["in_block"]:
            continue  # a word inside a block is a building label, whatever centreline runs past
        cen = apply(A, np.array([[(x1 + x2) / 2, (y1 + y2) / 2]]))[0]
        a_, b_ = allsegs[:, 0], allsegs[:, 1]
        ab_ = b_ - a_
        u_ = np.clip(((cen - a_) * ab_).sum(1) / np.maximum((ab_ ** 2).sum(1), 1e-9), 0, 1)
        dist_ = np.linalg.norm(a_ + u_[:, None] * ab_ - cen, axis=1)
        i_ = int(dist_.argmin())
        if dist_[i_] <= thr and _base(str(seg_key[i_])) != n_:
            prev = suggestions.get(txt)
            if prev is None or dist_[i_] < prev["distance_m"]:
                suggestions[txt] = {"label": txt, "modern": str(seg_key[i_]), "distance_m": round(float(dist_[i_]), 1)}
    alias_suggestions = sorted(suggestions.values(), key=lambda s_: s_["distance_m"])
    rlog.note(n_alias_suggestions=len(alias_suggestions), alias_suggestions=[f"{s_['label']}->{s_['modern']}" for s_ in alias_suggestions[:12]])
    if alias_suggestions:
        print(f"alias candidates (unmatched upper-case words lying within {thr:.0f} m of a modern centreline; if they are the same street, add them to --alias): "
              + ", ".join(f"{s_['label']} -> {s_['modern']} ({s_['distance_m']} m)" for s_ in alias_suggestions))

    # 4. outputs
    src_w, src_h = doc["source_size"]["w"], doc["source_size"]["h"]
    A_inv = invert(A)
    georef = {
        "sheet": stem, "source_image": doc["source_image"], "source_size": doc["source_size"],
        "crs": f"EPSG:{epsg} ({crs.name()})", "epsg": epsg, "streets": str(args.streets), "streets_fields": fields, "intersections": str(args.intersections) if args.intersections else "derived from centreline vertices",
        "method": "OCR street labels -> point-to-line ICP onto modern centrelines; similarity then affine (kept only if physically plausible); Huber weights",
        "transform": transform, "affine_rejected": affine_rejected, "alias_suggestions": alias_suggestions, "building_labels": building, "rotation_source": rotation_source,
        "near": [str(r) for r in args.near] if args.near else None, "fuzzy": bool(args.fuzzy),
        "affine_source_px_to_map": {"a11": A[0, 0], "a12": A[0, 1], "tx": A[0, 2], "a21": A[1, 0], "a22": A[1, 1], "ty": A[1, 2]},
        "affine_map_to_source_px": {"a11": A_inv[0, 0], "a12": A_inv[0, 1], "tx": A_inv[0, 2], "a21": A_inv[1, 0], "a22": A_inv[1, 1], "ty": A_inv[1, 2]},
        "scale_m_per_px": {"x": sx, "y": sy}, "rotation_deg": rot, "shear_deg": shear, "implied_dpi_if_50ft_per_inch": 15.24 / sx, "implied_dpi_if_100ft_per_inch": 30.48 / sx,
        "rms_m": rms, "median_m": float(np.median(d[inl])), "max_m": float(d[inl].max()), "n_labels": int(inl.sum()), "n_outliers": int((~inl).sum()), "outlier_threshold_m": thr, "dropped_far": dropped,
        "coarse_seed": {"rotation_deg": rot0, "scale_m_per_px": sc0}, "stated_scale_ft_per_inch": ft_per_in,
        "implied_dpi_from_stated_scale": (ft_per_in * 0.3048 / sx) if ft_per_in else None, "labels": labels, "unmatched_tokens": sorted(set(skipped)),
        "params": {k_: (str(v_) if isinstance(v_, Path) else v_) for k_, v_ in vars(args).items()} | {"run": str(run), "streets": str(args.streets), "intersections": str(args.intersections), "alias": str(args.alias) if args.alias else None, "near": [str(r) for r in args.near] if args.near else None},
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (run / f"{stem}_georef.json").write_text(json.dumps(georef, indent=1, default=float))

    # QGIS .points (source y is negative row index in QGIS' convention)
    lines = [f"#CRS: {crs.wkt()}", "mapX,mapY,sourceX,sourceY,enable,dX,dY,residual"]
    for l in labels:
        (mx, my), (px, py) = l["snapped_map"], l["px"]
        lines.append(f"{mx:.6f},{my:.6f},{px:.3f},{-py:.3f},{0 if l['outlier'] else 1},0,0,{l['residual_m']}")
    (run / f"{stem}_georef.points").write_text("\n".join(lines) + "\n")

    # world file: coefficients refer to the centre of the top-left pixel
    c = apply(A, np.array([[0.5, 0.5]]))[0]
    (run / f"{stem}.jgw").write_text("\n".join(f"{v:.10f}" for v in (A[0, 0], A[1, 0], A[0, 1], A[1, 1], c[0], c[1])) + "\n")

    def to_wgs84_ring(ring_px):
        m = apply(A, np.array(ring_px, float))
        lon, lat = crs.to_wgs84(m[:, 0], m[:, 1])
        return [[round(float(x), 7), round(float(y), 7)] for x, y in zip(lon, lat)]

    def to_map_ring(ring_px):
        m = apply(A, np.array(ring_px, float))
        return [[round(float(x), 3), round(float(y), 3)] for x, y in m]

    if args.retrace == "seeded" and next(run.glob("*_tiles.json"), None) is not None:
        # the fit knows where today's streets run on the scan: trace the blocks again with that as the street evidence
        import fim_blocks
        seg_list = [s_ for k_, s_ in streets.items() if k_.strip() and len(s_)]
        segs_px = apply(A_inv, np.concatenate(seg_list).reshape(-1, 2)).reshape(-1, 2, 2)
        print(f"re-tracing the blocks with {len(segs_px)} modern centreline segments as street seeds (necks narrower than {2 * args.neck_px} px carved) ...", flush=True)
        fim_blocks.trace(fim_blocks.default_args(run, georef=True, neck_px=args.neck_px, legend=args.legend, floors=args.floors), segs_px)
        rlog.lap("retrace")
    blocks_path = run / f"{stem}_blocks_px.geojson"
    if not blocks_path.exists() and (run / f"{stem}_blocks.geojson").exists():
        blocks_path = run / f"{stem}_blocks.geojson"  # pre-2026-09-14 name
    if blocks_path.exists():
        bl = json.loads(blocks_path.read_text())
        # what the fit learned about the tokens: which are street labels, and what modern street each names
        street_by_bbox = {}
        for l in labels:
            street_by_bbox[tuple(int(round(v)) for v in l["bbox_source"])] = l
        label_pts = np.array([l["px"] for l in labels], float) if labels else np.zeros((0, 2))

        def modern_streets_bounding(ring_map: np.ndarray, centroid_map: np.ndarray, reach_m: float, exclude: list[str]) -> list[dict]:
            """Modern centrelines within reach_m of the polygon's edge, with distance and compass side from the centroid."""
            out = []
            for key, segs in streets.items():  # every named street in the layer, matched or not
                if not key.strip() or key in exclude:
                    continue
                mid = segs.mean(1)
                near = segs[np.linalg.norm(mid - centroid_map, axis=1) < reach_m + 400]  # cheap prefilter
                if not len(near):
                    continue
                best, best_q, near_n, tot_n = 1e9, None, 0, 0
                for v in ring_map[:: max(1, len(ring_map) // 80)]:
                    q, _, dd = nearest_on_segments(v, near)
                    tot_n += 1
                    if dd <= reach_m:
                        near_n += 1
                    if dd < best:
                        best, best_q = dd, q
                if best <= reach_m and near_n / max(tot_n, 1) >= 0.08:  # a side of the block, not a corner touch
                    br = (math.degrees(math.atan2(best_q[0] - centroid_map[0], best_q[1] - centroid_map[1])) + 360) % 360  # map: x east, y north
                    out.append({"name": key, "distance_m": round(best, 1), "bearing_deg": round(br), "side": side_of(br), "ring_share": round(near_n / max(tot_n, 1), 2)})
            return sorted(out, key=lambda d: d["distance_m"])

        def streets_through(outer_px: np.ndarray, min_len_m: float = 40.0, margin_m: float = 8.0) -> list[str]:
            """Modern streets whose centreline runs through the polygon interior — at least margin_m inside the boundary — for
            at least min_len_m (sampled every 5 m). A street that merely skirts the edge does not count. The polygon is
            rasterised once (1 px = 1 m) and a distance transform gives every sample's depth inside in O(1)."""
            ring_map = apply(A, outer_px)
            lo, hi = ring_map.min(0) - 2, ring_map.max(0) + 2
            w, h = int(hi[0] - lo[0]) + 1, int(hi[1] - lo[1]) + 1
            mask = np.zeros((h, w), np.uint8)
            cv2.fillPoly(mask, [np.round(ring_map - lo).astype(np.int32)], 255)
            depth = cv2.distanceTransform(mask, cv2.DIST_L2, 3)  # metres inside the polygon
            found = []
            for key, segs in streets.items():
                if not key.strip():
                    continue
                flat = segs.reshape(-1, 2)
                if flat[:, 0].max() < lo[0] or flat[:, 0].min() > hi[0] or flat[:, 1].max() < lo[1] or flat[:, 1].min() > hi[1]:
                    continue
                inside_m = 0.0
                for (x1, y1), (x2, y2) in segs:
                    if max(x1, x2) < lo[0] or min(x1, x2) > hi[0] or max(y1, y2) < lo[1] or min(y1, y2) > hi[1]:
                        continue
                    L = math.hypot(x2 - x1, y2 - y1)
                    n = max(2, int(L / 5))
                    pts = np.linspace([x1, y1], [x2, y2], n) - lo
                    ix, iy = np.round(pts[:, 0]).astype(int), np.round(pts[:, 1]).astype(int)
                    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
                    inside_m += int((depth[iy[ok], ix[ok]] > margin_m).sum()) * (L / n)
                if inside_m >= min_len_m:
                    found.append(key)
            return found

        def split_by_streets(outer_px: np.ndarray, through: list[str], street_w_m: float = 14.0, min_part_m2: float = 400.0) -> list[np.ndarray]:
            """Cut the polygon along the given modern centrelines (drawn street_w_m wide) and return the parts as source-px rings."""
            ring_map = apply(A, outer_px)
            lo, hi = ring_map.min(0) - 2, ring_map.max(0) + 2
            w, h = int(hi[0] - lo[0]) + 1, int(hi[1] - lo[1]) + 1
            mask = np.zeros((h, w), np.uint8)
            cv2.fillPoly(mask, [np.round(ring_map - lo).astype(np.int32)], 255)
            for key in through:
                for (x1, y1), (x2, y2) in streets[key]:
                    cv2.line(mask, (int(round(x1 - lo[0])), int(round(y1 - lo[1]))), (int(round(x2 - lo[0])), int(round(y2 - lo[1]))), 0, int(street_w_m), cv2.LINE_8)
            n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
            parts = []
            for i in range(1, n):
                if stats[i, cv2.CC_STAT_AREA] < min_part_m2:
                    continue
                comp = (lab == i).astype(np.uint8)
                cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                c = max(cnts, key=cv2.contourArea).reshape(-1, 2).astype(float) + lo
                parts.append(np.round(apply(A_inv, c)).astype(int))
            return parts

        num_tokens = [t for t in tokens if re.fullmatch(r"\d+[½¼¾]?|\d+½", t["text"])]

        def tokens_inside(ring_px: np.ndarray) -> tuple[list[str], str | None]:
            """Numeric tokens inside a ring: (lot numbers, block number = the tallest-print numeral, if clearly taller)."""
            cnt = ring_px.astype(np.float32).reshape(-1, 1, 2)
            ins = []
            for t in num_tokens:
                x1, y1, x2, y2 = t["bbox_xyxy_source"]
                if cv2.pointPolygonTest(cnt, ((x1 + x2) / 2.0, (y1 + y2) / 2.0), False) > 0:
                    ins.append((y2 - y1, t["text"]))
            if not ins:
                return [], None
            ins.sort()
            heights = [h_ for h_, _ in ins]
            med = float(np.median(heights))
            block = ins[-1][1] if ins[-1][0] >= 1.6 * med and len(ins) >= 3 else None
            lots = [txt for h_, txt in ins if txt != block]
            return sorted(set(lots), key=lambda v: (len(v), v)), block

        accepted, rejected = [], []
        queue = list(bl["features"])
        while queue:
            f = queue.pop(0)
            g = f["geometry"]
            if g["type"] not in ("Polygon", "MultiPolygon"):
                continue
            rings_px = g["coordinates"] if g["type"] == "Polygon" else g["coordinates"][0]
            outer_px = np.array(rings_px[0], float)
            props = dict(f["properties"])
            # 1. split the tracer's 'streets' (any alphabetic token near the polygon) into real street labels and other text
            real, other = [], []
            for st in props.get("streets", []):
                key = tuple(int(round(v)) for v in st.get("label_bbox_source", []))
                l = street_by_bbox.get(key)
                if l and not l.get("outlier"):
                    real.append({"label_1895": st["name"], "modern": l["modern"], "side": st.get("side"), "distance_px": st.get("distance_px"), "residual_m": l.get("residual_m")})
                else:
                    other.append(st["name"])
            # 2. is it one block? Street labels inside the polygon and modern centrelines running through it say otherwise.
            #    An inset frame or a compound has several streets through it and OCR street labels whose street is far away
            #    (fit outliers). Two blocks merged across a narrow street have exactly one street through them: kept, flagged.
            inside_ok, inside_out = [], []
            if len(label_pts):
                cnt = outer_px.astype(np.float32).reshape(-1, 1, 2)
                for i in range(len(labels)):
                    if cv2.pointPolygonTest(cnt, (float(label_pts[i][0]), float(label_pts[i][1])), False) > 0:
                        (inside_out if labels[i].get("outlier") else inside_ok).append(labels[i]["text"])
            area_px = abs(float(cv2.contourArea(outer_px.astype(np.float32))))
            perim_px = float(cv2.arcLength(outer_px.astype(np.float32), True))
            compact = 4 * math.pi * area_px / max(perim_px**2, 1e-9)  # 1 = circle, ~0.6 rectangle, <0.15 a strip
            props["compactness"] = round(compact, 3)
            through = streets_through(outer_px)
            if through and not inside_out and not props.get("_split_from"):  # cut first: a compound's parts are judged on their own
                parts = split_by_streets(outer_px, through)
                parent_area = abs(cv2.contourArea(outer_px.astype(np.float32)))
                if len(parts) >= 2:
                    print(f"  split: block_number={props.get('block_number')} cut along {through} -> {len(parts)} parts")
                    for k_, ring in enumerate(parts):
                        part_area = abs(cv2.contourArea(ring.astype(np.float32)))
                        if part_area < 0.2 * parent_area:  # the street has been widened/realigned into the old block: a sliver, not a block
                            sub = dict(f["properties"]); sub["is_block"] = False
                            sub["rejected_because"] = f"sliver ({part_area / parent_area:.0%} of the parent) left after cutting along {through} — a street widened or realigned into the 1895 block"
                            sub["area_source_px2"] = int(part_area); sub.pop("streets", None)
                            rejected.append((sub, {"type": "Polygon", "coordinates": [ring.tolist() + [ring[0].tolist()]]}))
                            continue
                        sub = dict(f["properties"])
                        sub["block_number_inferred"] = True
                        sub["_split_from"] = {"block_number": props.get("block_number"), "cut_along": through, "part": k_ + 1, "of": len(parts)}
                        sub.pop("block_number", None); sub.pop("block_number_inferred", None)
                        sub["lot_numbers"], sub["block_number"] = tokens_inside(ring)
                        sub["block_number_inferred"] = True  # read by height among the part's numerals, not by stroke
                        sub["block_id"] = f"{props.get('block_id') or stem + ':block:fid?'}:part{k_ + 1}"
                        sub["centroid_source_px"] = [round(float(v)) for v in ring.mean(0)]
                        sub["area_source_px2"] = int(abs(cv2.contourArea(ring.astype(np.float32))))
                        queue.append({"type": "Feature", "properties": sub, "geometry": {"type": "Polygon", "coordinates": [ring.tolist() + [ring[0].tolist()]]}})
                    continue
            lots = props.get("lot_numbers") or []
            has_block_numeral = bool(props.get("block_number")) and props.get("block_number_inferred") is False
            if args.lots == "none":  # no lot or block numbering on this plan: the numerals are house numbers, years, ...
                props["numbers_inside"] = sorted(set(lots) | ({props["block_number"]} if props.get("block_number") else set()), key=lambda v: (len(v), v))
                props["block_number"], props["block_number_inferred"], props["lot_numbers"] = None, False, []
            reason = None
            if compact < 0.15:
                reason = f"thin strip (compactness {compact:.2f}) — a frame or border line, not a block"
            elif inside_out:
                reason = f"contains street labels whose streets lie elsewhere {inside_out} — an inset of another area"
            elif len(through) >= 2:
                reason = f"{len(through)} modern streets run through it {through} — an inset or compound, not one block"
            elif args.lots == "numbered" and len(lots) < 2 and not has_block_numeral:
                reason = f"only {len(lots)} lot number(s) inside and no block numeral — a building outline or a fragment"
            props["streets_through"] = through
            props["merged_across"] = through[0] if (not reason and through) else None
            if props.get("_split_from"):
                props["split_from"] = props.pop("_split_from")
            if inside_ok and not reason:
                props["street_labels_inside"] = inside_ok
            # 3. geometry in the map CRS + the modern streets that actually bound it
            ring_map = apply(A, outer_px)
            cen_map = apply(A, np.array([props.get("centroid_source_px", outer_px.mean(0))], float))[0]
            props["streets_1895"] = real
            props["streets_modern"] = modern_streets_bounding(ring_map, cen_map, args.block_street_reach_m, through) if not reason else []
            props["street_names"] = sorted({r["label_1895"] for r in real})
            props["nearby_text"] = sorted(set(other))
            props.pop("streets", None)
            props["centroid_map"] = [round(float(v), 3) for v in cen_map]
            props["is_block"] = reason is None
            if reason:
                props["rejected_because"] = reason
            (rejected if reason else accepted).append((props, g))
        for crs_urn, conv, name in ((f"urn:ogc:def:crs:EPSG::{epsg}", to_map_ring, f"epsg{epsg}"), ("urn:ogc:def:crs:OGC:1.3:CRS84", to_wgs84_ring, "wgs84")):
            for group, suffix in ((accepted, ""), (rejected, "_rejected")):
                out = {"type": "FeatureCollection", **({"crs": {"type": "name", "properties": {"name": crs_urn}}} if name != "wgs84" else {}),
                       "georeference": {"rms_m": rms, "n_labels": int(inl.sum()), "from": f"{stem}_georef.json"}, "source_blocks": str(blocks_path), "lot_convention": args.lots,
                       "note": ("blocks: polygons with lots inside and streets around them; streets_1895 = OCR street labels around the block that matched the modern layer, "
                                "streets_modern = modern centrelines within --block-street-reach-m of the polygon, nearby_text = other OCR text the tracer saw nearby"
                                if not suffix else "traced shapes that are not blocks (inset frames, building outlines, fragments) — kept for inspection"),
                       "features": []}
                for props, g in group:
                    if g["type"] == "Polygon":
                        geom = {"type": "Polygon", "coordinates": [conv(r) for r in g["coordinates"]]}
                    else:
                        geom = {"type": "MultiPolygon", "coordinates": [[conv(r) for r in poly] for poly in g["coordinates"]]}
                    out["features"].append({"type": "Feature", "geometry": geom, "properties": props})
                if group or not suffix:
                    (run / f"{stem}_blocks{suffix}_{name}.geojson").write_text(json.dumps(out, indent=1))
        print(f"blocks: {len(accepted)} kept -> {stem}_blocks_epsg{epsg}.geojson, {stem}_blocks_wgs84.geojson; {len(rejected)} rejected -> {stem}_blocks_rejected_*.geojson")
        for props, _ in rejected:
            print(f"  rejected: block_number={props.get('block_number')} area={props.get('area_source_px2')} — {props['rejected_because']}")
        for props, _ in accepted:
            print(f"  block {str(props.get('block_number') or '?'):>4s}: 1895 streets {props['street_names']}; modern {[d['name'] + ' ' + d['side'] for d in props['streets_modern']]}" + (f"; part {props['split_from']['part']}/{props['split_from']['of']} of a compound cut along {props['split_from']['cut_along']}" if props.get('split_from') else "") + (f"; MERGED across {props['merged_across']}" if props['merged_across'] else "") + (f"; other text {props['nearby_text'][:4]}" if props['nearby_text'] else ""))

    # buildings (fim_blocks.py --buildings): footprints inside the blocks, each linked to the block that holds its centroid
    # AFTER the cleaning above (a footprint whose block was split follows the part it lies in; one whose block was rejected
    # is kept with block_id null and 'orphan' true, so nothing silently disappears)
    bpath = run / f"{stem}_buildings_px.geojson"
    if blocks_path.exists() and bpath.exists():
        bl_b = json.loads(bpath.read_text())
        final_blocks = [(props_, np.array(g_["coordinates"][0] if g_["type"] == "Polygon" else g_["coordinates"][0][0], np.float32).reshape(-1, 1, 2)) for props_, g_ in accepted]
        b_out = []
        n_orphan = 0
        for f in bl_b["features"]:
            props_ = dict(f["properties"])
            cx_, cy_ = props_.get("centroid_source_px") or np.array(f["geometry"]["coordinates"][0]).mean(0)
            home = next((bp for bp, cnt_ in final_blocks if cv2.pointPolygonTest(cnt_, (float(cx_), float(cy_)), False) >= 0), None)
            if home is None:
                n_orphan += 1
                props_.update({"block_id": None, "block_number": None, "orphan": True, "orphan_because": "its block was rejected, split away or never traced"})
            else:
                props_.update({"block_id": home.get("block_id"), "block_number": home.get("block_number"), "orphan": False})
                props_["building_id"] = f"{home.get('block_id')}:bldg{f.get('id', len(b_out))}"
            props_["centroid_map"] = [round(float(v), 3) for v in apply(A, np.array([[float(cx_), float(cy_)]]))[0]]
            b_out.append((props_, f["geometry"]))
        for crs_urn, conv, name in ((f"urn:ogc:def:crs:EPSG::{epsg}", to_map_ring, f"epsg{epsg}"), ("urn:ogc:def:crs:OGC:1.3:CRS84", to_wgs84_ring, "wgs84")):
            out = {"type": "FeatureCollection", **({"crs": {"type": "name", "properties": {"name": crs_urn}}} if name != "wgs84" else {}),
                   "georeference": {"rms_m": rms, "n_labels": int(inl.sum()), "from": f"{stem}_georef.json"}, "source_buildings": str(bpath), "lot_convention": args.lots,
                   "note": bl_b.get("note"), "paper_chroma": bl_b.get("paper_chroma"), "legend": bl_b.get("legend"), "features": []}
            for props_, g_ in b_out:
                out["features"].append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [conv(r) for r in g_["coordinates"]]}, "properties": props_})
            (run / f"{stem}_buildings_{name}.geojson").write_text(json.dumps(out, indent=1, ensure_ascii=False))
        print(f"buildings: {len(b_out)} enclosed outlines -> {stem}_buildings_epsg{epsg}.geojson, {stem}_buildings_wgs84.geojson ({n_orphan} orphans whose block was not kept)")

    # colour-wash areas (fim_areas.py, run explicitly on tinted sheets): placed like the blocks, streets cleaned the same way,
    # but never split or rejected for lot counts — an area is a region of the sheet, not a city block
    areas_path = run / f"{stem}_areas_px.geojson"
    if areas_path.exists():
        ar = json.loads(areas_path.read_text())
        street_by_bbox_a = {tuple(int(round(v)) for v in l["bbox_source"]): l for l in labels}
        feats_out = []
        for f in ar["features"]:
            g = f["geometry"]
            if g["type"] != "Polygon":
                continue
            outer_px = np.array(g["coordinates"][0], float)
            props = dict(f["properties"])
            real, other = [], []
            for st in props.get("streets", []):
                l = street_by_bbox_a.get(tuple(int(round(v)) for v in st.get("label_bbox_source", [])))
                if l and not l.get("outlier"):
                    real.append({"label": st["name"], "modern": l["modern"], "distance_px": st.get("distance_px"), "residual_m": l.get("residual_m")})
                else:
                    other.append(st["name"])
            props["streets_matched"] = real
            props["street_names"] = sorted({r["label"] for r in real})
            props["nearby_text"] = sorted(set(other))
            props.pop("streets", None)
            props["centroid_map"] = [round(float(v), 3) for v in apply(A, np.array([props.get("centroid_source_px", outer_px.mean(0))], float))[0]]
            feats_out.append((props, g))
        for crs_urn, conv, name in ((f"urn:ogc:def:crs:EPSG::{epsg}", to_map_ring, f"epsg{epsg}"), ("urn:ogc:def:crs:OGC:1.3:CRS84", to_wgs84_ring, "wgs84")):
            out = {"type": "FeatureCollection", **({"crs": {"type": "name", "properties": {"name": crs_urn}}} if name != "wgs84" else {}),
                   "georeference": {"rms_m": rms, "n_labels": int(inl.sum()), "from": f"{stem}_georef.json"}, "source_areas": str(areas_path),
                   "note": "colour-wash areas traced by fim_areas.py (tints, not outlines); block_number is the big numeral inside (a key plan's sheet number)",
                   "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [conv(r) for r in g["coordinates"]]}, "properties": props} for props, g in feats_out]}
            (run / f"{stem}_areas_{name}.geojson").write_text(json.dumps(out, indent=1))
        print(f"areas: {len(feats_out)} -> {stem}_areas_epsg{epsg}.geojson, {stem}_areas_wgs84.geojson")

    tok_out = {"type": "FeatureCollection", "features": []}
    for t in tokens:
        x1, y1, x2, y2 = t["bbox_xyxy_source"]
        ring = t.get("polygon_source") or [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        ring = list(ring) + [ring[0]]
        cen = apply(A, np.array([[(x1 + x2) / 2, (y1 + y2) / 2]]))[0]
        tok_out["features"].append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [to_wgs84_ring(ring)]}, "properties": {"text": t["text"], "id": t.get("id"), "tile": t.get("tile"), "rotation_view": t.get("rotation", 0), "in_block": t.get("in_block"), "in_block_depth_px": t.get("in_block_depth_px"), "surya_conf": t.get("surya_conf"), "centre_map": [round(float(cen[0]), 3), round(float(cen[1]), 3)], "map_epsg": epsg, "bbox_source_px": [x1, y1, x2, y2]}})
    (run / f"{stem}_tokens_wgs84.geojson").write_text(json.dumps(tok_out, indent=1))
    print(f"tokens: {len(tok_out['features'])} -> {stem}_tokens_wgs84.geojson")

    # page footprint: the whole scan and the content box (--crop of the tile run) as polygons, in both CRSs
    W_, H_ = src_w, src_h
    page_ring = [[0, 0], [W_, 0], [W_, H_], [0, H_], [0, 0]]
    crop = doc.get("crop_source_px")
    cx0, cy0, cx1, cy1 = (int(v) for v in crop.split(",")) if crop else (0, 0, W_, H_)
    crop_ring = [[cx0, cy0], [cx1, cy0], [cx1, cy1], [cx0, cy1], [cx0, cy0]]
    common = {"sheet": stem, "source_image": doc["source_image"], "source_size_px": [W_, H_], "epsg_fit": epsg, "rms_m": round(rms, 2),
              "n_labels": int(inl.sum()), "scale_m_per_px": [round(sx, 5), round(sy, 5)], "rotation_deg": round(rot, 2), "shear_deg": round(shear, 2), "transform": transform}
    for crs_urn, conv, name in ((f"urn:ogc:def:crs:EPSG::{epsg}", to_map_ring, f"epsg{epsg}"), ("urn:ogc:def:crs:OGC:1.3:CRS84", to_wgs84_ring, "wgs84")):
        page_out = {"type": "FeatureCollection", **({"crs": {"type": "name", "properties": {"name": crs_urn}}} if name != "wgs84" else {}), "features": [
            {"type": "Feature", "properties": common | {"what": "scan", "note": "outline of the whole scanned page incl. margins, colour bar and ruler"}, "geometry": {"type": "Polygon", "coordinates": [conv(page_ring)]}},
            {"type": "Feature", "properties": common | {"what": "content", "crop_source_px": [cx0, cy0, cx1, cy1], "note": "the map content box that was tiled and OCR'd"}, "geometry": {"type": "Polygon", "coordinates": [conv(crop_ring)]}},
        ]}
        (run / f"{stem}_page_{name}.geojson").write_text(json.dumps(page_out, indent=1))
    georef["page_corners_wgs84"] = {"scan": to_wgs84_ring(page_ring)[:4], "content": to_wgs84_ring(crop_ring)[:4]}
    georef["page_corners_map"] = {"scan": to_map_ring(page_ring)[:4], "content": to_map_ring(crop_ring)[:4]}
    (run / f"{stem}_georef.json").write_text(json.dumps(georef, indent=1, default=float))
    print(f"page footprint -> {stem}_page_epsg{epsg}.geojson, {stem}_page_wgs84.geojson (scan outline + content box)")

    # 4b. street-name log: what this sheet says about names that changed. One feature per label, geometry = the modern
    #     street's centreline segments within the sheet's content box (so the entry carries the street's geography, not
    #     just a name), plus the label's own position. Kinds: renamed (matched through --alias), respelled (--fuzzy),
    #     moved (a matched label whose street now lies farther away — an outlier), candidate (unmatched label on a centreline).
    year = args.year
    if year is None and args.alias:
        m_ = re.search(r"(1[5-9]\d\d|20\d\d)", args.alias.name)
        year = int(m_.group(1)) if m_ else None
    content_map = apply(A, np.array(crop_ring, float))
    lo_c, hi_c = content_map.min(0) - 50, content_map.max(0) + 50

    def street_geom_on_sheet(keys: list[str]) -> dict | None:
        parts = []
        for k in keys:
            segs = streets.get(k)
            if segs is None:
                continue
            mid = segs.mean(1)
            inside = segs[(mid[:, 0] >= lo_c[0]) & (mid[:, 0] <= hi_c[0]) & (mid[:, 1] >= lo_c[1]) & (mid[:, 1] <= hi_c[1])]
            for (x1, y1), (x2, y2) in inside:
                lon, lat = crs.to_wgs84(np.array([x1, x2]), np.array([y1, y2]))
                parts.append([[round(float(lon[0]), 7), round(float(lat[0]), 7)], [round(float(lon[1]), 7), round(float(lat[1]), 7)]])
        return {"type": "MultiLineString", "coordinates": parts} if parts else None

    def name_entry(text: str, modern: list[str], kind: str, px: list[float], dist: float | None, used: bool | None, extra: dict | None = None) -> dict:
        cen = apply(A, np.array([px], float))[0]
        lon, lat = crs.to_wgs84(np.array([cen[0]]), np.array([cen[1]]))
        props = {"sheet": stem, "label_on_plan": text, "name_on_plan": norm_label(text)[0], "plan_year": year, "modern_name": modern,
                 "modern_source": str(args.streets), "kind": kind, "distance_m": None if dist is None else round(float(dist), 1),
                 "used_in_fit": used, "label_centre_wgs84": [round(float(lon[0]), 7), round(float(lat[0]), 7)],
                 "label_centre_map": [round(float(cen[0]), 3), round(float(cen[1]), 3)], "map_epsg": epsg} | (extra or {})
        geom = street_geom_on_sheet(modern) or {"type": "Point", "coordinates": props["label_centre_wgs84"]}
        return {"type": "Feature", "geometry": geom, "properties": props}

    names_out = []
    for l in labels:
        if l.get("alias"):
            names_out.append(name_entry(l["text"], l["modern"], "renamed", l["px"], l["residual_m"], not l["outlier"], {"how": "--alias file"}))
        elif l.get("fuzzy"):
            names_out.append(name_entry(l["text"], l["modern"], "respelled", l["px"], l["residual_m"], not l["outlier"], {"how": f"--fuzzy: read as {l['fuzzy']}"}))
        elif l["outlier"]:
            names_out.append(name_entry(l["text"], l["modern"], "moved", l["px"], l["residual_m"], False, {"how": f"matched by name but {l['residual_m']} m from today's centreline (fit outlier): the street moved, or the word is not a street label"}))
    for b in building:
        names_out.append(name_entry(b["text"], b["modern"], "building", b["px"], None, False, {"how": f"spells a street name but sits {b['depth_px']} px inside a traced block: a building or business label, not used"}))
    for s_ in alias_suggestions:
        t_ = next(t for t in tokens if t["text"].strip() == s_["label"])
        x1, y1, x2, y2 = t_["bbox_xyxy_source"]
        names_out.append(name_entry(s_["label"], [s_["modern"]], "candidate", [(x1 + x2) / 2, (y1 + y2) / 2], s_["distance_m"], False, {"how": "unmatched word lying on this modern centreline after the fit; confirm before adding to --alias"}))
    (run / f"{stem}_street_names_wgs84.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "georeference": {"rms_m": rms, "n_labels": int(inl.sum()), "from": f"{stem}_georef.json"},
        "note": "street-name changes seen on this sheet: renamed (--alias), respelled (--fuzzy), moved (fit outlier), candidate (unmatched word on a centreline), building (spells a street name but lies inside a traced block). "
                "Geometry = the modern street's centreline within the sheet's content box (or the label point if the layer has none there); label_centre_* = where the word sits.",
        "features": names_out}, indent=1))
    print(f"street names -> {stem}_street_names_wgs84.geojson ({len(names_out)} entries: " + ", ".join(f"{k} {sum(1 for f in names_out if f['properties']['kind'] == k)}" for k in ("renamed", "respelled", "moved", "candidate", "building")) + ")")

    # 5. overlay: modern centrelines + intersections back-projected onto the scan
    img = cv2.imread(doc["source_image"])
    if img is None:
        img = np.full((src_h, src_w, 3), 255, np.uint8)
    k = args.overlay_px / max(img.shape[:2])
    ov = cv2.resize(img, (round(img.shape[1] * k), round(img.shape[0] * k)), interpolation=cv2.INTER_AREA)
    allsegs = np.concatenate(list(streets.values()))
    px_segs = apply(A_inv, allsegs.reshape(-1, 2)).reshape(-1, 2, 2) * k
    H, W = ov.shape[:2]
    for (x1, y1), (x2, y2) in px_segs:
        if max(x1, x2) < 0 or max(y1, y2) < 0 or min(x1, x2) > W or min(y1, y2) > H:
            continue
        cv2.line(ov, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))), (0, 0, 255), 3, cv2.LINE_AA)
    for key in matched:
        for (x1, y1), (x2, y2) in apply(A_inv, streets[key].reshape(-1, 2)).reshape(-1, 2, 2) * k:
            if max(x1, x2) < 0 or max(y1, y2) < 0 or min(x1, x2) > W or min(y1, y2) > H:
                continue
            cv2.line(ov, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))), (255, 0, 0), 4, cv2.LINE_AA)
    for x_ in inter:
        x, y = apply(A_inv, np.array([x_["xy"]], float))[0] * k
        if 0 <= x < W and 0 <= y < H:
            cv2.circle(ov, (int(round(x)), int(round(y))), 9, (0, 200, 0), -1, cv2.LINE_AA)
            cv2.circle(ov, (int(round(x)), int(round(y))), 9, (0, 0, 0), 2, cv2.LINE_AA)
    for l in labels:
        px = np.array(l["px"]) * k
        q = apply(A_inv, np.array([l["snapped_map"]]))[0] * k
        cv2.line(ov, (int(px[0]), int(px[1])), (int(q[0]), int(q[1])), (255, 0, 255), 3, cv2.LINE_AA)
        cv2.circle(ov, (int(px[0]), int(px[1])), 12, (255, 0, 255), 3, cv2.LINE_AA)
        cv2.putText(ov, f"{l['text']} {l['residual_m']:.0f}m{' (outlier)' if l['outlier'] else ''}", (int(px[0]) + 14, int(px[1]) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2, cv2.LINE_AA)
    banner = f"{stem}: OCR-georeferenced onto {args.streets.name} (EPSG:{epsg}). {int(inl.sum())} labels (+{int((~inl).sum())} outliers), RMS {rms:.1f} m. red = modern streets, blue = streets named on this sheet, green = intersections, magenta = OCR label -> snapped centreline"
    cv2.rectangle(ov, (0, 0), (W, 44), (255, 255, 255), -1)
    cv2.putText(ov, banner[:230], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.imwrite(str(run / f"{stem}_georef_overlay.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"overlay -> {stem}_georef_overlay.jpg;  GCPs -> {stem}_georef.points;  world file -> {stem}.jgw (EPSG:{epsg})")
    rlog.note(**map_outputs_summary(run, stem), page_centre_wgs84=ring_centre(georef["page_corners_wgs84"]["content"]), status="placed")
    rlog.lap("outputs")


if __name__ == "__main__":
    main()
