#!/usr/bin/env python3
"""
Download a digitised map from the Library of Congress (loc.gov) with its provenance, for any city.

Give it any of the ways LOC points at a resource — the handle (hdl.loc.gov/loc.gmd/<id>), the resource page
(www.loc.gov/resource/<id>/?sp=N...), or the bare id (g3934tm.g3934tm_g013521884) — and it fetches every sheet
of that resource. The Library serves a JPEG 2000 master (.jp2, ~10 MB, which ordinary image viewers do not open); that is
downloaded to a temporary file, decoded once to a full-resolution lossless PNG (or --convert tif), and then deleted, so what
stays on disk is <stem>-NNNN.png per sheet (--keep-jp2 keeps the master too; --thumbnails also saves the 126 px GIFs). It writes
<out>/loc_manifest.json recording where each byte came from: the URL you gave (kept verbatim, accumulating over reruns), source URLs, HTTP Last-Modified, the master's size and
SHA-256 (recorded even though the file is not kept), the PNG's SHA-256, pixel size from the IIIF image server, retrieval time, and — when a catalogue record is available — the item's
title, date, contributors, notes and the Library's rights advisory / access statement.

Two routes to the file list, tried in order:
  1. the loc.gov JSON API (<resource URL>?fo=json), which lists the files exactly. From some networks www.loc.gov
     answers non-browser clients with a Cloudflare challenge (HTTP 403) — then pass --from-json FILE with the same
     URL saved from a browser (open .../?fo=json, save page). Either way the record's metadata goes into the manifest.
  2. the storage host tile.loc.gov, which serves the files directly and is not challenged. The directory is derived
     from the id (gmd/gmd<ddd>m/<gdddd>m/<class>/<item>/ — the G-schedule call-number tree) and sheets are probed
     as <stem>-NNNN.jp2 (numbering may start above 0001 and have holes; the search stops after three misses in a row).
     "sheet" in the manifest is the viewer's ?sp= position, "file_number" the NNNN in the file name. The stem defaults to the Sanborn collection's
     convention (item g3934tm_g01352 1884 -> 01352_1884); give --stem for anything else, or --from-json to avoid guessing.

    python3 scripts/fim_fetch_loc.py http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521884 --out data/Sanborn_<County>/<year>
    python3 scripts/fim_fetch_loc.py g3934tm.g3934tm_g013521884 --out data/Sanborn_<County>/<year> --from-json ~/Downloads/loc.json
    python3 scripts/fim_fetch_loc.py <id> --out <dir> --metadata-only          # refresh loc_manifest.json, no downloads
    python3 scripts/fim_fetch_loc.py <id> --out <dir> --sheets 2               # one sheet (the ?sp= number)

Layout in this repository: one directory per county, one subdirectory per edition year — data/Sanborn_<County>/<year>/
(see data/README.md). Files already present with the right size are hashed, not re-downloaded. Please keep to one resource at a time:
tile.loc.gov is a public service and the sheets are ~10 MB each.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "fire-insurance-maps/fim_fetch_loc.py (academic research; contact via the repository)"
STORAGE = "https://tile.loc.gov/storage-services/service/gmd"
IIIF = "https://tile.loc.gov/image-services/iiif"
PAUSE = 1.0  # seconds between requests to the same host


# ----------------------------------------------------------------------------------------------- identifiers
def parse_id(text: str) -> tuple[str, str]:
    """'g3934tm.g3934tm_g013521884' (or a URL containing it) -> ('g3934tm', 'g3934tm_g013521884')."""
    m = re.search(r"(g\d{4}[a-z]*)\.(\1_g\d+[a-z]*)", text)
    if not m:
        raise SystemExit(f"cannot find a loc.gmd resource id like g3934tm.g3934tm_g013521884 in {text!r}")
    return m.group(1), m.group(2)


def storage_dir(cls: str, item: str) -> str:
    # observed: g3934tm.g3934tm_g013521884 -> gmd/gmd393m/g3934m/g3934tm/g3934tm_g013521884/
    digits = re.match(r"g(\d{4})", cls).group(1)
    return f"{STORAGE}/gmd{digits[:3]}m/g{digits}m/{cls}/{item}"


def sanborn_stem(item: str) -> str | None:
    """Sanborn items end in _g<5-digit map number><4-digit year>: g013521884 -> 01352_1884."""
    m = re.search(r"_g(\d{5})(\d{4})$", item)
    return f"{m.group(1)}_{m.group(2)}" if m else None


def iiif_id(cls: str, item: str, stem: str) -> str:
    digits = re.match(r"g(\d{4})", cls).group(1)
    return f"service:gmd:gmd{digits[:3]}m:g{digits}m:{cls}:{item}:{stem}"


# ----------------------------------------------------------------------------------------------- http
def request(url: str, method: str = "GET", timeout: int = 120) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = b"" if method == "HEAD" else r.read()
            return r.status, {k.lower(): v for k, v in r.headers.items()}, body
    except urllib.error.HTTPError as ex:
        return ex.code, {k.lower(): v for k, v in ex.headers.items()}, b""


def head(url: str) -> tuple[int, dict]:
    code, hdrs, _ = request(url, "HEAD")
    time.sleep(PAUSE)
    return code, hdrs


def download(url: str, dest: Path, expect_size: int | None, timeout: int) -> dict:
    """Fetch url to dest unless dest already has expect_size bytes. Returns size/sha256/http headers."""
    hdrs: dict = {}
    if dest.exists() and expect_size and dest.stat().st_size == expect_size:
        print(f"  have {dest.name} ({expect_size} B), not re-downloading")
        code, hdrs = head(url)
    else:
        t0 = time.time()
        code, hdrs, body = request(url, timeout=timeout)
        if code != 200:
            raise SystemExit(f"{url}: HTTP {code}")
        dest.write_bytes(body)
        print(f"  {dest.name}: {len(body)} B in {time.time() - t0:.1f}s")
        time.sleep(PAUSE)
    size = dest.stat().st_size
    if expect_size and size != expect_size:
        raise SystemExit(f"{dest}: {size} B on disk but server says {expect_size} B")
    return {
        "url": url,
        "file": dest.name,
        "bytes": size,
        "sha256": sha256(dest),
        "http_last_modified": hdrs.get("last-modified"),
        "http_content_type": hdrs.get("content-type"),
    }


def convert(jp2: Path, fmt: str) -> dict:
    """Decode the JPEG 2000 once and write a lossless PNG or LZW TIFF beside it (skipped if already there)."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    dest = jp2.with_suffix("." + fmt)
    if not dest.exists():
        t0 = time.time()
        im = Image.open(jp2)
        im.load()
        if fmt == "tif":
            im.save(dest, compression="tiff_lzw")
        else:
            im.save(dest, optimize=False, compress_level=6)
        print(f"  {dest.name}: {im.size[0]}x{im.size[1]} {im.mode}, {dest.stat().st_size} B in {time.time() - t0:.0f}s")
    return {"file": dest.name, "bytes": dest.stat().st_size, "sha256": sha256(dest), "lossless_decode_of": jp2.name}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------------------------- catalogue record
def fetch_record(cls: str, item: str, from_json: Path | None, timeout: int) -> dict | None:
    """The loc.gov JSON for the resource, from a saved file or the live API. None if neither is available."""
    if from_json:
        return json.loads(from_json.read_text())
    url = f"https://www.loc.gov/resource/{cls}.{item}/?fo=json"
    # short timeout: when Cloudflare is challenging this host it sometimes holds the connection open for minutes
    try:
        code, hdrs, body = request(url, timeout=min(timeout, 20))
    except (TimeoutError, OSError) as ex:
        code, hdrs, body = 0, {}, b""
        print(f"loc.gov JSON API: no answer within 20 s ({type(ex).__name__})", file=sys.stderr)
    time.sleep(PAUSE)
    if code == 200 and "json" in hdrs.get("content-type", ""):
        return json.loads(body)
    why = "Cloudflare challenge" if code == 403 and hdrs.get("cf-mitigated") == "challenge" else f"HTTP {code}"
    print(f"loc.gov JSON API not available from here ({why}); falling back to the storage host. "
          f"For the catalogue metadata, save {url} from a browser and pass it with --from-json.", file=sys.stderr)
    return None


def record_metadata(rec: dict) -> dict:
    """The provenance-relevant fields of a loc.gov item record, kept verbatim under their API names."""
    it = rec.get("item", {}) or {}
    keys = [
        "id", "title", "other_title", "date", "dates", "created_published", "contributors", "creator",
        "subjects", "subject_headings", "location", "notes", "medium", "call_number", "digital_id",
        "library_of_congress_control_number", "shelf_id", "source_collection", "repository", "reproduction_number",
        "rights", "rights_advisory", "rights_information", "access_advisory", "access_restricted",
        "online_format", "format", "language", "part_of", "url", "aka",
    ]
    out = {k: it[k] for k in keys if k in it and it[k] not in (None, "", [], {})}
    # the resource-level view has a few more (e.g. the 'resource' block with the IIIF/PDF/download URLs)
    for k in ("cite_this", "resource"):
        if rec.get(k):
            out[k] = rec[k]
    return out


def record_files(rec: dict) -> list[list[dict]]:
    """resources[0].files: one list per sheet, each a list of renditions {url, mimetype, width, height, size}."""
    res = rec.get("resources") or []
    return res[0].get("files", []) if res else []


# ----------------------------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("resource", help="loc.gov handle, resource URL, or bare id (g3934tm.g3934tm_g013521884)")
    ap.add_argument("--out", type=Path, required=True, help="directory for the files and loc_manifest.json")
    ap.add_argument("--from-json", type=Path, default=None, metavar="FILE",
                    help="the resource's ?fo=json saved from a browser (when www.loc.gov refuses this host)")
    ap.add_argument("--stem", default=None, help="file stem on tile.loc.gov (default: Sanborn convention, e.g. 01352_1884)")
    ap.add_argument("--sheets", default=None, help="which sheets: '2', '1-3', '1,4' (default: all)")
    ap.add_argument("--convert", choices=["png", "tif"], default="png",
                    help="lossless format each sheet is kept in (default png; VS Code and the pipeline read it)")
    ap.add_argument("--keep-jp2", action="store_true", help="also keep the Library's JPEG 2000 master (default: deleted after decoding)")
    ap.add_argument("--thumbnails", action="store_true", help="also save the Library's 126 px GIF thumbnails (default: no)")
    ap.add_argument("--metadata-only", action="store_true", help="write the manifest from what is on disk / in the record; download nothing")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per request (default 300)")
    args = ap.parse_args()

    cls, item = parse_id(args.resource)
    stem = args.stem or sanborn_stem(item)
    args.out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    record = fetch_record(cls, item, args.from_json, args.timeout)
    meta = record_metadata(record) if record else {}
    if meta:
        print(f"record: {meta.get('title')} — {meta.get('date') or meta.get('created_published')}")
        for k in ("rights_advisory", "rights", "access_advisory"):
            if k in meta:
                print(f"  {k}: {meta[k]}")

    # --- which sheets, and where each rendition lives
    sheets: list[dict] = []  # {n, jp2_url, gif_url, expect_size}
    files = record_files(record) if record else []
    if files:
        for n, renditions in enumerate(files, start=1):
            by_type = {}
            for r in renditions:
                by_type.setdefault(r.get("mimetype"), r)
            jp2 = by_type.get("image/jp2")
            gif = by_type.get("image/gif")
            if not jp2:  # some items expose only a TIFF master; take the biggest non-JPEG rendition
                best = max((r for r in renditions if r.get("mimetype") not in ("image/jpeg",)), key=lambda r: r.get("size") or 0, default=None)
                jp2 = best
            if jp2:
                m = re.search(r"-(\d{4})\.\w+$", jp2["url"])
                sheets.append({"n": n, "file_number": int(m.group(1)) if m else None, "jp2_url": jp2["url"], "gif_url": gif["url"] if gif else None,
                               "expect_size": jp2.get("size"), "width": jp2.get("width"), "height": jp2.get("height")})
        print(f"record lists {len(sheets)} sheet(s)")
    else:
        if not stem:
            raise SystemExit("no catalogue record and no --stem: cannot guess the file names on tile.loc.gov")
        base = storage_dir(cls, item)
        print(f"probing {base}/{stem}-NNNN.jp2 ...")
        # numbering need not start at 0001 (Tampa 1895 starts at 0005) and may have holes, so: look through the
        # first LEAD numbers for a first hit, then stop after GAP misses in a row.
        LEAD, GAP = 40, 3
        misses, n = 0, 0
        while n < 500:
            n += 1
            url = f"{base}/{stem}-{n:04d}.jp2"
            code, hdrs = head(url)
            if code == 200:
                misses = 0
                sheets.append({"n": len(sheets) + 1, "file_number": n, "jp2_url": url, "gif_url": f"{base}/{stem}-{n:04d}.gif",
                               "expect_size": int(hdrs.get("content-length", 0)) or None})
            else:
                misses += 1
                if (not sheets and n >= LEAD) or (sheets and misses >= GAP):
                    break
        if sheets:
            nums = [s["file_number"] for s in sheets]
            print(f"found {len(sheets)} sheet(s): {stem}-{nums[0]:04d} .. -{nums[-1]:04d}" + (" (with gaps)" if nums[-1] - nums[0] + 1 != len(nums) else ""))
        else:
            print(f"found no files named {stem}-0001..{LEAD:04d}; pass --stem, or --from-json with the browser-saved record")

    if args.sheets:
        want: set[int] = set()
        for part in args.sheets.split(","):
            a, _, b = part.partition("-")
            want.update(range(int(a), int(b or a) + 1))
        sheets = [s for s in sheets if s["n"] in want]

    # --- fetch
    previous: dict[int, dict] = {}
    requested: list[str] = []  # every URL/id this directory was ever requested with, as given (the user's citation trail)
    mpath = args.out / "loc_manifest.json"
    if mpath.exists():
        try:
            old = json.loads(mpath.read_text())
            previous = {s["sheet"]: s for s in old.get("sheets", [])}
            requested = list(old.get("source", {}).get("requested_url") or [])
        except (json.JSONDecodeError, KeyError, TypeError):
            previous, requested = {}, []
    if args.resource not in requested:
        requested.append(args.resource)
    out_sheets = []
    for s in sheets:
        n = s["n"]
        print(f"sheet {n}:")
        entry: dict = {"sheet": n, "file_number": s.get("file_number"),
                       "resource_page": f"https://www.loc.gov/resource/{cls}.{item}/?sp={n}"}
        name = Path(s["jp2_url"].split("?")[0]).name
        dest = args.out / name
        final = dest.with_suffix("." + args.convert)
        if args.metadata_only:
            if dest.exists():
                entry["master"] = {"url": s["jp2_url"], "file": name, "bytes": dest.stat().st_size, "sha256": sha256(dest)}
            elif previous.get(n, {}).get("master"):
                entry["master"] = previous[n]["master"]  # the master is gone; keep what was recorded when it was hashed
            if final.exists():
                entry["image"] = {"file": final.name, "bytes": final.stat().st_size, "sha256": sha256(final),
                                  "lossless_decode_of": name}
        else:
            if final.exists() and not dest.exists() and previous.get(n, {}).get("master"):
                print(f"  have {final.name}, not re-downloading")
                entry["master"] = previous[n]["master"]
                entry["image"] = previous[n].get("image") or {"file": final.name, "bytes": final.stat().st_size,
                                                               "sha256": sha256(final), "lossless_decode_of": name}
            else:
                entry["master"] = download(s["jp2_url"], dest, s.get("expect_size"), args.timeout)
            if s.get("gif_url") and args.thumbnails:
                gdest = args.out / Path(s["gif_url"].split("?")[0]).name
                code, hdrs = head(s["gif_url"])
                if code == 200:
                    entry["thumbnail"] = download(s["gif_url"], gdest, int(hdrs.get("content-length", 0)) or None, args.timeout)
            if dest.exists():
                entry["image"] = convert(dest, args.convert)
                if not args.keep_jp2:
                    dest.unlink()
                    print(f"  removed {dest.name} (master not kept; its SHA-256 is in the manifest)")
            entry["master"]["kept"] = dest.exists()
        # pixel size from the IIIF image server (authoritative and cheap)
        sstem = Path(name).stem
        code, _, body = request(f"{IIIF}/{iiif_id(cls, item, sstem)}/info.json", timeout=args.timeout)
        time.sleep(PAUSE)
        if code == 200:
            info = json.loads(body)
            entry["iiif"] = {"id": info.get("@id"), "width": info.get("width"), "height": info.get("height")}
        elif s.get("width"):
            entry["iiif"] = {"width": s["width"], "height": s["height"]}
        out_sheets.append(entry)

    manifest = {
        "source": {
            "requested_url": requested,
            "institution": "Library of Congress, Geography and Map Division",
            "handle": f"http://hdl.loc.gov/loc.gmd/{cls}.{item}",
            "resource_page": f"https://www.loc.gov/resource/{cls}.{item}/",
            "item_page": (meta.get("url") or (f"https://www.loc.gov/item/{meta['id']}/" if meta.get("id") and not str(meta["id"]).startswith("http") else None)),
            "json_api": f"https://www.loc.gov/resource/{cls}.{item}/?fo=json",
            "storage_dir": storage_dir(cls, item),
        },
        "retrieved": now,
        "retrieved_by": "scripts/fim_fetch_loc.py",
        "catalogue_record": meta or None,
        "catalogue_record_source": (str(args.from_json) if args.from_json else ("loc.gov JSON API" if record else
                                    "unavailable from this host (Cloudflare challenge); save ?fo=json from a browser and rerun with --from-json")),
        "sheets": out_sheets,
    }
    path = mpath
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(out_sheets)} sheet(s) -> {path}")


if __name__ == "__main__":
    main()
