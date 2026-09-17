#!/usr/bin/env python3
"""
Fetch modern named street centrelines for any area, as the reference layer for fim_georef.py.

Two sources:
  OpenStreetMap (default) — every named `highway=*` way in a bounding box, via the Overpass API (several public
      mirrors are tried in turn). Works for any city. Names are OSM's full names ("<Name> Street").
  --arcgis <layer URL>     — a municipal ArcGIS MapServer/FeatureServer layer (a city's open-data "Streets" /
      "Road centrelines" layer), queried by envelope and paged past the transfer limit. All fields are kept;
      fim_georef.py auto-detects the name field or takes --name-field.

The area is a bounding box, never an administrative unit, so a sheet that crosses a municipal line is served like
any other. The box comes from --bbox S,W,N,E (WGS84 degrees); from one or more --place "<city, region>" (Nominatim
geocoder; several places are unioned); or from a fim_locate.py proposal (--from-locate <run> --candidate N, for a
sheet whose location was worked out from its own street names). --pad-km grows any of them.
Output is a GeoJSON FeatureCollection of LineStrings in a metric projected CRS — the UTM zone of the box centre unless
--epsg says otherwise — with a `crs` member so fim_georef.py knows what it is reading, written to
data/modern/<slug>_streets_epsg<code>.geojson.

    python3 scripts/fim_fetch_streets.py --place "<city, region>" --slug <city>_osm
    python3 scripts/fim_fetch_streets.py --place "<city>, <region>" --place "<neighbouring town>, <region>" --pad-km 1 --slug <area>_osm
    python3 scripts/fim_fetch_streets.py --bbox <S>,<W>,<N>,<E> --slug <city>_core
    python3 scripts/fim_fetch_streets.py --from-locate runs/hunyuan/<run> --candidate 1 --slug <slug>
    python3 scripts/fim_fetch_streets.py --bbox <S>,<W>,<N>,<E> --slug <city>_muni [--epsg <code>] \
        --arcgis https://<city gis host>/arcgis/rest/services/<service>/MapServer/<layer>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fim_crs import CRS, bbox_union, pad_bbox_km, utm_epsg_for  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UA = "fire-insurance-maps/0.1 (UVic research; fim_fetch_streets.py)"
OVERPASS_MIRRORS = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"]
# ways that are never a mapped street on a fire-insurance plan
OSM_EXCLUDE = {"footway", "path", "steps", "cycleway", "track", "bridleway", "corridor", "elevator", "platform", "bus_stop", "proposed", "construction", "raceway", "via_ferrata"}


def http(url: str, data: bytes | None = None, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


_LAST_GEOCODE = [0.0]


def geocode(place: str) -> tuple[float, float, float, float]:
    dt = time.time() - _LAST_GEOCODE[0]  # Nominatim asks for at most one request per second
    if dt < 1.1:
        time.sleep(1.1 - dt)
    _LAST_GEOCODE[0] = time.time()
    q = urllib.parse.urlencode({"q": place, "format": "json", "limit": 1})
    hits = json.loads(http(f"https://nominatim.openstreetmap.org/search?{q}", timeout=30))
    if not hits:
        raise SystemExit(f"Nominatim found nothing for {place!r}")
    s, n, w, e = (float(v) for v in hits[0]["boundingbox"])
    print(f"{place!r} -> {hits[0]['display_name']}  bbox S{s:.4f} W{w:.4f} N{n:.4f} E{e:.4f}")
    return s, w, n, e


def parse_bbox(text: str) -> tuple[float, float, float, float]:
    parts = tuple(float(v) for v in text.split(","))
    if len(parts) != 4 or not (parts[0] < parts[2] and parts[1] < parts[3]):
        raise SystemExit("--bbox must be S,W,N,E with S<N and W<E")
    return parts


def locate_candidate(run: Path, n: int) -> dict:
    """Candidate n (1-based) from the <stem>_locate.json fim_locate.py wrote in a run dir."""
    path = next(run.glob("*_locate.json"), None)
    if path is None:
        raise SystemExit(f"{run}: no *_locate.json (run fim_locate.py first)")
    cands = json.loads(path.read_text()).get("candidates") or []
    if not 1 <= n <= len(cands):
        raise SystemExit(f"{path} has {len(cands)} candidate(s); --candidate must be 1..{len(cands)}")
    c = cands[n - 1]
    c["_path"] = str(path)
    return c


def resolve_bbox(args) -> tuple[tuple[float, float, float, float], dict]:
    """(S,W,N,E, where it came from) for --bbox | --place [--place ...] | --from-locate + --candidate, then --pad-km."""
    if args.bbox:
        bbox, origin = parse_bbox(args.bbox), {"bbox": args.bbox}
    elif args.place:
        boxes = [geocode(p) for p in args.place]
        bbox, origin = bbox_union(boxes), {"place": list(args.place)}
        if len(boxes) > 1:
            print(f"union of {len(boxes)} places: S{bbox[0]:.4f} W{bbox[1]:.4f} N{bbox[2]:.4f} E{bbox[3]:.4f}")
    else:
        c = locate_candidate(args.from_locate, args.candidate)
        bbox = tuple(float(v) for v in c["bbox_padded_swne"])
        origin = {"locate": c["_path"], "candidate": args.candidate, "description": c.get("description"), "names": c.get("names")}
        print(f"fim_locate candidate {args.candidate}: {c.get('description')} — {c.get('n_names')} names ({', '.join(c.get('names') or [])})")
        print(f"  box S{bbox[0]:.4f} W{bbox[1]:.4f} N{bbox[2]:.4f} E{bbox[3]:.4f} (fim_locate's padded box)")
    if args.pad_km:
        bbox = pad_bbox_km(bbox, args.pad_km)
        print(f"padded {args.pad_km:g} km: S{bbox[0]:.4f} W{bbox[1]:.4f} N{bbox[2]:.4f} E{bbox[3]:.4f}")
    return bbox, origin


def fetch_osm(bbox: tuple[float, float, float, float], exclude: set[str], timeout: int) -> list[dict]:
    s, w, n, e = bbox
    query = f'[out:json][timeout:{timeout}];way["highway"]["name"]({s},{w},{n},{e});out geom;'
    last = None
    for url in OVERPASS_MIRRORS:
        t0 = time.time()
        try:
            raw = http(url, data=urllib.parse.urlencode({"data": query}).encode(), timeout=timeout + 30)
            ways = json.loads(raw).get("elements", [])
            print(f"{url}: {len(ways)} named ways in {time.time() - t0:.1f}s")
            feats = []
            for wy in ways:
                tags = wy.get("tags", {})
                if tags.get("highway") in exclude or "geometry" not in wy:
                    continue
                feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in wy["geometry"]]},
                              "properties": {"name": tags["name"], "highway": tags.get("highway"), "osm_id": wy["id"], "alt_name": tags.get("alt_name"), "old_name": tags.get("old_name"), "official_name": tags.get("official_name")}})
            return feats
        except Exception as ex:  # noqa: BLE001 — try the next mirror
            last = ex
            print(f"{url}: failed ({type(ex).__name__}: {str(ex)[:80]}), trying next mirror", file=sys.stderr)
    raise SystemExit(f"all Overpass mirrors failed; last error: {last}")


def fetch_arcgis(layer_url: str, bbox: tuple[float, float, float, float], epsg: int, timeout: int) -> list[dict]:
    """Envelope query in WGS84, geometry returned in `epsg`; pages with resultOffset until exceededTransferLimit clears."""
    s, w, n, e = bbox
    feats, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"where": "1=1", "geometry": f"{w},{s},{e},{n}", "geometryType": "esriGeometryEnvelope", "inSR": 4326, "outSR": epsg, "outFields": "*", "returnGeometry": "true", "f": "geojson", "resultOffset": offset})
        d = json.loads(http(f"{layer_url.rstrip('/')}/query?{q}", timeout=timeout))
        if "error" in d:
            raise SystemExit(f"ArcGIS error: {d['error']}")
        page = d.get("features", [])
        feats.extend(f for f in page if f.get("geometry") and f["geometry"]["type"] in ("LineString", "MultiLineString"))
        more = d.get("properties", {}).get("exceededTransferLimit") or d.get("exceededTransferLimit")
        print(f"{layer_url}: {len(page)} features at offset {offset}" + (" (more)" if more else ""))
        if not more or not page:
            break
        offset += len(page)
    # split MultiLineStrings so downstream sees LineStrings only
    out = []
    for f in feats:
        if f["geometry"]["type"] == "MultiLineString":
            for part in f["geometry"]["coordinates"]:
                out.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": part}, "properties": f["properties"]})
        else:
            out.append(f)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--bbox", help="S,W,N,E in WGS84 degrees")
    g.add_argument("--place", action="append", help="place name for the Nominatim geocoder, '<city>, <region>' (its bounding box is used); repeat for the union of several")
    g.add_argument("--from-locate", type=Path, metavar="RUN", help="a run dir holding fim_locate.py's <stem>_locate.json; needs --candidate")
    ap.add_argument("--candidate", type=int, default=None, metavar="N", help="which fim_locate candidate to take (1 = best); required with --from-locate, so the choice is yours")
    ap.add_argument("--pad-km", type=float, default=0.0, help="grow the box this many km on every side (default 0)")
    ap.add_argument("--slug", required=True, help="output name: data/modern/<slug>_streets_epsg<code>.geojson")
    ap.add_argument("--epsg", type=int, default=None, help="projected CRS for the output (default: WGS84 UTM zone of the box centre, e.g. 32610)")
    ap.add_argument("--arcgis", default=None, help="ArcGIS MapServer/FeatureServer layer URL to query instead of OpenStreetMap")
    ap.add_argument("--exclude", default=",".join(sorted(OSM_EXCLUDE)), help="OSM highway values to drop (default: footways, paths, steps, cycleways, ...)")
    ap.add_argument("--timeout", type=int, default=120, help="seconds per request (default 120)")
    ap.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "data/modern")
    args = ap.parse_args()

    if (args.from_locate is None) != (args.candidate is None):
        ap.error("--from-locate and --candidate go together")
    bbox, origin = resolve_bbox(args)
    epsg = args.epsg or utm_epsg_for((bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2)
    crs = CRS(epsg)

    if args.arcgis:
        feats = fetch_arcgis(args.arcgis, bbox, epsg, args.timeout)
        source = {"kind": "arcgis", "layer": args.arcgis}
    else:
        feats = fetch_osm(bbox, set(v for v in args.exclude.split(",") if v), args.timeout)
        source = {"kind": "openstreetmap", "overpass": OVERPASS_MIRRORS, "licence": "ODbL 1.0 — © OpenStreetMap contributors"}
        for f in feats:  # project lon/lat -> metric
            c = np.array(f["geometry"]["coordinates"], float)
            x, y = crs.from_wgs84(c[:, 0], c[:, 1])
            f["geometry"]["coordinates"] = [[round(float(a), 3), round(float(b), 3)] for a, b in zip(x, y)]
    if not feats:
        raise SystemExit("no street features returned")

    out = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": f"urn:ogc:def:crs:EPSG::{epsg}"}}, "epsg": epsg, "crs_name": crs.name(),
           "source": source, "bbox_wgs84_swne": list(bbox), "bbox_origin": origin, "pad_km": args.pad_km, "fetched_utc": datetime.now(timezone.utc).isoformat(), "features": feats}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    path = args.out_dir / f"{args.slug}_streets_epsg{epsg}.geojson"
    path.write_text(json.dumps(out))
    names = {f["properties"].get("name") or f["properties"].get("StreetName") or f["properties"].get("STNAME") or f["properties"].get("STRUCTURED_NAME_1") or f["properties"].get("FULLNAME") for f in feats}
    print(f"{len(feats)} segments, {len(names)} distinct names, {crs.name()} -> {path}")


if __name__ == "__main__":
    main()
