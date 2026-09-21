#!/usr/bin/env python3
"""
Run log: one JSON per run directory and one master JSON under runs/, so that what the terminal prints can be computed
on afterwards — OCR seconds against pixels and tiles, how many sheets reach --min-labels on their street names alone
(no alias file, no --fuzzy), which street layer and which area of it placed a sheet, how long each stage took.

Every stage script opens a Stage when it starts; the record is written when it ends, whether it ended well, was refused
(SystemExit with a message, e.g. too few labels) or crashed:

    from fim_runlog import Stage
    with Stage(run_dir, "georef", sheet=stem) as log:
        ...
        log.note(n_matched=..., rms_m=...)      # fields as they become known
        log.lap("fit")                          # seconds since the previous lap -> laps_s

Files (both under runs/, which git ignores — a run log names local paths and every run ever made):
  <run dir>/run_log.json   {"run_dir", "sheet", "events": [...]}   one event per stage execution on that run
  runs/run_log.json        {"events": [...]}                        every event of every run, appended live

Common event fields: event_id, stage (ocr | blocks | areas | locate | georef | fetch_streets | batch), script, argv,
run_dir, sheet, batch_id (set by fim_batch.py for its children), started_utc, finished_utc, elapsed_s, laps_s, ok,
status (ok | dry_run | placed | refused_min_labels | refused | error | interrupted), error, host, git_commit, git_dirty,
backfilled. The stage fields are documented where they are set (ocr_summary, georef fields in fim_georef.py, ...).
Nothing here is specific to a city or a book.

    python3 scripts/fim_runlog.py --summary                one line per run: latest OCR and latest fit
    python3 scripts/fim_runlog.py --csv runs/run_log.csv   every event flattened to one row (nested keys joined by '.')
    python3 scripts/fim_runlog.py --rebuild                master rebuilt from the per-run files
    python3 scripts/fim_runlog.py --backfill               events for runs made before the log existed, from their
                                                           *_tiles.json + tiles/*_metadata.json (OCR: model seconds,
                                                           tokens, GPU), *_georef.json (fit), *_blocks_px.geojson,
                                                           *_areas_px.geojson; marked backfilled: true. A backfilled
                                                           fit has no wall-clock time; a refused fit left no file and
                                                           cannot be backfilled.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import json
import math
import os
import socket
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
MASTER = RUNS / "run_log.json"
PER_RUN = "run_log.json"
PROMPTS_DIR = ROOT / "configs" / "prompts"
MASTER_NOTE = ("every stage execution of every run under runs/, appended live by scripts/fim_runlog.Stage; "
               "the same events sit in each run's run_log.json. Rebuild with fim_runlog.py --rebuild; "
               "flatten with --csv; summarise with --summary.")

COMMON_ORDER = ["event_id", "stage", "status", "ok", "run_dir", "sheet", "batch_id", "started_utc", "finished_utc", "elapsed_s",
                "script", "argv", "host", "git_commit", "git_dirty", "backfilled", "error"]


# ----------------------------------------------------------------------------------------------------- helpers
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(p: Path | str | None) -> str | None:
    if p is None:
        return None
    p = Path(p)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def _default(o: Any) -> Any:
    """json.dumps fallback: paths, numpy scalars/arrays, sets, anything else -> str."""
    if isinstance(o, Path):
        return str(o)
    if hasattr(o, "item"):
        try:
            return o.item()
        except Exception:  # noqa: BLE001
            pass
    if hasattr(o, "tolist"):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    return str(o)


def _git() -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5).stdout.strip() or None
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", "scripts", "configs"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=5).stdout.strip())
        return commit, dirty
    except Exception:  # noqa: BLE001 — no git, no problem
        return None, None


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Exclusive lock on <path>.lock while a JSON file is read, extended and written (two sheets never run at once
    in fim_batch.py, but nothing stops a person from fitting one sheet while a batch runs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    with open(lock, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def load_json(path: Path) -> dict | None:
    """The document, or None when the file is missing. A corrupt file is moved aside (never silently overwritten)."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        bad = path.with_suffix(f".corrupt-{datetime.now():%Y%m%d%H%M%S}.json")
        path.rename(bad)
        print(f"fim_runlog: {path} was not valid JSON; moved to {bad.name} and started afresh", file=sys.stderr)
        return None


def write_json(path: Path, doc: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=_default), encoding="utf-8")
    tmp.replace(path)


def sheet_of(run_dir: Path | None) -> str | None:
    if run_dir is None:
        return None
    t = next(Path(run_dir).glob("*_tiles.json"), None)
    return t.name[: -len("_tiles.json")] if t else None


def append_event(event: dict, run_dir: Path | None) -> None:
    """Append one event to the run's log (if it belongs to a run) and to the master."""
    if run_dir is not None:
        p = Path(run_dir) / PER_RUN
        with locked(p):
            doc = load_json(p) or {"run_dir": rel(run_dir), "sheet": event.get("sheet"), "events": []}
            doc.setdefault("events", []).append(event)
            if not doc.get("sheet") and event.get("sheet"):
                doc["sheet"] = event["sheet"]
            write_json(p, doc)
    with locked(MASTER):
        doc = load_json(MASTER) or {"note": MASTER_NOTE, "events": []}
        doc.setdefault("events", []).append(event)
        write_json(MASTER, doc)


# ----------------------------------------------------------------------------------------------------- Stage
class Stage:
    """Context manager around one stage execution. Fields go in with note(); the event is written on exit."""

    def __init__(self, run_dir: Path | str | None, stage: str, sheet: str | None = None, argv: list[str] | None = None, **fields: Any) -> None:
        self.run_dir = Path(run_dir).expanduser().resolve() if run_dir is not None else None
        commit, dirty = _git()
        self.event: dict[str, Any] = {
            "event_id": uuid.uuid4().hex[:12], "stage": stage, "status": None, "ok": None,
            "run_dir": rel(self.run_dir), "sheet": sheet or sheet_of(self.run_dir), "batch_id": os.environ.get("FIM_BATCH_ID"),
            "started_utc": utc_now(), "finished_utc": None, "elapsed_s": None,
            "script": Path(sys.argv[0]).name if sys.argv and sys.argv[0] else None, "argv": list(argv if argv is not None else sys.argv[1:]),
            "host": socket.gethostname(), "git_commit": commit, "git_dirty": dirty, "backfilled": False, "error": None,
        }
        self.event.update(fields)
        self._t0 = time.perf_counter()
        self._lap = self._t0
        self.laps: dict[str, float] = {}

    def note(self, **fields: Any) -> None:
        self.event.update(fields)

    def lap(self, name: str) -> None:
        now = time.perf_counter()
        self.laps[name] = round(self.laps.get(name, 0.0) + now - self._lap, 3)
        self._lap = now

    def __enter__(self) -> "Stage":
        return self

    def __exit__(self, et, ev, tb) -> bool:
        e = self.event
        e["finished_utc"] = utc_now()
        e["elapsed_s"] = round(time.perf_counter() - self._t0, 3)
        if self.laps:
            e["laps_s"] = self.laps
        if et is None:
            e["ok"] = True
            e["status"] = e["status"] or "ok"
        elif issubclass(et, SystemExit):
            code = ev.code
            e["ok"] = code in (None, 0)
            if e["ok"]:
                e["status"] = e["status"] or "ok"
            else:
                e["status"] = e["status"] or "refused"
                e["error"] = str(code)[:1000]
        elif issubclass(et, KeyboardInterrupt):
            e["ok"] = False
            e["status"] = "interrupted"
            e["error"] = "KeyboardInterrupt"
        else:
            e["ok"] = False
            e["status"] = "error"
            e["error"] = f"{et.__name__}: {ev}"[:1000]
        try:
            append_event(e, self.run_dir)
        except Exception as ex:  # noqa: BLE001 — the log must never take the run down with it
            print(f"fim_runlog: could not write the run log ({type(ex).__name__}: {ex})", file=sys.stderr)
        return False


# ----------------------------------------------------------------------------------------------------- summaries shared by the live hooks and --backfill
def _crop_px(doc: dict) -> tuple[int, int]:
    """(content area in source px, content area in work px) — the crop box if the run had one, else the whole sheet."""
    sw, sh = doc["source_size"]["w"], doc["source_size"]["h"]
    crop = doc.get("crop_source_px")
    if crop:
        x0, y0, x1, y1 = (int(v) for v in crop.split(","))
        src = (x1 - x0) * (y1 - y0)
    else:
        src = sw * sh
    return src, round(src * doc.get("work_scale", 1.0) ** 2)


def prompt_preset_of(prompt: str) -> str:
    """Name of the preset in configs/prompts/ whose text is this prompt, else 'custom'."""
    for p in sorted(PROMPTS_DIR.glob("*.txt")):
        try:
            if p.read_text(encoding="utf-8").strip() == prompt.strip():
                return p.stem
        except OSError:
            continue
    return "custom"


def ocr_summary(doc: dict, run_dir: Path) -> dict[str, Any]:
    """OCR fields from a <stem>_tiles.json and the per-view tiles/*_metadata.json beside it.

    source_px / content_px: pixels of the scan, and of the part that was tiled (the crop box or the whole sheet).
    n_tiles_planned / n_tiles_ocr / n_tiles_blank_skipped / n_tiles_not_selected: the grid and what was read.
    n_views_ocr: tiles x rotations actually read; pixels_ocr_work: work-image pixels fed to the model over all views
    (overlaps counted every time, as the model saw them); pixels_ocr_source: the same in scan pixels.
    generate_s_all / prepare_s_all: model seconds over every view whose metadata exists (resumed views included —
    the cost of the run's OCR whenever it was paid); input_tokens_sum / output_tokens_sum likewise; n_views_hit_cap.
    tokens_parsed / tokens_kept / tokens_dup / tokens_fragment / tokens_conflict / runaway_dropped: the stitched result.
    """
    tiles = doc.get("tiles", {})
    ok = {k: v for k, v in tiles.items() if v.get("status") == "ok"}
    n_views = n_cap = n_meta = 0
    px_work = 0
    gen_s = prep_s = 0.0
    in_tok = out_tok = 0
    runaway = 0
    utcs: list[str] = []
    gpu = revision = None
    for v in ok.values():
        area = max(0, v["x1"] - v["x0"]) * max(0, v["y1"] - v["y0"])
        views = v.get("rotations") or {"0": v}  # runs before rotated views kept the single view's fields on the tile itself
        for r in views.values():
            n_views += 1
            px_work += area
            n_cap += bool(r.get("hit_cap"))
            runaway += int(r.get("runaway_dropped") or 0)
            content = r.get("content")
            if not content:
                continue
            mp = Path(run_dir) / content.replace("_content.txt", "_metadata.json")
            if not mp.exists():
                continue
            try:
                m = json.loads(mp.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            n_meta += 1
            comp = m.get("compute") or {}
            gen_s += float(comp.get("generate_elapsed_seconds") or 0.0)
            prep_s += float(comp.get("prepare_elapsed_seconds") or 0.0)
            in_tok += int(m.get("input_tokens") or 0)
            out_tok += int(m.get("output_tokens") or 0)
            if m.get("run_utc"):
                utcs.append(m["run_utc"])
            revision = revision or m.get("model_revision")
            if gpu is None:
                devs = ((comp.get("cuda") or {}).get("during_and_after_generate") or {}).get("devices") or []
                gpu = devs[0].get("name") if devs else None
    toks = doc.get("tokens", [])
    n_frag = sum(1 for t in toks if t.get("fragment"))
    n_conf = sum(1 for t in toks if t.get("conflict"))
    n_dup = sum(1 for t in toks if t.get("dup_of") is not None) - n_frag - n_conf
    content_src, content_work = _crop_px(doc)
    ws = doc.get("work_scale", 1.0) or 1.0
    grid = doc.get("grid") or {}
    return {
        "source_image": doc.get("source_image"), "source_w": doc["source_size"]["w"], "source_h": doc["source_size"]["h"],
        "source_px": doc["source_size"]["w"] * doc["source_size"]["h"], "work_w": doc["work_size"]["w"], "work_h": doc["work_size"]["h"], "work_scale": ws,
        "crop_source_px": doc.get("crop_source_px"), "content_px_source": content_src, "content_px_work": content_work,
        "tile_px": doc.get("tile_px"), "overlap_px": doc.get("overlap_px"), "grid_rows": grid.get("rows"), "grid_cols": grid.get("cols"),
        "rotations_deg": doc.get("rotations_deg") or [0], "n_rotations": len(doc.get("rotations_deg") or [0]),
        "n_tiles_planned": len(tiles), "n_tiles_ocr": len(ok),
        "n_tiles_blank_skipped": sum(1 for v in tiles.values() if v.get("status") == "skipped_blank"),
        "n_tiles_not_selected": sum(1 for v in tiles.values() if v.get("status") == "not_selected"),
        "n_views_ocr": n_views, "n_views_with_metadata": n_meta, "n_views_hit_cap": n_cap,
        "pixels_ocr_work": px_work, "pixels_ocr_source": round(px_work / (ws * ws)) if ws else None,
        "generate_s_all": round(gen_s, 3), "prepare_s_all": round(prep_s, 3), "generate_s_per_view": round(gen_s / n_meta, 3) if n_meta else None,
        "generate_s_per_megapixel_work": round(gen_s / (px_work / 1e6), 3) if px_work and gen_s else None,
        "input_tokens_sum": in_tok, "output_tokens_sum": out_tok,
        "views_first_utc": min(utcs) if utcs else None, "views_last_utc": max(utcs) if utcs else None,
        "tokens_parsed": len(toks), "tokens_kept": sum(1 for t in toks if t.get("dup_of") is None), "tokens_dup": n_dup, "tokens_fragment": n_frag, "tokens_conflict": n_conf,
        "runaway_dropped": runaway,
        "model": doc.get("model"), "model_revision": revision, "gpu": gpu, "max_new_tokens": doc.get("max_new_tokens"), "min_ink": doc.get("min_ink"), "dedupe_iou": doc.get("dedupe_iou"),
        "prompt_preset": prompt_preset_of(doc.get("prompt", "")), "prompt_chars": len(doc.get("prompt", "")),
        "shift_work_px": doc.get("shift_work_px"), "merged_from": doc.get("merged_from") or [], "surya_lines": doc.get("surya_lines"),
    }


_STREETS_CACHE: dict[str, dict] = {}


def streets_provenance(path: Path | str | None) -> dict[str, Any] | None:
    """What fim_fetch_streets.py recorded about a street layer: source, licence, the WGS84 box (and the place names or
    locate candidate it came from), its area in km2, CRS, fetch time, feature count. The answer to 'which area of which
    layer placed this sheet'. Cached per process (a county layer is tens of MB)."""
    if path is None:
        return None
    key = str(Path(path).expanduser().resolve())
    if key in _STREETS_CACHE:
        return _STREETS_CACHE[key]
    p = Path(key)
    if not p.exists():
        return {"file": rel(p), "missing": True}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"file": rel(p), "unreadable": True}
    bbox = d.get("bbox_wgs84_swne")
    area = None
    if bbox and len(bbox) == 4:
        s, w, n, e = (float(v) for v in bbox)
        area = round(abs(n - s) * 111.32 * abs(e - w) * 111.32 * math.cos(math.radians((n + s) / 2)), 1)
    src = d.get("source") or {}
    feats = d.get("features") or []
    names = set()
    for f in feats:
        pr = f.get("properties") or {}
        nm = pr.get("name") or pr.get("STNAME") or pr.get("StreetName") or pr.get("FULLNAME") or pr.get("STRUCTURED_NAME_1") or pr.get("FULL_NAME")
        if nm:
            names.add(str(nm).upper())
    out = {"file": rel(p), "source_kind": src.get("kind"), "layer": src.get("layer"), "licence": src.get("licence"),
           "bbox_wgs84_swne": bbox, "bbox_area_km2": area, "bbox_origin": d.get("bbox_origin"), "pad_km": d.get("pad_km"),
           "epsg": d.get("epsg"), "crs_name": d.get("crs_name"), "fetched_utc": d.get("fetched_utc"), "n_features": len(feats), "n_distinct_names": len(names) or None}
    _STREETS_CACHE[key] = out
    return out


def _n_features(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return len(json.loads(path.read_text(encoding="utf-8")).get("features", []))
    except (OSError, json.JSONDecodeError):
        return None


def px_outputs_summary(run_dir: Path, stem: str) -> dict[str, Any]:
    """Counts of the pixel-space products (stage 2) in a run dir."""
    run_dir = Path(run_dir)
    return {"n_blocks_px": _n_features(run_dir / f"{stem}_blocks_px.geojson"),
            "n_buildings_px": _n_features(run_dir / f"{stem}_buildings_px.geojson"),
            "n_areas_px": _n_features(run_dir / f"{stem}_areas_px.geojson")}


def map_outputs_summary(run_dir: Path, stem: str) -> dict[str, Any]:
    """Counts of the map-space products (stage 4) in a run dir, by kind."""
    run_dir = Path(run_dir)
    out: dict[str, Any] = {"n_blocks_kept": _n_features(run_dir / f"{stem}_blocks_wgs84.geojson"),
                           "n_blocks_rejected": _n_features(run_dir / f"{stem}_blocks_rejected_wgs84.geojson"),
                           "n_buildings": _n_features(run_dir / f"{stem}_buildings_wgs84.geojson"),
                           "n_areas": _n_features(run_dir / f"{stem}_areas_wgs84.geojson"),
                           "n_tokens_wgs84": _n_features(run_dir / f"{stem}_tokens_wgs84.geojson")}
    sn = run_dir / f"{stem}_street_names_wgs84.geojson"
    if sn.exists():
        try:
            feats = json.loads(sn.read_text(encoding="utf-8")).get("features", [])
            kinds: dict[str, int] = {}
            for f in feats:
                k = (f.get("properties") or {}).get("kind") or "?"
                kinds[k] = kinds.get(k, 0) + 1
            out["n_street_name_entries"] = len(feats)
            out["street_name_kinds"] = kinds
        except (OSError, json.JSONDecodeError):
            pass
    return out


def georef_summary(gj: dict) -> dict[str, Any]:
    """Fit fields from a <stem>_georef.json (what fim_georef.py knows at the end; used to backfill).

    n_matched: street labels that went into the fit (after the lonely-street drop); n_matched_plain: of those, matched
    by name alone — no alias entry, no fuzzy match — the count that says whether the sheet places without any
    per-city configuration; n_matched_alias / n_matched_fuzzy the rest. min_labels_met_plain compares the plain count
    with the --min-labels the fit used. Older georef.json (before 2026-09-17) lack the alias/fuzzy flags: plain is null.
    """
    labels = gj.get("labels") or []
    params = gj.get("params") or {}
    flagged = labels and all(("alias" in l or "fuzzy" in l) for l in labels)
    n_alias = sum(1 for l in labels if l.get("alias")) if flagged else None
    n_fuzzy = sum(1 for l in labels if l.get("fuzzy")) if flagged else None
    n_plain = sum(1 for l in labels if not l.get("alias") and not l.get("fuzzy")) if flagged else None
    min_labels = params.get("min_labels")
    aff = gj.get("affine_rejected")
    near = gj.get("near") or params.get("near")
    return {
        "streets_file": rel(gj.get("streets")), "streets": streets_provenance(gj.get("streets")), "epsg": gj.get("epsg"), "crs": gj.get("crs"),
        "streets_fields": gj.get("streets_fields"), "intersections": gj.get("intersections"),
        "alias_file": rel(params.get("alias")) if params.get("alias") else None, "fuzzy": bool(gj.get("fuzzy") or params.get("fuzzy")),
        "near": [rel(r) for r in near] if near else None, "n_near": len(near) if near else 0,
        "min_labels": min_labels, "lots": params.get("lots"), "spelling": params.get("spelling"), "rotation_mode": params.get("rotation"), "year": params.get("year"),
        "scales_given": params.get("scales_given"),
        "n_matched": len(labels), "n_matched_plain": n_plain, "n_matched_alias": n_alias, "n_matched_fuzzy": n_fuzzy,
        "n_distinct_streets": len({k for l in labels for k in (l.get("modern") or [])}),
        "min_labels_met": (len(labels) >= min_labels) if min_labels is not None else None,
        "min_labels_met_plain": (n_plain >= min_labels) if (min_labels is not None and n_plain is not None) else None,
        "n_building_labels": len(gj.get("building_labels") or []), "n_unmatched_alpha": len(gj.get("unmatched_tokens") or []),
        "n_dropped_far": len(gj.get("dropped_far") or []), "n_alias_suggestions": len(gj.get("alias_suggestions") or []),
        "alias_suggestions": [f"{s.get('label')}->{s.get('modern')}" for s in (gj.get("alias_suggestions") or [])][:12],
        "transform": gj.get("transform"), "affine_rejected": bool(aff), "affine_rejected_why": (aff or {}).get("why") if isinstance(aff, dict) else None,
        "rotation_source": gj.get("rotation_source"),
        "rms_m": gj.get("rms_m"), "median_m": gj.get("median_m"), "max_m": gj.get("max_m"), "n_inliers": gj.get("n_labels"), "n_outliers": gj.get("n_outliers"),
        "outlier_threshold_m": gj.get("outlier_threshold_m"),
        "scale_m_per_px_x": (gj.get("scale_m_per_px") or {}).get("x"), "scale_m_per_px_y": (gj.get("scale_m_per_px") or {}).get("y"),
        "rotation_deg": gj.get("rotation_deg"), "shear_deg": gj.get("shear_deg"),
        "coarse_seed": gj.get("coarse_seed"), "stated_scale_ft_per_inch": gj.get("stated_scale_ft_per_inch"), "implied_dpi_from_stated_scale": gj.get("implied_dpi_from_stated_scale"),
        "page_centre_wgs84": ring_centre(((gj.get("page_corners_wgs84") or {}).get("content"))),
    }


def ring_centre(ring: list | None) -> list[float] | None:
    """Mean of a ring's vertices (WGS84 lon/lat when the ring is one)."""
    if not ring:
        return None
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    return [round(sum(xs) / len(xs), 6), round(sum(ys) / len(ys), 6)]


# ----------------------------------------------------------------------------------------------------- CLI: rebuild / backfill / csv / summary
def run_dirs() -> list[Path]:
    """Every directory under runs/ holding a <stem>_tiles.json, at any depth (books are nested by year and sheet)."""
    return sorted({p.parent for p in RUNS.rglob("*_tiles.json")})


def _parse_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def backfill_run(run_dir: Path, force: bool = False) -> list[dict]:
    """Synthesise the events a run would have logged, from its files. Only stages without an event yet (or all with force)."""
    stem = sheet_of(run_dir)
    if not stem:
        return []
    have = {e.get("stage") for e in ((load_json(run_dir / PER_RUN) or {}).get("events") or [])} if not force else set()
    tiles_path = run_dir / f"{stem}_tiles.json"
    try:
        doc = json.loads(tiles_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as ex:
        print(f"  {rel(run_dir)}: cannot read {tiles_path.name} ({ex})", file=sys.stderr)
        return []
    commit, dirty = None, None
    base = {"run_dir": rel(run_dir), "sheet": stem, "batch_id": None, "argv": None, "host": None, "git_commit": commit, "git_dirty": dirty, "backfilled": True, "error": None, "ok": True}
    events: list[dict] = []

    if "ocr" not in have:
        s = ocr_summary(doc, run_dir)
        first, last, end = _parse_utc(s["views_first_utc"]), _parse_utc(s["views_last_utc"]), _parse_utc(doc.get("run_utc"))
        started = first or end
        finished = end or last
        elapsed = round((finished - started).total_seconds(), 1) if (started and finished and finished >= started) else None
        events.append({"event_id": uuid.uuid4().hex[:12], "stage": "ocr", "status": "dry_run" if doc.get("dry_run") else "ok", **base, "script": "fim_tile_ocr.py",
                       "started_utc": started.isoformat() if started else None, "finished_utc": finished.isoformat() if finished else None, "elapsed_s": elapsed,
                       "elapsed_note": "first view's run_utc to the tiles.json run_utc; spans a resumed run's earlier passes" if elapsed is not None else None,
                       **s, "n_views_inferred": None, "n_views_resumed": None, "model_load_s": None, "generate_s_new": None})

    blocks_px = run_dir / f"{stem}_blocks_px.geojson"
    if "blocks" not in have and blocks_px.exists():
        try:
            bl = json.loads(blocks_px.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            bl = {}
        seeded = "georef" in str(bl.get("street_seeds", ""))
        events.append({"event_id": uuid.uuid4().hex[:12], "stage": "blocks", "status": "ok", **base, "script": "fim_georef.py (re-trace)" if seeded else "fim_blocks.py",
                       "started_utc": None, "finished_utc": bl.get("generated_utc"), "elapsed_s": None,
                       "georef_seeded": seeded, "neck_px": (bl.get("params") or {}).get("neck_px"), "white_space": bl.get("white_space"), "params": bl.get("params"),
                       **px_outputs_summary(run_dir, stem)})

    areas_px = run_dir / f"{stem}_areas_px.geojson"
    if "areas" not in have and areas_px.exists():
        try:
            ar = json.loads(areas_px.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            ar = {}
        events.append({"event_id": uuid.uuid4().hex[:12], "stage": "areas", "status": "ok", **base, "script": "fim_areas.py",
                       "started_utc": None, "finished_utc": ar.get("generated_utc"), "elapsed_s": None,
                       "n_areas_px": len(ar.get("features", [])), "n_tints": len(ar.get("tints") or []), "tints": [t.get("name") for t in (ar.get("tints") or [])]})

    loc = run_dir / f"{stem}_locate.json"
    if "locate" not in have and loc.exists():
        try:
            lj = json.loads(loc.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            lj = {}
        cands = lj.get("candidates") or []
        best = cands[0] if cands else None
        events.append({"event_id": uuid.uuid4().hex[:12], "stage": "locate", "status": "ok" if cands else "no_candidates", **base, "script": "fim_locate.py",
                       "started_utc": None, "finished_utc": lj.get("generated_utc"), "elapsed_s": None,
                       "n_names_queried": len(lj.get("names") or []), "n_candidates": len(cands),
                       "best_candidate": {k: best.get(k) for k in ("description", "core_score", "n_names", "bbox_padded_swne", "utm_epsg")} if best else None,
                       "params": lj.get("params")})

    gpath = run_dir / f"{stem}_georef.json"
    if "georef" not in have and gpath.exists():
        try:
            gj = json.loads(gpath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            gj = None
        if gj:
            events.append({"event_id": uuid.uuid4().hex[:12], "stage": "georef", "status": "placed", **base, "script": "fim_georef.py",
                           "started_utc": None, "finished_utc": gj.get("generated_utc"), "elapsed_s": None,
                           **georef_summary(gj), **map_outputs_summary(run_dir, stem)})
    return events


def backfill(force: bool = False) -> None:
    n_runs = n_ev = 0
    for rd in run_dirs():
        evs = backfill_run(rd, force)
        if not evs:
            continue
        n_runs += 1
        for e in evs:
            append_event(e, rd)
            n_ev += 1
        print(f"  {rel(rd)}: {', '.join(e['stage'] for e in evs)}")
    print(f"backfilled {n_ev} events over {n_runs} runs -> {rel(MASTER)}")


def rebuild() -> None:
    events: list[dict] = []
    for p in sorted(RUNS.rglob(PER_RUN)):
        if p.resolve() == MASTER.resolve():
            continue
        events.extend((load_json(p) or {}).get("events") or [])
    # events that belong to no run (fetch_streets, batch) live only in the master: keep the ones already there
    old = (load_json(MASTER) or {}).get("events") or []
    ids = {e.get("event_id") for e in events}
    events.extend(e for e in old if e.get("run_dir") is None and e.get("event_id") not in ids)
    events.sort(key=lambda e: (e.get("finished_utc") or e.get("started_utc") or ""))
    with locked(MASTER):
        write_json(MASTER, {"note": MASTER_NOTE, "rebuilt_utc": utc_now(), "events": events})
    print(f"rebuilt {rel(MASTER)}: {len(events)} events")


def flatten(d: dict, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        elif isinstance(v, list):
            out[key] = json.dumps(v, ensure_ascii=False, default=_default) if v and not all(isinstance(x, (str, int, float)) for x in v) else " ".join(str(x) for x in v)
        else:
            out[key] = v
    return out


def to_csv(path: Path) -> None:
    events = (load_json(MASTER) or {}).get("events") or []
    rows = [flatten(e) for e in events]
    keys = set().union(*(r.keys() for r in rows)) if rows else set()
    cols = [c for c in COMMON_ORDER if c in keys] + sorted(k for k in keys if k not in COMMON_ORDER)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
    print(f"{len(rows)} events x {len(cols)} columns -> {path}")


def summary() -> None:
    events = (load_json(MASTER) or {}).get("events") or []
    by_run: dict[str, dict[str, dict]] = {}
    for e in events:
        if not e.get("run_dir"):
            continue
        latest = by_run.setdefault(e["run_dir"], {})
        prev = latest.get(e["stage"])
        if prev is None or (e.get("finished_utc") or "") >= (prev.get("finished_utc") or ""):
            latest[e["stage"]] = e
    print(f"{'run':<58} {'tiles':>5} {'views':>5} {'gen s':>7} {'kept':>5}  {'fit':<18} {'plain/all':>9} {'RMS m':>6}  streets layer / area")
    for rd, st in sorted(by_run.items()):
        o, g = st.get("ocr"), st.get("georef")
        fit = (g or {}).get("status") or "-"
        lab = (f"{g['n_matched_plain'] if g.get('n_matched_plain') is not None else '?'}/{g.get('n_matched', '-')}") if g else "-"
        rms = f"{g['rms_m']:.1f}" if g and g.get("rms_m") is not None else "-"
        area = ""
        if g and g.get("streets"):
            s = g["streets"]
            org = s.get("bbox_origin") or {}
            where = ", ".join(org.get("place", [])) if org.get("place") else (org.get("description") or org.get("bbox") or "")
            area = f"{Path(s.get('file') or '').name} {s.get('bbox_area_km2') or ''} km2 {where}".strip()
        n_tiles = str(o.get("n_tiles_ocr", "-")) if o else "-"
        n_views = str(o.get("n_views_ocr", "-")) if o else "-"
        gen = f"{o['generate_s_all']:.0f}" if o and o.get("generate_s_all") else "-"
        kept = str(o.get("tokens_kept", "-")) if o else "-"
        print(f"{rd[-58:]:<58} {n_tiles:>5} {n_views:>5} {gen:>7} {kept:>5}  {fit:<18} {lab:>9} {rms:>6}  {area}")
    stray = [e for e in events if not e.get("run_dir")]
    if stray:
        print(f"\n{len(stray)} events without a run dir (fetch_streets / batch): " + ", ".join(sorted({e['stage'] for e in stray})))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", action="store_true", help="one line per run: latest OCR and latest fit")
    ap.add_argument("--csv", type=Path, metavar="PATH", help="write every event of the master as one CSV row")
    ap.add_argument("--rebuild", action="store_true", help="rebuild runs/run_log.json from the per-run run_log.json files")
    ap.add_argument("--backfill", action="store_true", help="synthesise events for runs that predate the log (stages without an event yet)")
    ap.add_argument("--force", action="store_true", help="with --backfill: add backfilled events even where events exist")
    args = ap.parse_args()
    if not any((args.summary, args.csv, args.rebuild, args.backfill)):
        ap.error("choose --summary, --csv PATH, --rebuild and/or --backfill")
    if args.backfill:
        backfill(args.force)
    if args.rebuild:
        rebuild()
    if args.csv:
        to_csv(args.csv)
    if args.summary:
        summary()


if __name__ == "__main__":
    main()
