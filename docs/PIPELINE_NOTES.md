# Pipeline notes (detailed)

> This was the top-level README until 2026-09-15. `../README.md` is now the quick start for new users; this file keeps the
> full design notes, per-stage rationale, results and history. The **Dependencies** section below describes the original
> workstation setup; the supported setup is now the `.venv` in README → Setup (`_hunyuan_compat.py` finds either).

OCR and structured extraction for the **Victoria, B.C. fire insurance plans** (Chas. E. Goad; 1885 index/key
crops and the 1891→1895 revised book, 37 pages). One project for what was previously spread across
`~/projects/hunyuan`, `~/projects/chandra/output`, `~/projects/recast` and three `~/projects/datasets` dirs.

Two kinds of output are pursued, with different models:

| Goal | Model | Why | Entry point |
|---|---|---|---|
| Every word on a map sheet **with pixel coordinates** (street names, block numbers, building labels) | HunyuanOCR (`tencent/HunyuanOCR`) | emits `word(x1,y1),(x2,y2)` in 0–1000 normalised coords | `scripts/fim_tile_ocr.py` (tiled, whole sheet) or `scripts/fim_hunyuan.py` → `scripts/fim_overlay.sh` (single image) |
| **Tables** from the index pages (street → sheet lookups, block-number tables) and prose transcripts (key, cover memoranda, feature descriptions) | Chandra (`datalab-to/chandra`) | strong layout/table → markdown+HTML | `scripts/fim_chandra.sh` → `scripts/fim_csvify.py` |

**Rights:** the RBCM scans are licensed for research use only and are not in this repository, only data derived
from them. See `RIGHTS.md` before reusing or publishing anything here.

## Layout

```
data/               symlinks into ~/projects/datasets/fire_insurance_maps (no copies; see data/README.md)
  gcp/              QGIS .points files (real files); modern/  named-street layers from fim_fetch_streets.py (City of Victoria ArcGIS, OpenStreetMap), block/road CSVs
  1885/             6 crops: Index, Index_col1..4, Key
  1895/             p01..p31(+6b,7b), covers, inside-cover crops, 360° rotation sweeps p02..p10 (209 GB)
  1895_p06b_rotations/  1895_p25_rotations/
runs/               results (hunyuan/ and chandra/ moved here — MANIFEST.md has the provenance; surya/ is new)
  hunyuan/single_page/          25 sheet×rotation runs: *_content.txt, *_metadata.json, *_resized.png; overlays/
  hunyuan/p06b_rot_coords_run/  4 runs of sheet 6b with the block-number prompt
  chandra/                      10 Chandra runs (1885 index/key tables, 1895 p01 cover, p06b/p25 descriptions)
  surya/<date>_detect_*/        Surya line polygons;  surya/<date>_ocr2*/  Surya OCR 2 blocks + HTML, streets_1895.csv, blocks_1895.csv
configs/prompts/    the exact prompts used so far, one per file — used by --preset
configs/recast/     CSV column configs for csvify (reconstructed; the originals were lost)
configs/georef/     street-renaming aliases per city/year for fim_georef.py --alias
configs/viewer/     HTML template for fim_viewer.py
scripts/            fim_tile_ocr.py  fim_blocks.py  fim_areas.py  fim_georef.py  fim_locate.py  fim_fetch_streets.py  fim_crs.py  fim_viewer.py  fim_rotation_probe.py  fim_hunyuan.py  fim_overlay.sh  fim_tickfilter.py  fim_surya_detect.py  fim_surya_ocr2.py  fim_gazetteer.py  fim_chandra.sh  fim_csvify.py  fim_run_history.py
docs/run_history.md every run so far: prompt, tokens, output size, verdict
docs/HANDOFF_2026-09-14.md  end-of-day notes: commands per stage, results per sheet, what is manual, next steps
docs/viewer.html    the interactive viewer built by fim_viewer.py (self-contained; built locally, not tracked)
MANIFEST.md         where each copied file came from + the dataset move
RIGHTS.md           why no scan is committed (RBCM research-only licence) and what may be reused
```

## Dependencies (read-only, imported/called in place)

| Path | What is used | Override |
|---|---|---|
| `~/projects/hunyuan` | `hepworth_hunyuan_batch.py` (`load_pil`, `resize_max_edge`, `hunyuan_infer_one`) and `overlay_boxes.py`. Same modules `~/projects/map-region-ocr` imports. | `HUNYUAN_SRC` |
| `~/projects/chandra` | the `chandra` CLI run with `uv run`. **Needs the local, uncommitted `--prompt` patch** in `chandra/scripts/cli.py` (also writes `chandra_run.log`). Stock Chandra has no custom-prompt flag. | `CHANDRA_SRC` |
| a Python env with **surya-ocr ≥ 0.22** | Surya detection and OCR 2. `fim_surya_detect.py` runs under the interpreter named by `SURYA_PY`. The default, the shared `/opt/venvs/vllm` (surya-ocr 0.20 + vLLM 0.22, root-owned), serves OCR 2 but **its text detector is broken** (flat heatmap on any input, torch 2.11); point `SURYA_PY` at any venv with surya-ocr ≥ 0.22 (verified with 0.22.1 / torch 2.13). `.surya-extra/` is a machine-local, untracked directory of symlinks that supplies `platformdirs`, missing from the shared venv (see `fim_surya_detect.py`). | `SURYA_PY` |
| `~/projects/recast` | `recast.config` / `recast.converter` for CSV conversion; `fim_csvify.py` re-execs into `recast/.venv` if `yaml`/`bs4` are missing from the current interpreter. | `RECAST_SRC` |

HunyuanOCR needs a `transformers` build with `HunYuanVLForConditionalGeneration`; the system `python3` (transformers 5.7)
does not have it, but `~/projects/hunyuan/hunyuanocr/` (the hunyuan project's venv) does. `fim_hunyuan.py` and
`fim_tile_ocr.py` detect this and re-exec themselves under that venv (`HUNYUAN_PY` overrides the interpreter), so plain
`python3 scripts/...` works from any shell. `pip install -r requirements.txt` only adds the small pure-Python deps.

## Workflows

### A. Word coordinates for a whole sheet — tiled (HunyuanOCR)

```bash
# preview the grid and tile PNGs without touching the GPU
python3 scripts/fim_tile_ocr.py data/1895/p06b.jpg --dry-run --crop 300,150,7000,7980

# pass 1: OCR every tile, stitch, dedupe overlaps (~2.5 min/sheet incl. model load)
python3 scripts/fim_tile_ocr.py data/1895/p06b.jpg --crop 300,150,7000,7980 -o runs/hunyuan/<date>_tiles_p06b

# rotations (recommended for sheets with text at arbitrary angles): OCR each tile at 0/30/60°, union
python3 scripts/fim_tile_ocr.py data/1895/p06b.jpg --crop 300,150,7000,7980 --rotations 0,30,60 -o runs/hunyuan/<date>_tiles_p06b_rot

# pass 2 (alternative/extra): same grid shifted half a stride, unioned with pass 1 — catches words the model
# skipped or that sat on a tile edge in pass 1
python3 scripts/fim_tile_ocr.py data/1895/p06b.jpg --crop 300,150,7000,7980 --shift 435,574 \
    --merge runs/hunyuan/<date>_tiles_p06b/p06b_tiles.json -o runs/hunyuan/<date>_tiles_p06b_pass2
#   -> <out>/{p06b_tiles.json, p06b_tokens.csv, p06b_tile_overlay.jpg, tiles/*}
#   add --surya-lines runs/surya/<date>_detect_p06b/p06b_surya_lines.json for a surya_line/surya_conf review column
```

How it works: the sheet is downscaled to a 4096 px longest edge (≈0.49× for the 7800×8400 scans) and cut into 1536 px
tiles with ≥192 px overlap spread evenly (3×3 = 9 tiles per sheet); each tile is OCR'd unresized with the `text_coords`
prompt under an 8192-token cap; the model's 0–1000 tile coordinates are mapped to sheet pixels; then

- **exact duplicates** (same text, IoU ≥ 0.4, different tiles) collapse to the copy farthest from its tile edge,
- **edge fragments** (`OHNSON`, `YAT`, `LEY` — a word the tile cut) are suppressed when a longer kept token contains
  their text and ≥ 60 % of their box (`fragment=1` in the CSV, `dup_of` → the whole word),
- tokens merged from earlier passes take part in both steps (their `tile` is prefixed with the pass dir name; they
  draw orange in the overlay).

`--crop X0,Y0,X1,Y1` (source px) keeps the scan margin, Kodak colour bar and ruler out of the grid; coordinates stay
in full-sheet space regardless. `--resume` re-uses tiles whose geometry matches, so re-stitching after a code change
costs no GPU time. Tiles below `--min-ink` dark-pixel fraction are skipped. `p06b_tokens.csv` has both work-image and
source-scan pixels; `p06b_tiles.json` has everything including per-tile token counts and cap hits.

### A′. Word coordinates for a single image (HunyuanOCR)

```bash
# 1. OCR — writes runs/hunyuan/<date>_<preset>/<stem>_{resized.png,content.txt,metadata.json}
python3 scripts/fim_hunyuan.py data/1895_p06b_rotations/fireinsurance_victoria_1895_p06b_rot000_cropped.png \
    --preset text_coords_rotated         # or --prompt "..."; --max-edge 1536 default (1048 and 2048 were also used)

# 2. Boxes on the image (+ .log with the transform, + *_coordinates.json in image pixels)
scripts/fim_overlay.sh runs/hunyuan/<run>/<stem>_resized.png runs/hunyuan/<run>/<stem>_content.txt
#    extra overlay_boxes flags after "--", e.g.  -- --offset-y 4 --norm-clip 0
```

`*_content.txt` is the raw model string: `JOHNSON(529,32),(651,42)-VICTORIA-B.C(919,35),(1000,41)…` — coordinates are
0–1000 normalised to the fed image, so `x_px = x/1000 * saved_width`. `overlay_boxes.py` does this (`--scaling norm1000`)
and writes a structured `*_coordinates.json` (`bbox_xyxy` in pixels) for downstream use.

Two things to know before reading a single-page overlay:

- **Old overlays are wrong on x.** Overlays drawn before 2026-09-10 used an `overlay_boxes.py` that normalised x by the
  largest emitted coordinate (or by 1500), so boxes sat up to ~20% too far right while y was correct — they looked
  skewed. They are quarantined in `runs/hunyuan/single_page/overlays/stale_old_tool/` (README there); a log without a
  `Scale factors applied` line is from that tool. Re-render with the command above.
- **Ruler noise.** When the scan ruler / Kodak step wedge is in frame the model reads a few tick labels then keeps
  counting (1…123) with boxes extrapolated in a straight line across the map and past the image edge (y wraps from
  1000 to ~100). `scripts/fim_tickfilter.py <stem>_content.txt` drops those runs and any out-of-range/inverted box and
  writes `<stem>_filtered_content.txt` (+ metadata copy and `_filtered_report.json`) that `fim_overlay.sh` accepts unchanged. On p06b_rot112 this
  removes 175 of 190 elements and leaves the 15 real labels. Cropping the ruler out before OCR (`--crop` in the tiled
  pipeline, or the `_cropped` inputs) avoids the problem at source.

### A″. Text-line detection with Surya (where the text is, not what it says)

```bash
# SURYA_PY: any venv with surya-ocr >= 0.22 (the shared /opt/venvs/vllm detector is broken)
SURYA_PY=/path/to/surya-venv/bin/python \
python3 scripts/fim_surya_detect.py data/1895/p06b.jpg --crop 300,150,7000,7980
#   -> runs/surya/<date>_detect_p06b/{p06b_surya_lines.json, p06b_surya_overlay.jpg}
```

Runs the small Surya line detector per tile (same grid as the tiler; the detector resizes its input to 1200 px, so a
whole sheet degenerates to one blob) and stitches the polygons. ~7 s per sheet on the GPU. Each line has a 4-point
polygon (rotated quads for rotated text), an `angle_deg`, a confidence, and work/source-pixel boxes.

### A‴. Block-level GeoJSON with street labels (no model — OpenCV on the linework + the tile run's tokens)

```bash
python3 scripts/fim_blocks.py runs/hunyuan/<date>_tiles_p06b_rot
#   -> <run>/p06b_blocks_px.geojson (scan pixels — not a map until fim_georef.py runs)  p06b_blocks.csv  p06b_blocks_overlay.jpg
# open wharf blocks (no frontage line drawn): close them by hand, segments in source px
python3 scripts/fim_blocks.py runs/hunyuan/<date>_tiles_p06b_rot --close-lines 2500,900,3400,2600
```

How it works: ink mask of the sheet → seal hairline gaps → classify white space (regions on the content border or
larger than any block = street network, harbour, margins; the rest = lots, alleys, courtyards) → fill the enclosed ones,
drop lone strokes with a morphological opening (`--open-px 10`: frame, shoreline, dashed lines and the double tramway
line along Fort St, which once sealed is ~18 px wide and chained blocks 53 and 95 on p09) → one connected component
per block → polygon. Then per block: **block number** = the numeral inside with heavy strokes (block numerals are 11–21
px strokes on 6b, lot numbers 3–6 px — height alone fails because tilted lot numbers have tall boxes; a fused OCR token
`BLOCK 50` counts as the numeral 50), **lot numbers** = the other numerals inside, **streets** = alphabetic tokens
within `--street-reach` of the polygon with distance, bearing and compass side. Coordinates are source-scan pixels;
apply the sheet's georeferencing transform to get WGS84.

**Residential sheets (2026-09-17).** The 1895 book run traced p09 as 36 polygons and every one of them was a building
footprint: the residential sheets draw lot lines dashed and frontage lines faint, so a block's interior is one open
white region that (a) is bigger than the 5 % lot ceiling the old rule used, or far more often (b) leaks through a gap in
the frontage line into the street network — on p05 the largest white region held seven block numerals. Nothing in the
plain image separates such an interior from the street: a corridor severed by a dashed cross-line and an interior
joined to the street by a gap are the same shape (two regions through a porous wall). What does separate them is where
today's streets run, so the recovery happens once the sheet is placed: `fim_blocks.py --georef` (what `fim_georef.py
--retrace seeded` calls after its fit) erodes the white by `--neck-px` (16 work px: gaps narrower than 32 px pinch
off, streets stay), labels the surviving cores and grows them back inside the original white (`separate_necks`), then
sorts the pieces of each street region: the largest piece, the pieces on the border and the pieces a modern centreline
runs through (`--seed-px` 20 px of centreline) stay street; a thin leftover with no core (a margin strip, the gap
between tramway rails, a lane narrower than the neck) joins any street neighbour; a piece with a core joins when it is
open towards street space along more than `--open-max` (10 %) of its boundary — a severed corridor is open across its
whole width, a block interior only along its gap — and what remains is filled as block interior. Pieces of an enclosed
region are never touched, so lots and courtyards behave exactly as before. Without a georeference the neck step is off
(a plain `fim_blocks.py` run is the old rule): tried on all ten runs with the border and size as the only seeds, it
filled severed corridors on the dense downtown sheets and p07 fell from 12 polygons to 4, so it is an explicit option
(`--neck-px 16` on an un-georeferenced residential sheet) rather than a default. Results on the book run: p09 8 of 8
blocks with their numerals (68, 69, 54, 86, 95, 53 and the two unnumbered ones), p05 from 4 to 10 of 13 block
numerals inside a traced polygon, p06 from 4 to 8 of 11, p08 from 5 to 6 of 10; Vienna from 12 kept blocks to 52,
Vancouver from 4 to 11. The GeoJSON records which seeds were used (`street_seeds`) and the counts (`white_space`).

Scope on 6b: closed blocks 24, 23, 16 and 8 come out with the right number, lots and streets (23: Oriental Ave E,
Waddington W, Yates S, alley NW); the Provincial Law Courts and the halves of block 15 (split by its alley, numeral in
the alley) come out as polygons without a number — `--number-reach 120` labels the 15 halves `15*` (inferred) but at
that reach also mislabels a wharf strip across the street, so the default stays 80. **Not recovered:** wharf-side blocks 107, 16½, 15½,
whose lot lines stop at Wharf Street with no frontage line, so their interiors are open to the street corridor. An
automatic fix (fit a line through the row of house numbers) is in the script behind `--close-frontages` but is
unreliable — house numbers legitimately sit in the corridor on other blocks — so it is off; `--close-lines` is the
dependable route for now (2–3 segments per sheet).

### A⁗. Georeference the sheet from its OCR (no control points clicked; any city)

```bash
# 0. (only if you do not know where the sheet is) let its street names say: ranked places, a box and a fetch command each
python3 scripts/fim_locate.py runs/hunyuan/<run> --list-only                # the names it would ask Nominatim about; no network
python3 scripts/fim_locate.py runs/hunyuan/<run> [--country cc] [--near "<region>"]   # -> <run>/<stem>_locate.json, nothing chosen
# 1. a modern named-street layer for the area — OpenStreetMap for any area on Earth, or a municipal ArcGIS layer.
#    The area is a box, never an administrative boundary: a sheet across a municipal line just needs a box that covers both.
python3 scripts/fim_fetch_streets.py --place "Victoria, British Columbia" --slug victoria_osm       # -> data/modern/victoria_osm_streets_epsg32610.geojson
python3 scripts/fim_fetch_streets.py --place "Victoria, British Columbia" --place "Esquimalt, British Columbia" --pad-km 1 --slug victoria_west   # union of two places
python3 scripts/fim_fetch_streets.py --bbox 43.63,-79.42,43.68,-79.35 --slug toronto_core          # S,W,N,E in degrees; UTM zone picked automatically
python3 scripts/fim_fetch_streets.py --from-locate runs/hunyuan/<run> --candidate 1 --slug <slug>   # the box fim_locate proposed; --candidate is required
python3 scripts/fim_fetch_streets.py --bbox 48.40,-123.40,48.45,-123.32 --slug victoria_city --epsg 26910 \
    --arcgis https://maps.victoria.ca/server/rest/services/OpenData/OpenData_Transportation/MapServer/25
# 2. fit a tile run to it
python3 scripts/fim_georef.py runs/hunyuan/<date>_tiles_p06b_rot --streets data/modern/victoria_city_streets_epsg26910.geojson \
    --alias configs/georef/aliases_victoria_1895.json
#   -> <run>/p06b_georef.json               affine source px -> layer CRS (+inverse), per-label residuals, RMS, implied dpi
#      <run>/p06b_georef.points             QGIS Georeferencer GCPs (pixel <-> snapped centreline point), CRS in the header
#      <run>/p06b.jgw                       world file: copy next to data/1895/p06b.jpg and QGIS/GDAL read the scan georeferenced
#      <run>/p06b_blocks_epsg26910.geojson, p06b_blocks_wgs84.geojson   fim_blocks.py polygons in the world, cleaned (below)
#      <run>/p06b_blocks_rejected_*.geojson  traced shapes that are not blocks (frames, buildings, fragments) with the reason
#      <run>/p06b_page_wgs84.geojson        footprint of the whole scan and of the tiled content box
#      <run>/p06b_tokens_wgs84.geojson      every kept OCR token as a WGS84 polygon with its text
#      <run>/p06b_georef_overlay.jpg        modern centrelines/intersections back-projected onto the scan — the check
```

Nothing in the fit is specific to Victoria. `fim_georef.py` takes any GeoJSON of named centrelines in a metric CRS (the
name field is auto-detected — `name`, `STNAME`+`STTYPE`, `StreetName`, `FULLNAME`… — or given with `--name-field`);
the CRS is read from the file's `crs` member (any UTM zone on WGS84/NAD83/ETRS89 is handled natively in
`scripts/fim_crs.py`; other projections need `pip install pyproj`). Intersections are derived from the centrelines'
shared vertices, so no second layer is needed. Street names are matched after normalising the type word, so OSM's
"Yates Street" and the city's `Yates` + `ST` both become `YATES ST`. Renamings since the plan go in a small JSON
(`configs/georef/aliases_victoria_1895.json`: *Bastion* → Bastion Sq/St, *Commercial St* → Commercial Alley).

**Locating a sheet from its own names (`fim_locate.py`).** The lookup service is Nominatim, because an Overpass name
query without a bounding box is a planet-wide scan the public mirrors refuse, while Nominatim indexes exactly
name → feature with an address hierarchy (so each candidate can be described from the hits themselves, no reverse
geocoding). Tokens inside the traced blocks are dropped first (`street_candidates`), then map furniture, digits and
company-style words; names carrying a type word rank first, bare names are asked for with the type word the sheet
uses most ('ST' on a Goad plan, 'GASSE' on a Viennese one — `sheet_type_word`) and once more bare if that finds no
road. Nominatim does not enumerate every street with a name on Earth — it returns its best-ranked forty — so a name
unique to one city may come back as forty way segments while a common one comes back from twenty cities. Each name is
therefore weighted `1/sqrt(number of distinct places it was found in)`, hits are clustered greedily within
`--radius-km` (6 km; one single-link step joins an adjacent municipality), and for the best `--verify` candidates the
still-missing names are asked for again *inside that candidate's box* (a bounded search, which also finds
'West <Name> Street' spellings the global ranking dropped). Confirmed names join the count; candidates whose hit boxes overlap are merged (one city found twice). A metropolis
holds nearly every common street name somewhere, so the final ranking is by the *core*: the names within `--core-km`
(1.5 km) of one spot, weighted the same way; the proposed box is that core padded by `--pad-km`, not the whole city.
On the 1895 sheet p06 this is what put the right city (9 names within 1.5 km) above a capital with 16 names spread over
25 km. Everything Nominatim answered is cached in `<run>/<stem>_locate_cache.json`, so re-scoring with other flags costs no
requests. The output is a proposal: a person copies a fetch command or names a candidate number.

How it fits: every alphabetic token from the tile run that names a street is a point-to-line constraint — the label's
centre must land on that street's modern centreline. A coarse search (rotation every 10°, five scales, 25 m
translation grid over the neighbourhood where the named streets intersect) seeds a point-to-line ICP that solves a
similarity transform (rotation × reflection, since scan y points down), rejects labels farther than max(12 m,
3 × median) from their street, then solves a full affine on the inliers. Type-only labels (ALLEY, AVE) are ignored; a
label whose street meets none of the other named streets is dropped (the water label *Harbour* → Harbour Rd across the
Inner Harbour). No compass-rose detection: rotation, scale and skew all fall out of the fit. Needs only numpy + OpenCV.

On 6b, 12 labels match; 11 fit and *Court Alley* is the one outlier (32 m — the modern alley is west of the 1895 one,
Bastion Square was rebuilt; the overlay shows exactly that). Two reference layers, same OCR:

| layer | RMS | max inlier | scale m/px | rotation | shear | implied dpi at 50 ft/in |
|---|---|---|---|---|---|---|
| City of Victoria *Streets* (EPSG:26910, `victoria_city_streets_epsg26910.geojson`) | **2.1 m** | 4.1 m | 0.0494 × 0.0502 | −8.8° | 1.6° | 308 |
| OpenStreetMap (EPSG:32610) | 3.2 m | 8.5 m | 0.0506 × 0.0489 | −15.8° | −4.5° | 301 |

The city layer is the better reference: isotropic scale, near-zero shear, and it implies the 300 dpi scan the sheet
plainly is. The OSM fit is looser because OSM's alleys and the pedestrian Bastion Square are drawn approximately, and
point-to-line constraints let rotation trade against shear when the N–S streets are few; the two fits differ by
under 10 m at the block centroids but 29 m at the far NW corner of the sheet, where no label constrains them. Use municipal centrelines when a city publishes them, OSM otherwise, and treat
shear ≫ 2° or anisotropic scale as a warning. Only sheets with named streets in both orientations can be fitted (a
sheet of one long street constrains nothing across it); `--min-labels` (default 6) refuses otherwise.

**Guard rails and helpers added 2026-09-16, after the first book run (sheets 4–10).** Three of seven sheets went wrong
in three different ways, each now handled in a city-agnostic way:

- *Repetition loops.* On the densest sheet (p07) 12 of 20 tiles hit the 4096-token cap and the model looped: `BROAD`
  236 times at one box, `M` marching along a tile edge 290 times. Those tokens all "matched" Broad St and swamped the fit
  (297 inliers, RMS 1.5 m, then a degenerate affine with a 0.0026 m/px y-scale). `fim_tile_ocr.py` now keeps only the
  first of a run of 5+ consecutive identical words when it parses a tile (`drop_runaway`; real lot numbers repeat, but
  never back to back). Re-parsing p07 with `--resume` dropped ~2,400 looped tokens and kept 1,716.
- *Implausible affine.* On p08 every label but two sat on east–west streets, so the affine step stretched x by 2×
  (0.099 × 0.050 m/px) while keeping a 4.4 m RMS. Paper shrink and scanner skew are under 2 % and 1°, so
  `fim_georef.py` keeps the affine only if the x/y scales agree within `--max-anisotropy` (4 %) and the shear is under
  `--max-shear-deg` (2°); otherwise the similarity fit is kept and `transform: similarity` / `affine_rejected` are
  written to `<stem>_georef.json`.
- *Too few names.* p05 read only Burdett and Humboldt: its other streets are renamed (Kane → Broughton, Rae →
  Courtney), respelled (Blanchard, Penwell → Penwill) or fragments (OUGLAS, DOUGL). Three helpers, all opt-in:
  `--fuzzy` accepts a label one edit from a street or alias name, or a 5+ letter prefix/suffix of one, when exactly one
  name fits; `--near RUN...` takes the georeferenced runs of neighbouring sheets of the same book and limits the
  translation search to one sheet around their footprints, with their scale added to the seeds (an atlas names its
  neighbours in the margins, "SEE SHEET No 4"); and after every fit the printout lists **alias candidates** — unmatched
  upper-case words lying within the outlier threshold of a modern centreline once the sheet is placed — which is how
  KANE → BROUGHTON ST (0.7 m) and BLANCHARD → BLANSHARD ST were found and added to the alias file. The neighbour prior is
  only meaningful for a book, so only `fim_batch.py` uses it, in a second pass over the sheets that failed, and only
  when several sheets were given.
- *A log of name changes.* `<stem>_street_names_wgs84.geojson` records, per sheet, every label that was renamed
  (alias), respelled (fuzzy), moved (fit outlier) or is a candidate, with the modern street's centreline within the
  sheet as geometry, the name on the plan, the plan year (`--year`, else the year in the alias file's name) and the
  modern name from the layer — a linked-data trail; `fim_merge.py` joins them across a book.
- *Building labels that spell a street name.* On p08 the second line of a lot label, "LIME / STORE", matched Store St
  and was rejected as a 598 m outlier: harmless to the fit, but noise in the outlier list and a false "moved" entry in
  the names log. The fit chose labels by name alone. Now the traced blocks are loaded **before** matching and a word
  whose centre lies inside a block (any depth: building labels hug the lot frontage) is set aside as kind `building` (the blocks are
  under-traced rather than over-traced, so a real street label is almost never inside one). Alias candidates get the
  same test. The split is importable: `fim_georef.load_block_rings(run, stem)` and `street_candidates(tokens, rings)`
  (returns the tokens outside blocks and stamps every token with `in_block` / `in_block_depth_px`; the flags are also
  written to `<stem>_tokens_wgs84.geojson`), so other scripts reuse it rather than re-deriving it.
- *Rotation from the words, not their positions.* p08 came out 3° under-rotated (−6.5° where its neighbours and the
  orthogonal modern grid say −9.6°) and p04 a little: a label's centre is only a point somewhere in a 20 m corridor, and
  with 23 such points on a 330 m sheet two or three 12 m strays (a VIEW at the left edge, a FORT at the right) can tilt a
  position-only similarity by 3° while keeping a 5 m RMS; the affine then wanted a 4° shear and was rightly refused.
  Chloe's original idea fixes it at no cost: a street name is printed along its street, so its box already says which
  way the street runs (wide = along x, tall = along y, rotated views give the angle). `label_direction` reads that off
  the existing OCR box; `icp_label_rotation` takes the weighted median over labels of (modern segment bearing at the
  snapped point − text direction) as the rotation and solves only scale + translation from the positions
  (`solve_fixed_rot`). p08: −9.58°, and the two Yates labels that were bending the sheet are now honest 12 m outliers.
  Falls back to the free fit with fewer than three oriented labels (`--rotation free` forces it). The text direction is
  coarse — the rotated OCR views are 30° apart — and on the Vancouver 1912 sheet, whose streets run diagonally, it
  placed the sheet 16° off with 6 inliers where the positions alone place 12 at 0.5 m; so since 2026-09-17 both fits
  are run and the position-only one wins when it places at least half again as many labels (`rotation_source` says
  which; ties go to the text direction, which is what fixes p08). The same text
  directions prefilter the coarse search: each of the 36 candidate rotations is scored by how many oriented labels
  would run along their candidate street (no translation needed), and only the agreeing 4–6 go through the
  translation sweep. Identical fits, `fim_georef.py` down from ~50 s to ~10 s per sheet. The scale seeds are *not*
  narrowed to the sheet's stated scale on purpose: OCR can read "50" as 5 or 500.
- `fim_batch.py` runs a book end to end (OCR → blocks → fit, second pass with `--near --fuzzy --min-labels 4`, optional
  re-OCR with rotated views, `--merge` into one GeoJSON per kind via `fim_merge.py`).
- *Other languages, other centuries (2026-09-17).* Measured on the Vienna 1912 tile against the OSM layer: of 207 named
  streets with centreline inside the footprint, the OCR holds 26 exactly (after type-word normalisation), 46 within two
  edits (Karnthner/KARNTNER, Himmelfort/HIMMELPFORT, Sellerstätte/SEILERSTATTE), 11 as fragments and 124 not at all
  (Parkring, Stephansplatz, Rotenturmstrasse among them — blurry bold Fraktur-adjacent print). Yet the fit had used
  only 12: the matcher was throwing away more than the OCR missed. Two rules changed. (1) "A label's street must share
  an intersection vertex with another matched street" became "must lie within `--lonely-m` (300 m) of another matched
  street": Singer-Strasse meets Kärntner Strasse, which the OCR had not read, so it and 14 other real labels were
  dropped as lonely; the metric rule still removes a landmark or date whose name is a road elsewhere (Vancouver's
  "Dominion", p08's "MAY, 1891."). (2) `spell_key`: orthographic equivalences applied to BOTH the label and the layer
  name before comparing — TH→T, PH→F, DT→T, hard C→K, non-initial Y→I (the German 1901 reform: Rothenthurm/Rotenturm,
  Carl/Karl; Freyung/Freiung) — a language-level table in the script, off with `--spelling exact`. Result on Vienna
  without `--fuzzy`: 34 labels matched, 25 inliers, RMS 1.8 m (was 10 / 6 / 6.5 m); 50 blocks kept. With `--fuzzy` it
  matches 67 but the RMS goes to 5.4 m — Bank→BANK GASSE, Somburger→HAMBURGER, Verein→VEREINS are the kind of hit a
  one-edit rule makes on a 3,000-token sheet — so fuzzy stays opt-in and is best kept for sheets with few labels.
  Victoria and Vancouver fits are unchanged. Still open for the 124 unread names: a second OCR pass (Surya's line
  detector plus recognition would give phrase-level boxes, good enough to match a name to a street and snap the box
  centre) and an alias file of pre-1901 spellings the folds do not cover; the language itself needs no model — the
  layer's type words (GASSE/STRASSE vs ST/AVE) already say it, which is how `FUSED_TYPE_WORDS` is triggered.

**Buildings inside the blocks (2026-09-17).** `fim_blocks.py --buildings enclosed` (default) writes
`<stem>_buildings_px.geojson`: every enclosed white region inside a traced block, traced back out to its drawn line and
linked to the block by `block_id` (`<sheet>:block:<number>`, or `<sheet>:block:fid<n>` when the block has no numeral;
a part cut by fim_georef gets `:part<k>`), with its own `building_id` (`<block_id>:bldg<n>`). Nothing is inferred
about what a shape is — footprint, yard, courtyard. The attributes are (a) the OCR tokens whose centre lies inside
the outline, `text_inside` in reading order and the same split by regex into `numerals_inside` (`\d+(½|1/2)?`,
'BLOCK n' folded to n) and `words_inside` (two or more letters), plus a `floors` field that is null by default — on Goad
plans the numeral inside a footprint is not reliably the storey count, so a person fills it (Chloe, 2026-09-17: first asked
for the rule, then took it back for Goad) — and is filled only with `--floors single-numeral-1-3`, the Sanborn
convention: exactly one numeral inside the outline reading 1 to 3 inclusive (1½ → 1.5). The words (business or building
name) are left to the consumer; and (b) the measured
wash inside the outline, `wash_rgb`, `wash_chroma` (mean Lab chroma over the paper's median) and `hue_deg`, which are
read into a `material` only when the plan's colour key is given as a config, `--legend configs/legend/<edition>.json`.
The key is written the way the printed legend words it: each material names its **colour word** ("yellow", "pink",
"grey"; German and French words too), which `COLOUR_WORDS` turns into a deliberately broad hue band — scans differ in
colour balance, and many keys are text only ("red brick, grey stone") with no fill to measure — or, for a key
calibrated from a sheet's own reference fills, an exact `hue_deg` range. `min_chroma` separates a wash from paper (the
chroma is measured relative to the sheet's own paper), `untinted` is the key's word for a paper-white outline, and
"grey" means little chroma but darker than the paper (`wash_lightness_delta`). The Goad/Sanborn key ships as
`goad_sanborn_default.json` and must be checked against the sheet's printed key; Vienna has no colour and gets no
legend, so its `material` is null. Deriving a calibrated key from a crop of the sheet's own printed legend (measure
each reference fill, write the hue ranges) is the natural next step and is not done. Chloe's rule (2026-09-17): nothing about a building is inferred beyond what the OCR
contains, read with regex, except a colour flood matched to a key that is a config. A region larger than `--building-max-share` (60 %) of its block is the block's
own ground and is skipped, as is the open interior recovered at the necks. fim_georef.py places the outlines after
cleaning the blocks and re-links each to the block that finally holds its centroid — a footprint whose block was split
follows its part; one whose block was rejected is kept with `block_id` null and `orphan` true, so nothing disappears
silently — and writes `<stem>_buildings_{epsg<code>,wgs84}.geojson`; fim_merge.py and fim_batch.py include
`buildings` by default. p09: 211 outlines in 8 blocks; Vancouver 1912: 286; Vienna: 621 (courtyards and rooms of a
hatched plan). Known impurity: the numerals inside footprints are still also counted in the block's `lot_numbers`.
The viewer does not draw the buildings layer yet.

**Cleaning the blocks once the sheet is georeferenced.** After the fit, `fim_georef.py` first traces the blocks again
with the modern centrelines as street seeds (`--retrace seeded`, default; `--retrace keep` uses the run's existing
`<stem>_blocks_px.geojson`; see "Residential sheets" above) and rewrites `<stem>_blocks_px.geojson`, `.csv` and
`_overlay.jpg`. `fim_blocks.py` knows nothing about
streets, so its `streets` list is every alphabetic token near a polygon (on a dense sheet that includes BAKERY, STABLE,
"Scale 400 Feet…") and its polygons include anything closed by linework (an inset's frame, a school building). The
georeferenced blocks GeoJSON fixes both with what the fit knows: `streets_1895` keeps only the OCR labels that matched
a modern street (with the modern name and the fit residual), `streets_modern` lists the modern centrelines that bound
the polygon (within `--block-street-reach-m`, along a real share of its edge, with compass side), everything else the
tracer saw goes to `nearby_text`. Polygons are rejected, with the reason written to `<stem>_blocks_rejected_*.geojson`,
when they are a thin strip (compactness < 0.15: an inset frame or border), contain OCR street labels whose street lies
elsewhere (an inset of another area), have two or more modern centrelines running well inside them (a compound), or —
under the default `--lots numbered` — hold neither a bold block numeral nor two lot numbers (a building outline or
fragment; before 2026-09-17 the block numeral did not count and p05's blocks 80, 106 and 50 were thrown out for having
lots the OCR had not read). `--lots none` is for plans without lot subdivisions or block numbers (the Vienna
Generalstadtplan: the small numbers are house numbers, the 4-digit ones inside buildings are construction years): no
numeral test at all, `block_number` is null and the numerals go to `numbers_inside`; the pre-fit exclusion of words
inside traced polygons is also skipped, because without numerals nothing tells a block from a compound or the canal
before the fit and it was setting five real street labels aside (Wallner-Strasse 2 px inside a polygon edge). A polygon
with modern centrelines running well inside it is
blocks the tracer merged across a narrow street: it is **cut along those centrelines** (drawn 14 m wide) before any
other test and each part becomes a block (`split_from` records the parent and the cut); a part under 20 % of the parent
is a sliver where the street was widened or realigned into the 1895 block and is rejected. On p25 the 208/209 compound splits along Rebecca St
and Mason St, which shows St. Louis St and Elizabeth St are both today's Mason St. Where the cut does not separate the
parts (the modern street stops short) the polygon is kept with `merged_across`. The pixel-space
`<stem>_blocks_px.geojson`/`.csv` are left raw.

### A⁗′. Colour-washed areas (key plans) — `fim_areas.py`, run on purpose

```bash
python3 scripts/fim_areas.py runs/hunyuan/<date>_tiles_p03_t1024_rot     # -> <run>/p03_areas_px.geojson, _areas.csv, _areas_overlay.jpg
python3 scripts/fim_georef.py runs/hunyuan/<date>_tiles_p03_t1024_rot --streets data/modern/capital_region_crd_streets_epsg26910.geojson
#   -> also p03_areas_epsg26910.geojson / p03_areas_wgs84.geojson
```

Key plans mark each detailed sheet's coverage with a colour wash, not an outline, so the block tracer sees nothing.
`fim_areas.py` estimates the paper colour, takes the chroma offset of every bright pixel from it, clusters the strong
offsets in the Lab a/b plane (k chosen by silhouette; on cream paper a "blue" wash is merely *less yellow* than the
paper and has almost no HSV saturation, so hue/saturation rules fail), assigns weak-wash pixels to the nearest tint,
closes gaps of a street's width within each tint so one tinted area is one polygon, and drops components with no
numerals inside that touch the border (page stains) or are thin (the water tint along the shore). The area's number is
the big upright numeral inside (≥ 1.9 × the median numeral height — a key plan's sheet numbers are 2–2.5 × its block
numbers; numerals read in rotated views are excluded because their boxes are inflated and they are often misread); an
area holding two big numerals is split between them. On p03 this yields 22 areas numbered 6–30 exactly as printed; on
p02, 9 areas (26, 18, 20, 27 and "431", HunyuanOCR's reading of 31). You decide when to run it — nothing detects tints.

**Second sheet, p25 (Fernwood, 100 ft = 1 inch, 2026-09-14).** Same commands, no per-sheet tuning beyond the crop box.
Two OCR runs of the same scan, then blocks + georeference on each:

| tile run | model calls | GPU time | cap hits | tokens kept | street labels | RMS | rotation |
|---|---|---|---|---|---|---|---|
| `2026-09-14_tiles_p25_rot` — 3×3 tiles of 1536 px, views 0/30/60°, cap 8192 | 27 | 37 min | 16 | 4952 (mostly runaway-loop junk) | 28 | 5.0 m | −5.05° |
| `2026-09-14_tiles_p25_t1024` — 4×5 tiles of 1024 px, upright only, cap 4096 | 20 | 8.6 min | 2 | 1910 | 30 | **3.8 m** | −4.92° |

At 100 ft/in a 1536 px tile holds ~4× the text of a 6b tile: 16 of 27 views hit the 8192-token cap, many as runaway
loops (8192 tokens, a few hundred characters). Smaller tiles with a lower cap fixed it in a quarter of the time and read
more real street names (Alfred, Elizabeth, Putnam, St. Louis were missed by the rotated run). Both runs agree on
rotation and scale; 0.0974 m/px at 100 ft/in implies a **313 dpi** scan, matching the 308 dpi found on 6b at 50 ft/in.
Outliers in both: the *Yates* label inside the sheet-30 inset (488 m — the inset is another part of town) and one
*Pandora* label where the modern avenue curves at Vancouver St (18 m). Street names on the sheet with no modern
counterpart in the layer (Frederick, Putnam, Alfred, Elizabeth, St. Louis, Cadboro Bay) are simply unused — renamed or
gone; add them to the alias file if their modern names are known. Upright-only OCR is enough for georeferencing because
street names are printed along the axes and the model reads vertical text unrotated; rotated views are for lot numbers
along diagonal streets and should be run only on tiles where Surya finds tilted lines.

**Cost at scale (prototype numbers, single GPU, HF transformers, one tile per call).** ~9 min per dense sheet upright, so
~5 h for the 37-sheet book; ×3 with 0/30/60° views. The known path down: serve HunyuanOCR through vLLM (batched tiles,
5–10× throughput), keep the 4096 cap with 1024 px tiles, rotated views only where needed, and abort runaway generation
when the tail repeats. The fitting stages (blocks, georeference) are seconds per sheet on CPU.

## What the results say so far (Sept 2026)

- **Orientation matters enormously for HunyuanOCR.** On sheets 2 and 6, only a handful of rotations produce a full
  transcript (~20–25 KB); most rotations return a few hundred bytes. The 360° sweeps in `data/1895/` exist to map this.
  See the "Rotation sensitivity" table in `docs/run_history.md`.
- **Tiling works (2026-09-10, sheet 6b).** 9 tiles at 0.49× scale, 3–17 s each, none near the 8192-token cap. Pass 1
  kept 219 tokens; pass 2 with a half-stride shift added the 11 the model skipped (incl. WHARF) → **230 tokens, every
  street name on the sheet** (JOHNSON, YATES, FORT, BROUGHTON, LANGLEY, WADDINGTON, ORIENTAL AVE, COMMERCIAL ST,
  COURT ALLEY, CHANCERY LANE, BASTION SQUARE, PROVINCIAL LAW COURTS, WHARF, Victoria Harbour, scale bar) plus ~190
  building/lot numbers, boxes landing on the glyphs. See `runs/hunyuan/2026-09-10_tiles_p06b*` and `docs/run_history.md`.
  Not yet verified against ground truth; the overlay is the check for now.
- **Surya (2026-09-10, sheet 6b): useful as a geometry check, not as an OCR stage.** Its line detector (surya 0.22.1;
  the shared 0.20 venv's detector is broken) finds 213 line polygons in 7 s with correct orientation (WHARF as a 70°
  quad, COMMERCIAL/WADDINGTON/LANGLEY as 90° boxes). 210 of HunyuanOCR's 230 tokens fall inside a Surya line; the 20
  that don't are real text Surya missed — letter-spaced labels (`Y A T E S`, `BASTION SQUARE`) and the big cursive
  `Victoria Harbour`. Feeding the 37 Surya-only boxes to HunyuanOCR as a fill pass added **nothing**: they are pieces of
  multi-word tokens Hunyuan already had (`LEY`, `LLEY`, `COURT`, `LANE`, `AVE`), letters of the cursive, or noise
  (every box with confidence < 0.45). `fim_tile_ocr.py --surya-lines` tags tokens with their Surya line for review.
- **Surya OCR 2 (2026-09-10, local vLLM): good on the 1895 inside-cover tables, wrong on the 1885 index, useless on sheets.**
  The 1895 street index and block-number table come back as HTML tables in 3–8 s per crop; `fim_gazetteer.py` turns
  them into `streets_1895.csv` (192 rows, 114 streets, 86 house-number ranges, every row but one cross-reference with
  a sheet) and `blocks_1895.csv` (blocks 1–130 + 113½, all present, 1891-edition sheet and old-edition sheet each).
  Spot-checked against the page (Blanchard, Fort, Quadra, Yates): ranges and sheets right; the one systematic loss is
  the printed `West Side`/`South Side` label at the switch between sides, dropped in almost every read — recovered from
  the house-number restart (parity is consistent per side afterwards). Reads of the same row differ between crops
  (`194-263` vs `194-268`, `18-66` vs `18½-66`); the column crops win. On the **1885** index col2 it hallucinated the
  sheet column (45 of 59 rows read as sheet 10; agrees with Chandra on 11/59, and Chandra matches the page) — keep
  Chandra for 1885. On sheet 6b it returns one `Figure` block and reads the cursive *Victoria Harbour* as
  "Harold of Manchester": not a sheet-OCR model.
- **Rotation (probe on 6b tile r1c1, 12 angles, constant canvas): HunyuanOCR reads text only when it is presented
  within ~20–30° of horizontal or vertical.** Recall of the upright token set: 100% at 0°, 77–89% at 90/180/270°,
  46–61% at every off-axis angle — yet WHARF (printed at ~70°) was *only* read at 60/90/120/180/240/270°, i.e. when
  rotating the view brought it near an axis. So orientation detection is not needed: OCR each tile at 0/30/60°
  (`fim_tile_ocr.py --rotations 0,30,60`) and every text angle is within 15° of an axis in one view; boxes are
  mapped back and unioned through the same dedupe. This replaces the 360° whole-sheet rotation sweeps in `data/1895/`.
  Surya's polygon angles are not a substitute: short labels have no usable long axis and quads can't tell 70° from 250°.
- **0/30/60° views on the whole of 6b (27 OCR calls, 242 s generate):** 252 tokens kept vs 230 from the shifted two-pass.
  200 came from the upright view, 29 from 30°, 23 from 60°; 50 are not in the two-pass set and 42 of those lie in a Surya
  line (real text — chiefly the ~70° lot numbers along Wharf St, plus WHARF / YATES / BASTION SQUARE read in several views).
  The two-pass set has 28 the rotation run lacks, so framing and rotation are complementary. Dedupe had to move from
  box-IoU to polygon-centre distance (a tilted word's axis box is inflated); a conflict rule suppresses a rotated
  misread at the same spot as an upright read. Residual junk: rotated views misread the cursive *Victoria* as
  `Vicona` / `Vic T O` (kept, no upright overlap — review column `conflict`/`rotation` in the CSV).
- **Block-level GeoJSON (2026-09-10, 6b):** `fim_blocks.py` recovers the closed blocks with number, lot numbers and
  neighbouring streets by side; the open wharf blocks need `--close-lines`.
- **Key plans p02 and p03 (2026-09-14):** both fit at 0.52 m/px, −16°, on the CRD regional centrelines (6.8 m RMS over
  78 labels on p03; 12.8 m over 47 on p02) with scale seeds taken from the sheet's own "Scale: 500 feet = 1 inch"
  statement. `fim_areas.py` (new, run explicitly on tinted sheets) traces the colour-washed sheet areas and reads the
  big sheet numerals: p03 gives 22 areas numbered 6–30 as printed. `fim_viewer.py` builds the interactive page
  (`docs/viewer.html`). Full notes: `docs/HANDOFF_2026-09-14.md`.
- **Georeferenced from OCR (2026-09-14, 6b and p25):** `fim_georef.py` fits the sheet to modern street centrelines using only
  the OCR'd street labels — RMS 2.1 m over 11 labels on 6b and 3.8 m over 28 labels on p25 against the City of Victoria layer (3.2 m on 6b
  against OpenStreetMap), no control points clicked. Page footprints (scan outline + content box) are written too. Works for any city: `fim_fetch_streets.py` pulls the reference layer for any bounding box or
  place name. Blocks and every token now exist in the layer CRS and WGS84. The 1884 `.points` file and the modern block/road CSVs turned out not to be usable for
  this (see `data/README.md`): GCPs are image-specific, that file's source coordinates are metres not pixels, the modern
  `BlockRoll` numbering is unrelated to Goad's, and the roads CSV has no geometry.
- **Constraint:** every stage runs on this machine — local open weights (HunyuanOCR 1B, Surya, Chandra; vLLM-served
  models are fine) or plain OpenCV. Nothing with per-usage or token costs is used anywhere in the pipeline.
- **Full transcripts hit the 16 384-token cap** and the tail is repetition (`hunyuan_infer_one` trims the repeated
  suffix, but coverage of the lower part of the sheet is lost). Cropping the sheet (`p06b_rot000_cropped`) is what made
  sheet 6b work; the uncropped 1420×1536 run returned the single character `6`. Tiling is the obvious next step.
- **Chandra handles the 1885 index columns** (`street | relative_position | sheet`, ~70 rows each) and expands ditto
  marks when asked (`index_1885_dittos` preset). The block-number table on the full index page comes back as two
  side-by-side column pairs (`configs/recast/fireinsurance_1885_blocks.yaml`).
- **Chandra prose on whole sheets is unreliable**: `p25_rot000` degenerates into thousands of `100' = N'` lines;
  `p06b_rot000` produced a plausible but unverifiable feature list. Use it for tables and cover text, HunyuanOCR for
  sheet content.
- **Not yet run**: the 1895 `-specials*.jpg` crops (churches, hotels, firms) are OCR'd by Surya OCR 2 but not parsed
  into a table; Chandra has not been run on the 1895 inside-cover crops (`configs/recast/fireinsurance_1895_streets.yaml`
  is ready) — a second read would settle the residual digit disagreements. No ground truth exists for any page yet, so
  all accuracy statements above are by inspection.

## Provenance / housekeeping

- Everything under `runs/` was **moved** from `~/projects/hunyuan/{input,output}` and `~/projects/chandra/output/fireinsurance_*`
  (verified byte-identical before the originals were deleted). Each old location has a `FIREINSURANCE_MOVED.md`
  pointing here; `MANIFEST.md` lists each file's former path.
- `~/projects/datasets/1895` was **moved** to `~/projects/datasets/fire_insurance_maps/1895` and replaced by a symlink,
  so `datasets/fire_insurance_maps/` now holds all raw scans. Details in `data/README.md`.
- `.gitignore` excludes rasters under `runs/` (~110 MB, regenerable). Remove those lines to track them.
- `~/projects/hunyuan/hunyuan_transformers.py` (hard-coded to sheet 6b) and the deleted `fireinsurance_*` configs in
  `~/projects/recast/configs` are superseded by `scripts/fim_hunyuan.py` and `configs/recast/` here.
