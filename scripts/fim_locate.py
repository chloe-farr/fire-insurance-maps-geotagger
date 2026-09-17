#!/usr/bin/env python3
"""
Where on Earth is this sheet? Propose the place(s) a tile-OCR run comes from, using only the street names it read.

For a sheet whose location is unknown — or that straddles two municipalities — there is no city to give
fim_fetch_streets.py. This step needs none: it takes the words fim_tile_ocr.py read off the sheet, keeps the ones that
look like street names (outside the traced blocks, with a type word or repeated), looks each one up in Nominatim (the
OpenStreetMap place index; open data, one request per second), and ranks the places where the most DISTINCT names lie
within a few kilometres of each other. A name that exists in hundreds of towns weighs little; three or four rare names
meeting in one spot weigh a lot.

It PROPOSES. Nothing is fetched or chosen: each candidate is printed with the place description Nominatim's addresses
give it, a padded S,W,N,E box, and the exact fim_fetch_streets.py command to copy. <run>/<stem>_locate.json records
the same (with `selected: null` — no code path ever fills it). Raw responses are cached in
<run>/<stem>_locate_cache.json so scoring flags can be changed without new requests.

    python3 scripts/fim_locate.py runs/hunyuan/<run> --list-only              # which names WOULD be queried, no network
    python3 scripts/fim_locate.py runs/hunyuan/<run>                          # look them up, rank the places
    python3 scripts/fim_locate.py runs/hunyuan/<run> --country <cc> --near "<region>, <country>"   # narrow when you know that much
    python3 scripts/fim_fetch_streets.py --from-locate runs/hunyuan/<run> --candidate 1 --slug <slug>   # then fetch the layer

No city, street or landmark name is built in; every decision is data on the sheet or a flag on this command line.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fim_crs import bbox_union, pad_bbox_km, utm_epsg_for  # noqa: E402
from fim_georef import DIRECTION_WORDS, FUSED_TYPE_WORDS, TYPE_WORDS, fold, load_block_rings, norm_label, street_candidates  # noqa: E402

UA = "fire-insurance-maps/0.1 (UVic research; fim_locate.py)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
LICENCE = "ODbL 1.0 — © OpenStreetMap contributors"
KM_PER_DEG = 111.32
# the long spelling of each type abbreviation, for the query ("ST" -> "STREET"); fused types spell themselves
TYPE_LONG: dict[str, str] = {}
for _k, _v in TYPE_WORDS.items():
    if len(_k) > len(TYPE_LONG.get(_v, "")):
        TYPE_LONG[_v] = _k
FUSED_TYPES = set(FUSED_TYPE_WORDS.values())
MUNICIPALITY_KEYS = ("city", "town", "village", "municipality", "city_district", "borough", "hamlet", "suburb")
BUSINESS_RE = re.compile(r"&|\b(CO|LTD|INC|BROS|SONS|MFG)\b\.?")  # company-form words, not place names
# map furniture and building vocabulary: a BARE word made of these names no street ("<NAME> BLK", "PROPOSED WHARF",
# "DISTRICT LOT"); with a type word the same word is a street ("WHARF ST") and is kept
FURNITURE_WORDS = {"BLK", "BLOCK", "BLDG", "BUILDING", "HOTEL", "HALL", "WHARF", "LOT", "LOTS", "DISTRICT", "TOWNSITE", "PROPOSED",
                   "OFFICIAL", "PLAN", "SCALE", "FEET", "SHEET", "KEY", "INDEX", "CITY", "TOWN", "VILLAGE", "LIMITS", "RESERVE",
                   # construction notes written on the buildings themselves
                   "ROOF", "SHINGLES", "SHINGLE", "WALL", "WALLS", "WHSE", "WAREHOUSE", "PLATFORM", "DRIVEWAY", "PREMISES", "STABLE",
                   "SHED", "OFFICE", "DWELLING", "DWG", "BRICK", "FRAME", "IRON", "STONE", "GLASS", "INCLINED", "BONDED", "VACANT",
                   "STORIES", "STORY", "BASEMENT", "CELLAR", "TANK", "BOILER", "ENGINE", "YARD", "FENCE", "STEPS", "PORCH", "VERANDAH"}


# ------------------------------------------------------------------------------------------------- tokens -> names
def load_run(run: Path) -> tuple[str, dict]:
    tiles_path = next(run.glob("*_tiles.json"), None)
    if tiles_path is None:
        raise SystemExit(f"{run}: no *_tiles.json (run fim_tile_ocr.py first)")
    return tiles_path.name[: -len("_tiles.json")], json.loads(tiles_path.read_text())


def kept_tokens(doc: dict) -> list[dict]:
    """The same keep-filter fim_georef.py applies: not a duplicate, fragment or conflict."""
    return [t for t in doc["tokens"] if t.get("dup_of") is None and not t.get("fragment") and not t.get("conflict")]


def sheet_type_word(tokens: list[dict]) -> str | None:
    """The type word this sheet uses most ('ST' on an English plan, 'GASSE' on a Viennese one), counted over every kept
    token that carries or IS one ('YATES ST.', a lone 'ST.'). A bare name is then asked for as '<Name> Street' — Nominatim
    answers a bare 'Yates' with places called Yates, not streets. None when the sheet shows no type words at all."""
    c: Counter = Counter()
    for t in tokens:
        name, typ = norm_label(t["text"])
        if typ:
            c[typ] += 1
        elif name in TYPE_WORDS:
            c[TYPE_WORDS[name]] += 1
    return c.most_common(1)[0][0] if c else None


def select_names(tokens: list[dict], *, min_len: int = 4, max_names: int = 25, bare: str = "repeated",
                 force: tuple[str, ...] = (), drop: tuple[str, ...] = (), default_type: str | None = None) -> tuple[list[dict], dict[str, list[str]]]:
    """Group the tokens into street-name queries, best first, and record why the rest were left out.

    Tiers: A has a type word ('<NAME> ST', '<NAME>gasse'); B is bare but repeated, or all-caps and 6+ letters; C is any
    other bare word. `bare` says which bare tiers are queried: none (A), repeated (A+B, default), all (A+B+C).
    Tokens already stamped in_block by street_candidates() are building labels and skipped first. A bare name is queried
    with default_type (the sheet's own dominant type word, see sheet_type_word) and recorded as type_assumed."""
    skipped: dict[str, list[str]] = {}

    def skip(reason: str, text: str) -> None:
        skipped.setdefault(reason, []).append(text)

    groups: dict[str, dict] = {}
    for t in tokens:
        text = t["text"].strip()
        if t.get("in_block"):
            skip("in_block", text)
            continue
        if not re.search(r"[A-Za-z]{3,}", fold(text)):
            skip("no_letters", text)
            continue
        name, typ = norm_label(text)
        if not name:
            skip("no_letters", text)
            continue
        if typ is None and all(wd in TYPE_WORDS or wd in DIRECTION_WORDS for wd in name.split()):
            skip("type_only", text)
            continue
        if typ is None and any(wd in FURNITURE_WORDS for wd in name.split()):
            skip("furniture", text)
            continue
        if BUSINESS_RE.search(fold(text).upper()) or len(name.split()) > 3:
            skip("business", text)
            continue
        if len(name.replace(" ", "")) < min_len:
            skip("short", text)
            continue
        if typ is None and re.search(r"\d", text):
            skip("digits", text)
            continue
        g = groups.setdefault(name, {"name": name, "typ": None, "texts": [], "token_ids": [], "n_upper": 0})
        g["texts"].append(text)
        g["token_ids"].append(t.get("id"))
        if typ and not g["typ"]:
            g["typ"] = typ
        letters = re.sub(r"[^A-Za-z]", "", fold(text))
        if letters and letters.isupper():
            g["n_upper"] += 1

    forced = {}
    for f in force:
        n, ty = norm_label(f)
        if n:
            forced[n] = ty
            g = groups.setdefault(n, {"name": n, "typ": ty, "texts": [f], "token_ids": [], "n_upper": 0})
            g["typ"] = g["typ"] or ty
    dropped = {norm_label(d)[0] for d in drop}

    allowed = {"none": {"A"}, "repeated": {"A", "B"}, "all": {"A", "B", "C"}}[bare]
    queries = []
    for g in groups.values():
        occ = len(g["texts"])
        upper_frac = g["n_upper"] / occ if occ else 0.0
        if g["name"] in dropped:
            skip("dropped", g["texts"][0])
            continue
        if g["name"] in forced:
            tier = "A"
        elif g["typ"]:
            tier = "A"
        elif occ >= 2 or (upper_frac == 1.0 and len(g["name"]) >= 6):
            tier = "B"
        else:
            tier = "C"
        if tier not in allowed:
            skip(f"bare_tier_{tier}", g["texts"][0])
            continue
        rank = 3 * (g["typ"] is not None) + 2 * upper_frac + min(occ - 1, 3) + len(g["name"]) / 4
        assumed = default_type if g["typ"] is None else None
        queries.append({"name": g["name"], "type": g["typ"], "type_assumed": assumed, "tier": tier, "occurrences": occ, "upper_frac": round(upper_frac, 2),
                        "token_ids": [i for i in g["token_ids"] if i is not None], "texts": g["texts"], "rank": round(rank, 2),
                        "query": build_query(g["name"], g["typ"] or assumed, g["texts"])})
    queries.sort(key=lambda q: (-q["rank"], q["name"]))
    for q in queries[max_names:]:
        skip("over_max", q["texts"][0])
    return queries[:max_names], skipped


def build_query(name: str, typ: str | None, texts: list[str] | None = None) -> str:
    """The string to ask Nominatim for: '<Name> Street' for spaced types; '<Name>gasse' / '<A>-<B>-Platz' for fused types
    (OSM's spelling; Nominatim does not match a spaced or hyphenated 'X-Gasse' to it); a bare name as title case."""
    if typ is None:
        return name.title()
    if typ in FUSED_TYPES:  # OSM writes these fused ('<Name>gasse') or hyphenated for multi-word names ('<A>-<B>-Platz');
        words = name.split()  # Nominatim does not equate 'X-Gasse' with 'Xgasse', so ask the way OSM spells it
        if len(words) == 1:
            return f"{words[0].title()}{typ.lower()}"
        return "-".join(w.title() for w in words) + "-" + typ.title()
    return f"{name.title()} {TYPE_LONG.get(typ, typ).title()}"


# ----------------------------------------------------------------------------------------------------- Nominatim
class Throttle:
    def __init__(self, sleep_s: float):
        self.sleep_s, self.last = sleep_s, 0.0

    def wait(self) -> None:
        dt = time.time() - self.last
        if dt < self.sleep_s:
            time.sleep(self.sleep_s - dt)
        self.last = time.time()


def nominatim_get(params: dict, throttle: Throttle, timeout: int = 30, retries: int = 3) -> list[dict]:
    url = NOMINATIM + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries + 1):
        throttle.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as ex:
            if ex.code in (429, 500, 502, 503, 504) and attempt < retries:
                print(f"  Nominatim HTTP {ex.code}; waiting {2 ** (attempt + 1)} s", file=sys.stderr)
                time.sleep(2 ** (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as ex:
            if attempt < retries:
                print(f"  Nominatim unreachable ({type(ex).__name__}); waiting {2 ** (attempt + 1)} s", file=sys.stderr)
                time.sleep(2 ** (attempt + 1))
                continue
            raise
    return []


def nominatim_bbox(raw: dict) -> tuple[float, float, float, float]:
    """Nominatim's boundingbox is [S, N, W, E] strings -> our S,W,N,E floats."""
    s, n, w, e = (float(v) for v in raw["boundingbox"])
    return s, w, n, e


def viewbox_param(bbox_swne) -> str:
    """Our S,W,N,E -> Nominatim's viewbox=W,N,E,S."""
    s, w, n, e = bbox_swne
    return f"{w},{n},{e},{s}"


def to_hit(name: str, raw: dict) -> dict:
    return {"name": name, "category": raw.get("category") or raw.get("class"), "type": raw.get("type"),
            "lat": float(raw["lat"]), "lon": float(raw["lon"]), "bbox_swne": list(nominatim_bbox(raw)),
            "display_name": raw.get("display_name", ""), "address": raw.get("address") or {},
            "osm_type": raw.get("osm_type"), "osm_id": raw.get("osm_id"), "importance": raw.get("importance")}


def filter_hits(name: str, raw: list[dict], classes: set[str] | None) -> list[dict]:
    return [to_hit(name, r) for r in raw if classes is None or (r.get("category") or r.get("class")) in classes]


class Cache:
    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text()) if path.exists() else {}
        self.requests = self.from_cache = 0

    def get(self, params: dict, throttle: Throttle, refresh: bool) -> list[dict]:
        key = json.dumps(params, sort_keys=True)
        if key in self.data and not refresh:
            self.from_cache += 1
            return self.data[key]["results"]
        raw = nominatim_get(params, throttle)
        self.requests += 1
        self.data[key] = {"utc": datetime.now(timezone.utc).isoformat(), "results": raw}
        self.path.write_text(json.dumps(self.data))  # after every request: a crash keeps what was answered
        return raw


def lookup_all(queries: list[dict], base: dict, cache: Cache, throttle: Throttle, classes: set[str] | None, limit: int, refresh: bool) -> dict[str, list[dict]]:
    hits_by_name: dict[str, list[dict]] = {}
    failures = 0
    for q in queries:
        try:
            raw = cache.get(dict(base, q=q["query"]), throttle, refresh)
            hits = filter_hits(q["name"], raw, classes)
            q["query_used"] = q["query"]
            bare = q["name"].title()
            if not hits and q["query"] != bare:  # the typed form found no road: try the bare name once
                raw2 = cache.get(dict(base, q=bare), throttle, refresh)
                hits2 = filter_hits(q["name"], raw2, classes)
                if hits2:
                    raw, hits, q["query_used"] = raw2, hits2, bare
            failures = 0
        except Exception as ex:  # noqa: BLE001 — one name failing must not lose the others
            failures += 1
            q.update({"query_used": q["query"], "n_hits_raw": 0, "n_hits_kept": 0, "saturated": False, "error": f"{type(ex).__name__}: {str(ex)[:80]}"})
            print(f"  {q['name']:<24s} {q['query']!r}: request failed ({q['error']})", file=sys.stderr)
            if failures >= 3:
                raise SystemExit(f"Nominatim unreachable or rate-limited three times in a row; {cache.requests} answers so far are kept in {cache.path} — re-run later")
            continue
        q.update({"n_hits_raw": len(raw), "n_hits_kept": len(hits), "saturated": len(raw) >= limit})
        hits_by_name[q["name"]] = hits
        print(f"  {q['name']:<24s} {q['query_used']!r:<32s} {len(raw):3d} hits, {len(hits):3d} kept" + ("  (saturated)" if q["saturated"] else ""))
    return hits_by_name


# ------------------------------------------------------------------------------------------------------ scoring
def km_matrix(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Pairwise equirectangular distances in km (exact enough for the few-km radii used here)."""
    la = np.radians(lat)
    dlat = (lat[:, None] - lat[None, :]) * KM_PER_DEG
    dlon = (lon[:, None] - lon[None, :]) * KM_PER_DEG * np.cos((la[:, None] + la[None, :]) / 2)
    return np.hypot(dlat, dlon)


def n_places(hits: list[dict], radius_km: float) -> int:
    """How many distinct places (groups of hits within radius_km) a name occurs in. Nominatim returns one result per
    way segment, so a street unique to one city may come back as forty hits — that is ONE place."""
    if not hits:
        return 0
    D = km_matrix(np.array([h["lat"] for h in hits], float), np.array([h["lon"] for h in hits], float))
    alive = np.ones(len(hits), bool)
    count = 0
    while alive.any():
        i = int(np.flatnonzero(alive)[0])
        alive &= ~(D[i] <= radius_km)
        count += 1
    return count


def name_weight(places: int) -> float:
    """A name that exists in one place is strong evidence; one that exists in forty weighs 1/sqrt(40)."""
    return 1.0 / math.sqrt(max(places, 1))


def name_weights(hits_by_name: dict[str, list[dict]], radius_km: float) -> dict[str, float]:
    return {n: name_weight(n_places(hs, radius_km)) for n, hs in hits_by_name.items()}


def cluster_hits(hits_by_name: dict[str, list[dict]], *, radius_km: float = 6.0, max_candidates: int = 8, min_names: int = 2) -> list[dict]:
    """Greedy seed clustering: the hit with the highest weighted count of distinct names within radius_km seeds a candidate;
    one single-link step then pulls in hits of names not yet present that lie within the radius of any member (so a sheet
    across a municipal line becomes one candidate without letting a chain crawl across a region). Members are removed
    and the search repeats. Returned best first."""
    names = [n for n, hs in hits_by_name.items() if hs]
    if not names:
        return []
    pts = [(h, i) for i, n in enumerate(names) for h in hits_by_name[n]]
    lat = np.array([h["lat"] for h, _ in pts], float)
    lon = np.array([h["lon"] for h, _ in pts], float)
    idx = np.array([i for _, i in pts], int)
    weights = name_weights(hits_by_name, radius_km)
    w = np.array([weights[n] for n in names], float)
    H, N = len(pts), len(names)
    D = km_matrix(lat, lon)
    onehot = np.zeros((H, N), float)
    onehot[np.arange(H), idx] = 1.0
    alive = np.ones(H, bool)
    out = []
    while len(out) < max_candidates:
        within = (D <= radius_km) & alive[None, :] & alive[:, None]
        present = (within.astype(float) @ onehot) > 0  # (H, N): names within the radius of each seed
        score = present @ w
        score[~alive | (present.sum(1) < min_names)] = -1.0  # a lone rare name is not a place, and must not stop the search
        s = int(score.argmax())
        if score[s] <= 0:
            break
        members = within[s].copy()
        near_any = (D[members] <= radius_km).any(0) & alive
        members |= near_any & (~present[s])[idx]
        mem_names = np.unique(idx[members])
        hits = [pts[i][0] for i in np.flatnonzero(members)]
        out.append({"score": float(w[mem_names].sum()), "n_names": int(len(mem_names)), "n_hits": int(members.sum()),
                    "names": [names[i] for i in mem_names], "hits": hits,
                    "centre_latlon": [float(np.median(lat[members])), float(np.median(lon[members]))]})
        alive &= ~members
    out.sort(key=lambda c: (-c["score"], -c["n_names"], c["n_hits"], bbox_area_km2(candidate_bbox(c["hits"], 0.0)[0])))
    return out


def bbox_area_km2(b) -> float:
    s, w, n, e = b
    return abs((n - s) * KM_PER_DEG * (e - w) * KM_PER_DEG * math.cos(math.radians((s + n) / 2)))


def candidate_bbox(hits: list[dict], pad_km: float, max_hit_diag_km: float = 5.0) -> tuple[tuple, tuple]:
    """Union of the supporting hits' own boxes (a street's extent is useful) — but a hit whose box is longer than
    max_hit_diag_km (a highway) contributes its point only — then padded. Returns (raw, padded)."""
    boxes = []
    for h in hits:
        s, w, n, e = h["bbox_swne"]
        diag = math.hypot((n - s) * KM_PER_DEG, (e - w) * KM_PER_DEG * math.cos(math.radians((s + n) / 2)))
        boxes.append((s, w, n, e) if diag < max_hit_diag_km else (h["lat"], h["lon"], h["lat"], h["lon"]))
    raw = bbox_union(boxes)
    return raw, pad_bbox_km(raw, pad_km)


def verify_candidates(cands: list[dict], queries: list[dict], hits_by_name: dict[str, list[dict]], base: dict, cache: "Cache", throttle: "Throttle",
                      classes: set[str] | None, radius_km: float, top_n: int, refresh: bool) -> None:
    """Ask Nominatim, for each of the top_n candidates, whether each name NOT yet supporting it exists inside the candidate's
    box (a bounded search, which also finds '<Direction> <Name> Street' spellings the global search ranked out). Confirmed
    names join the candidate; scores are recomputed and the list re-sorted. This is what turns a coarse global ranking into
    a count of the sheet's streets actually present at each place."""
    if not cands or top_n <= 0:
        return
    weights = name_weights(hits_by_name, radius_km)
    for c in cands[:top_n]:
        raw_box, _ = candidate_bbox(c["hits"], 0.0)
        box = pad_bbox_km(raw_box, radius_km)
        c["verified"] = []
        line = []
        for q in queries:
            if q["name"] in c["names"] or q.get("error"):
                continue
            params = dict(base, q=q["query"], viewbox=viewbox_param(box), bounded=1, limit=10)
            hs = filter_hits(q["name"], cache.get(params, throttle, refresh), classes)
            if not hs and q["query"] != q["name"].title():
                hs = filter_hits(q["name"], cache.get(dict(params, q=q["name"].title()), throttle, refresh), classes)
            line.append(f"{q['name']} {'yes' if hs else 'no'}")
            if hs:
                c["hits"].extend(hs)
                c["names"].append(q["name"])
                c["verified"].append(q["name"])
        c["score"] = float(sum(weights.get(n) or 1.0 for n in c["names"]))  # a name the global search never found anywhere is rare: weight 1
        c["n_names"], c["n_hits"] = len(c["names"]), len(c["hits"])
        print(f"  verify {describe_place(c['hits'])['description'][:40]:<40s} +{len(c['verified'])} names: " + ", ".join(line))
    cands.sort(key=lambda c: (-c["score"], -c["n_names"], c["n_hits"]))


def core_of(hits: list[dict], weights: dict[str, float], core_km: float) -> dict:
    """The densest spot of a candidate: the hit around which, within core_km, the most distinct names lie (weighted).
    A fire-insurance sheet covers a compact area, so this — not the count over a whole metropolis, where nearly every
    common street name exists somewhere — is what ranks candidates. Returns the core's hits, names and score."""
    lat = np.array([h["lat"] for h in hits], float)
    lon = np.array([h["lon"] for h in hits], float)
    D = km_matrix(lat, lon)
    best, best_score = None, -1.0
    for i in range(len(hits)):
        near = D[i] <= core_km
        names = {hits[j]["name"] for j in np.flatnonzero(near)}
        sc = sum(weights.get(n) or 1.0 for n in names)
        if sc > best_score:
            best, best_score = near, sc
    core_hits = [hits[j] for j in np.flatnonzero(best)]
    return {"hits": core_hits, "names": sorted({h["name"] for h in core_hits}), "score": float(best_score)}


def merge_overlapping(cands: list[dict], weights: dict[str, float]) -> list[dict]:
    """Two candidates whose hit boxes intersect are one place found twice (a city split by the greedy clustering)."""
    out: list[dict] = []
    for c in cands:
        b = candidate_bbox(c["hits"], 0.0)[0]
        for o in out:
            ob = candidate_bbox(o["hits"], 0.0)[0]
            if b[0] <= ob[2] and ob[0] <= b[2] and b[1] <= ob[3] and ob[1] <= b[3]:
                o["hits"].extend(c["hits"])
                o["names"] = list(dict.fromkeys(o["names"] + c["names"]))
                o["verified"] = list(dict.fromkeys(o.get("verified", []) + c.get("verified", [])))
                o["score"] = float(sum(weights.get(n) or 1.0 for n in o["names"]))
                o["n_names"], o["n_hits"] = len(o["names"]), len(o["hits"])
                break
        else:
            out.append(c)
    return out


def describe_place(hits: list[dict]) -> dict:
    """Majority vote over the hits' address fields; up to two municipalities ('A / B' is what a sheet across a boundary
    looks like). No extra request."""
    munis, county, state, country, cc = Counter(), Counter(), Counter(), Counter(), Counter()
    for h in hits:
        a = h.get("address") or {}
        m = next((a[k] for k in MUNICIPALITY_KEYS if a.get(k)), None)
        if m:
            munis[m] += 1
        for key, c in (("county", county), ("state", state), ("country", country), ("country_code", cc)):
            if a.get(key):
                c[a[key]] += 1
    top = munis.most_common(2)
    municipalities = [top[0][0]] if top else []
    if len(top) == 2 and top[1][1] >= max(2, 0.2 * sum(munis.values())):
        municipalities.append(top[1][0])
    pick = lambda c: c.most_common(1)[0][0] if c else None
    place = {"municipalities": municipalities, "county": pick(county), "state": pick(state), "country": pick(country), "country_code": pick(cc)}
    place["description"] = ", ".join(x for x in [" / ".join(municipalities), place["state"], place["country"]] if x) or "(no address details returned)"
    return place


def slug_for(place: dict) -> str:
    base = place["municipalities"][0] if place["municipalities"] else (place.get("county") or place.get("state") or "")
    s = re.sub(r"[^a-z0-9]+", "_", fold(base).lower()).strip("_")
    return (s + "_locate") if s else "locate"


def fetch_command(bbox_swne, slug: str) -> str:
    s, w, n, e = bbox_swne
    return f"python3 scripts/fim_fetch_streets.py --bbox {s:.4f},{w:.4f},{n:.4f},{e:.4f} --slug {slug}"


# --------------------------------------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="fim_tile_ocr.py output dir (needs <stem>_tiles.json; uses <stem>_blocks_px.geojson if present)")
    sel = ap.add_argument_group("which names to look up")
    sel.add_argument("--list-only", action="store_true", help="print the names that would be queried, with tiers and skip reasons, and stop before any request")
    sel.add_argument("--min-len", type=int, default=4, help="shortest name (letters) worth a global search (default 4)")
    sel.add_argument("--max-names", type=int, default=25, help="how many names to look up, best first (default 25; about one request per second)")
    sel.add_argument("--bare", choices=["none", "repeated", "all"], default="repeated", help="bare words (no type word): none | repeated or all-caps 6+ letters (default) | all")
    sel.add_argument("--name", action="append", default=[], metavar="TEXT", help="force a name in (repeatable), e.g. one you can read that the OCR missed")
    sel.add_argument("--drop", action="append", default=[], metavar="TEXT", help="leave a name out (repeatable)")
    sel.add_argument("--ignore-blocks", action="store_true", help="do not use the traced blocks to drop building labels")
    sel.add_argument("--min-names", type=int, default=3, help="fewer queryable names than this: say so and stop (default 3)")
    net = ap.add_argument_group("Nominatim")
    net.add_argument("--country", default=None, metavar="CC[,CC]", help="restrict to ISO country codes, if you know that much")
    net.add_argument("--near", default=None, metavar="S,W,N,E | 'place'", help="restrict to a box, or to a geocoded region padded by --near-pad-km")
    net.add_argument("--near-pad-km", type=float, default=15.0, help="padding around a geocoded --near region (default 15; a municipality's own box would cut off a sheet that crosses its line)")
    net.add_argument("--lang", default=None, help="accept-language for returned names (default: unset, local names)")
    net.add_argument("--limit", type=int, default=40, help="results per name (default 40, Nominatim's cap is 50)")
    net.add_argument("--classes", default="highway", help="OSM classes kept, comma list, or 'any' (default highway)")
    net.add_argument("--sleep", type=float, default=1.1, help="seconds between requests (default 1.1; Nominatim asks for at most one per second)")
    net.add_argument("--refresh", action="store_true", help="ignore the request cache")
    sc = ap.add_argument_group("scoring")
    sc.add_argument("--radius-km", type=float, default=6.0, help="hits within this distance support one candidate (default 6)")
    sc.add_argument("--pad-km", type=float, default=1.0, help="padding of each candidate's box (default 1)")
    sc.add_argument("--max-candidates", type=int, default=8)
    sc.add_argument("--verify", type=int, default=5, metavar="N", help="for the N best candidates, ask whether each missing name exists inside the candidate's box (one bounded request per name; default 5, 0 = off)")
    sc.add_argument("--core-km", type=float, default=1.5, help="a sheet is compact: candidates are ranked by the names that lie within this radius of one spot, and the proposed box is built from that spot (default 1.5; raise for a key plan covering a whole town)")
    args = ap.parse_args()

    run = args.run
    stem, doc = load_run(run)
    tokens = kept_tokens(doc)
    block_rings = [] if args.ignore_blocks else load_block_rings(run, stem)
    street_candidates(tokens, block_rings)  # stamps in_block on every token
    if block_rings:
        print(f"{stem}: {len(tokens)} kept tokens; {sum(1 for t in tokens if t['in_block'])} inside the {len(block_rings)} traced blocks (building labels, skipped)")
    else:
        print(f"{stem}: {len(tokens)} kept tokens; no traced blocks{' (--ignore-blocks)' if args.ignore_blocks else ' beside the tiles JSON (run fim_blocks.py to drop building labels)'} — pattern rules only")

    default_type = sheet_type_word(tokens)
    print(f"type word the sheet uses most: {default_type or 'none'}" + (f" -> a bare name is asked for as '<Name> {TYPE_LONG.get(default_type, default_type).title()}' first" if default_type else ""))
    queries, skipped = select_names(tokens, min_len=args.min_len, max_names=args.max_names, bare=args.bare, force=tuple(args.name), drop=tuple(args.drop), default_type=default_type)
    print(f"{len(queries)} names to look up; skipped: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(skipped.items())))
    for q in queries:
        print(f"  {q['tier']}  {q['name']:<24s} x{q['occurrences']:<3d} -> {q['query']!r}")
    out_path = run / f"{stem}_locate.json"
    params = {"radius_km": args.radius_km, "pad_km": args.pad_km, "verify": args.verify, "sheet_type_word": default_type, "min_len": args.min_len, "max_names": args.max_names, "bare": args.bare,
              "classes": args.classes, "sleep": args.sleep, "country": args.country, "near": args.near, "lang": args.lang, "limit": args.limit, "ignore_blocks": args.ignore_blocks}
    result = {"sheet": stem, "run": str(run), "generated_utc": datetime.now(timezone.utc).isoformat(),
              "service": {"name": "nominatim", "endpoint": NOMINATIM, "user_agent": UA, "licence": LICENCE},
              "params": params, "names": queries, "skipped": skipped, "candidates": [], "selected": None}
    if args.list_only:
        print("--list-only: no request made. Adjust with --bare / --min-len / --name / --drop, then run again without it.")
        return
    if len(queries) < args.min_names:
        out_path.write_text(json.dumps(result, indent=1, ensure_ascii=False))
        raise SystemExit(f"only {len(queries)} street-like names on this sheet (< --min-names {args.min_names}), not enough to locate it; "
                         f"try --bare all, --min-len 3, or --name <a street you can read>. Written: {out_path}")

    base = {"format": "jsonv2", "addressdetails": 1, "limit": args.limit, "dedupe": 1}
    if args.country:
        base["countrycodes"] = args.country.lower()
    if args.lang:
        base["accept-language"] = args.lang
    throttle = Throttle(args.sleep)
    cache = Cache(run / f"{stem}_locate_cache.json")
    if args.near:
        if re.fullmatch(r"\s*-?[\d.]+\s*,\s*-?[\d.]+\s*,\s*-?[\d.]+\s*,\s*-?[\d.]+\s*", args.near):
            near = tuple(float(v) for v in args.near.split(","))
        else:
            hits = cache.get({"format": "jsonv2", "limit": 1, "q": args.near}, throttle, args.refresh)
            if not hits:
                raise SystemExit(f"--near {args.near!r}: Nominatim found nothing")
            near = pad_bbox_km(nominatim_bbox(hits[0]), args.near_pad_km)
            print(f"--near {args.near!r} -> {hits[0].get('display_name', '')}, padded {args.near_pad_km:.0f} km -> S{near[0]:.3f} W{near[1]:.3f} N{near[2]:.3f} E{near[3]:.3f}")
        base["viewbox"], base["bounded"] = viewbox_param(near), 1
        result["params"]["near_bbox_swne"] = list(near)
    classes = None if args.classes.strip().lower() == "any" else {c.strip() for c in args.classes.split(",") if c.strip()}

    print(f"looking up {len(queries)} names in Nominatim ({args.sleep:.1f} s apart; cached answers are free):")
    hits_by_name = lookup_all(queries, base, cache, throttle, classes, args.limit, args.refresh)
    print(f"{cache.requests} requests made, {cache.from_cache} answered from {cache.path.name}")
    weights = name_weights(hits_by_name, args.radius_km)
    for q in queries:
        q["n_places"] = n_places(hits_by_name.get(q["name"]) or [], args.radius_km)
        q["weight"] = round(weights[q["name"]], 3) if q["name"] in weights else None

    cands = cluster_hits(hits_by_name, radius_km=args.radius_km, max_candidates=args.max_candidates, min_names=2)
    if cands and args.verify:
        print(f"verifying the {min(args.verify, len(cands))} best candidates (are the other names there too?):")
        verify_candidates(cands, queries, hits_by_name, base, cache, throttle, classes, args.radius_km, args.verify, args.refresh)
        print(f"{cache.requests} requests made in total, {cache.from_cache} answered from {cache.path.name}")
    answered = [q["name"] for q in queries if q.get("n_hits_kept")]
    cands = merge_overlapping(cands, weights)
    for c in cands:
        c["core"] = core_of(c["hits"], weights, args.core_km)
    cands.sort(key=lambda c: (-c["core"]["score"], -c["score"], -c["n_names"], c["n_hits"]))
    for r, c in enumerate(cands, 1):
        core = c.pop("core")
        all_box = candidate_bbox(c["hits"], 0.0)[0]
        raw_box, box = candidate_bbox(core["hits"], args.pad_km)
        place = describe_place(core["hits"])
        slug = slug_for(place)
        present = set(c["names"])
        missing = [{"name": q["name"], "reason": "no hits anywhere" if not q.get("n_hits_kept") else ("saturated" if q.get("saturated") else "elsewhere")}
                   for q in queries if q["name"] not in present]
        c.setdefault("verified", [])
        c.update({"rank": r, "core_km": args.core_km, "core_score": round(core["score"], 3), "core_names": core["names"],
                  "bbox_swne": [round(v, 5) for v in raw_box], "bbox_padded_swne": [round(v, 5) for v in box], "bbox_all_hits_swne": [round(v, 5) for v in all_box],
                  "utm_epsg": utm_epsg_for((box[1] + box[3]) / 2, (box[0] + box[2]) / 2), "place": place, "description": place["description"],
                  "suggested_slug": slug, "fetch_command": fetch_command(box, slug),
                  "supporting": [{k: h[k] for k in ("name", "osm_type", "osm_id", "lat", "lon", "display_name")} for h in c["hits"]], "missing": missing})
        del c["hits"]
    result["candidates"] = cands
    out_path.write_text(json.dumps(result, indent=1, ensure_ascii=False))

    if not cands:
        print(f"no place where two or more of the {len(answered)} answered names meet within {args.radius_km:.0f} km. Each name's best hits, to reason by hand:")
        for q in queries:
            for h in (hits_by_name.get(q["name"]) or [])[:3]:
                print(f"  {q['name']:<24s} {h['lat']:9.4f} {h['lon']:10.4f}  {h['display_name'][:90]}")
        print(f"Written: {out_path}. Try --radius-km larger, --bare all, or --country / --near if you know that much.")
        return
    print()
    print(f"{'#':>2} {'core':>6} {'within':>7} {'names':>7}  {'place':<44s} bbox S,W,N,E of the core, padded {args.pad_km:.1f} km   UTM")
    print(f"{'':>2} {'score':>6} {f'{args.core_km:g} km':>7} {'in box':>7}")
    for c in cands:
        b = c["bbox_padded_swne"]
        print(f"{c['rank']:>2} {c['core_score']:6.2f} {len(c['core_names']):>3}/{len(queries):<3} {c['n_names']:>3}/{len(queries):<3}  {c['description'][:44]:<44s} {b[0]:.4f},{b[1]:.4f},{b[2]:.4f},{b[3]:.4f}  EPSG:{c['utm_epsg']}")
        core_set = set(c["core_names"])
        print(f"   core:    {', '.join(n + ('*' if n in c['verified'] else '') for n in c['names'] if n in core_set)}" + ("   (* confirmed by a bounded search)" if core_set & set(c["verified"]) else ""))
        far = [n for n in c["names"] if n not in core_set]
        if far:
            print(f"   farther: {', '.join(n + ('*' if n in c['verified'] else '') for n in far)}")
        if c["missing"]:
            miss = ", ".join(m["name"] + ("" if m["reason"] == "elsewhere" else f" ({m['reason']})") for m in c["missing"])
            print(f"   missing: {miss}")
        print(f"   {c['fetch_command']}")
    print(f"\nA fire-insurance sheet is compact: the 'core' is the spot where most of its names lie within {args.core_km:g} km; the box is that spot padded, not the whole city (--pad-km / --core-km grow it).")
    print(f"Nothing was fetched or chosen. Copy the command of the candidate you recognise (or: fim_fetch_streets.py --from-locate {run} --candidate N --slug <slug>),")
    print(f"or narrow with --country / --near and run again. Written: {out_path}")


if __name__ == "__main__":
    main()
