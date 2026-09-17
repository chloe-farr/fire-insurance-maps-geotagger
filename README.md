# fire-insurance-maps

Turn a scanned historical city plan into GeoJSON, using the text printed on it.

The scripts read every word on the sheet with an OCR model, trace the city blocks from the linework, match the street
names to today's street centrelines, and from those matches work out where the sheet sits on the Earth: no control
points to click, no GIS experience needed. Built for Chas. E. Goad's fire insurance plans of Victoria B.C. (1885–1895),
tested on Goad's 1912 Vancouver atlas and on the 1912 Generalstadtplan of Vienna (German, no lot numbers, no colour). Any
city with named streets on the sheet and in OpenStreetMap should work.

```
scan  ──▶  1. OCR every word        ──▶  2. trace the blocks   ──▶  4. fit to modern streets  ──▶  GeoJSON + world file
           (HunyuanOCR, GPU)             (OpenCV, no model)         (3. street layer from OSM)      + interactive viewer
```

Everything runs on your own machine with open-weight models. Nothing is sent to a paid API.

---

## What you need

| | |
|---|---|
| Computer | Linux (tested on Ubuntu 22.04). An **NVIDIA GPU with about 20 GB free memory** for the OCR stage (RTX 6000 Ada used here; a 24 GB card is fine). Every other stage runs on the CPU in seconds to minutes. |
| Software | Python 3.10 or newer, `git`. Nothing else system-wide. |
| Disk | ~3 GB for the OCR model (downloaded on first run) plus ~100 MB per sheet of results. |
| Network | Only on the first OCR run (about 2 GB of model weights from Hugging Face) and when fetching a street layer (OpenStreetMap). |

## Setup (once, about 10 minutes)

```bash
git clone <this repo> fire-insurance-maps
cd fire-insurance-maps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Check it worked:

```bash
.venv/bin/python -c "import torch; from transformers import HunYuanVLForConditionalGeneration; print('GPU:', torch.cuda.is_available())"
```

You should see `GPU: True`. Every command below is written as `python3 scripts/...`; the scripts notice the `.venv`
and use it themselves, so you do not need to "activate" anything. (If you keep the environment elsewhere, set
`HUNYUAN_PY=/path/to/that/python`.)

Check the CPU stages without a GPU (block tracing, name matching; a few seconds):

```bash
.venv/bin/pip install pytest
python3 -m pytest tests -q
```

## Try it on the included sheet (about 30 minutes, mostly waiting)

The repo ships one public-domain sheet: a tile of Goad's 1912 Vancouver atlas covering downtown and Gastown,
`data/example/vancouver_1912_MAP342a_04.tif`, together with a modern street layer for Vancouver. Four commands take it
from scan to GeoJSON.

**1. Read the words.** About 25 minutes on the GPU; the model downloads first time.

```bash
python3 scripts/fim_tile_ocr.py data/example/vancouver_1912_MAP342a_04.tif \
    --work-max-edge 0 --tile 1536 --rotations 0,30,60 --max-new-tokens 8192 \
    --preset text_coords_vancouver_1912 -o runs/hunyuan/demo_vancouver
```

Open `runs/hunyuan/demo_vancouver/vancouver_1912_MAP342a_04_tile_overlay.jpg`: every word the model read, boxed on the
sheet. Expect around 1,900 words including nine street names.

**2. Trace the blocks.** Seconds.

```bash
python3 scripts/fim_blocks.py runs/hunyuan/demo_vancouver
```

Open `..._blocks_overlay.jpg`: each city block filled in a colour, with its block number and neighbouring streets, and
every enclosed outline inside it in magenta; `..._buildings_px.geojson` holds those outlines with their block id, the
OCR tokens inside them (numerals and words; `floors` stays null for a person to fill unless `--floors single-numeral-1-3`, the Sanborn convention) and their measured wash colour, which becomes a material only when you
pass the plan's colour key as a config (`--legend configs/legend/goad_sanborn_default.json` for Goad and Sanborn). This first pass only closes blocks whose outlines are drawn solid; step 3 traces them again with today's streets as
evidence, which also recovers residential blocks whose dashed frontage lines let the interior run into the street.

**3. Fit the sheet to the modern streets.** A couple of minutes.

```bash
python3 scripts/fim_georef.py runs/hunyuan/demo_vancouver --streets data/modern/vancouver_streets_epsg32610.geojson
```

The terminal prints which street labels matched, how far each one lands from its modern centreline, and a summary
line like `fit (affine): RMS 0.5 m over 12 inlier labels`. Open `..._georef_overlay.jpg`: today's streets (red) drawn
back onto the 1912 sheet. If they run down the middle of the drawn streets, it worked. The fit then traces the blocks
a second time with those streets as evidence (`--retrace seeded`, the default) and rewrites `..._blocks_px.geojson` and
the overlay, so look at the overlay again: it should now show 15 blocks and the outlines inside them. Add
`--legend configs/legend/goad_sanborn_default.json` to read each outline's wash against the Goad colour key
(brick, frame, stone); without it the colour is recorded but not interpreted.

**4. Look at the result.**

```bash
python3 scripts/fim_viewer.py runs/hunyuan/demo_vancouver -o runs/hunyuan/demo_vancouver/viewer.html
```

Open `viewer.html` in a browser: blocks over modern centrelines, every word, the sheet outline, a table of residuals.
Or drag `..._blocks_wgs84.geojson` onto <https://geojson.io>, or open the scan in QGIS: copy
`..._georef.jgw` next to the `.tif`, rename it `vancouver_1912_MAP342a_04.tfw`, and QGIS reads the scan georeferenced.

This tile was georectified by the City of Vancouver in 2014, so you can check the answer: the fit from the OCR alone
lands within about 3 m of the City's placement across the drawn area.

**A European plan.** `data/example/README.md` says how to fetch the CC BY 1912 Vienna tile from the City's WMS and its
OSM street layer. It is German, has no lot numbers or block numerals and no colour, so the run differs in two flags:
`--preset text_coords_vienna_1912` for the OCR and `--lots none` for the fit (otherwise its blocks are rejected as
"building outlines" for holding no lot numbers). Expect about 25 labels matched at under 2 m RMS and 50 blocks.

---

## Run it on your own map

You need: a scan (JPG, PNG or TIFF, any size; 300 dpi originals work best) and about an hour per sheet the first time.
Only four things are decided by you; everything else is worked out from the data.

### Step 1. Look at the sheet and pick the content box

```bash
python3 scripts/fim_tile_ocr.py path/to/sheet.jpg --dry-run -o runs/hunyuan/mysheet
```

No GPU used. It writes `..._tile_overlay.jpg` showing the tile grid over the sheet. If the scan has a black margin,
colour bar or ruler, note the pixel box that contains just the map (image viewers show pixel coordinates) and pass it
as `--crop X0,Y0,X1,Y1` from now on. If the sheet fills the image, skip `--crop`.

### Step 2. Choose tile size and views, then read the words

| Sheet | Settings |
|---|---|
| Detailed plan, 50–100 ft to the inch, dense text | `--tile 1024 --max-new-tokens 4096` |
| Less dense, or a lower-resolution scan | `--tile 1536 --max-new-tokens 8192` |
| Text runs at many angles (diagonal streets, key plans) | add `--rotations 0,30,60` (three times the GPU time) |
| Text is mostly along the page axes | leave rotations out |

The prompt tells the model what it is looking at. Pick a preset from `configs/prompts/` or write your own file there
(one sentence, e.g. *"This is a city plan of Lyon, France, from 1900, with French street names. Return the text with
coordinates."*). The phrase **"Return the text with coordinates"** must stay: it is what makes the model emit boxes.
Naming the city and language is a hint, not a requirement: if you do not know where the sheet is, use the preset
`text_coords_generic`, which says only that it is a fire insurance map with street names.

```bash
python3 scripts/fim_tile_ocr.py path/to/sheet.jpg --crop 300,150,7000,7980 --tile 1024 --max-new-tokens 4096 \
    --preset my_prompt -o runs/hunyuan/mysheet
```

Budget about 9 minutes per dense sheet without rotations. Lines saying `HIT CAP` mean the model ran out of room on a
tile and looped; a few are normal, and the looped words (the same word five or more times in a row) are dropped when
the output is parsed. If many tiles hit the cap, use smaller tiles. `--resume` re-uses finished tiles if you have to
restart.

### Step 3. Trace the blocks (detailed plans) or the tinted areas (key plans)

```bash
python3 scripts/fim_blocks.py runs/hunyuan/mysheet          # blocks drawn as closed outlines
python3 scripts/fim_areas.py  runs/hunyuan/mysheet          # key plans that mark sheet coverage with colour washes
```

Run whichever fits the sheet; both can be run. Blocks left open on the sheet (a wharf with no frontage line) can be
closed by hand with `--close-lines X1,Y1,X2,Y2 ...` in scan pixels. Step 5 re-traces the blocks once the sheet is
placed, using the modern centrelines to tell street space from the open interior of a residential block (`fim_blocks.py
--georef`); on a sheet that will not be georeferenced, `--neck-px 16` tries the same carving with the border alone as
street evidence — good on residential sheets, it merges blocks on dense downtown ones, so it is not the default.

Every enclosed outline inside a block also comes out, in `<stem>_buildings_px.geojson`, linked to its block by id and
carrying only what the OCR read inside it (`text_inside`, split into `numerals_inside` and `words_inside`), a `floors`
field left null for a person to fill (or `--floors single-numeral-1-3` on Sanborn plans), and its measured wash colour.
The colour becomes a `material` only through the plan's key given as a config: `--legend configs/legend/<edition>.json`
(the Goad/Sanborn key is included; write one per edition from the sheet's printed legend, colour words are enough).
`--buildings off` skips the file.

### Step 4. Get a modern street layer for the area (once per area)

```bash
python3 scripts/fim_fetch_streets.py --place "Lyon, France" --slug lyon
# or a box  (south,west,north,east in degrees):
python3 scripts/fim_fetch_streets.py --bbox 45.74,4.80,45.78,4.86 --slug lyon_centre
# a sheet that crosses a municipal line: several places (their boxes are unioned), or a box, plus a margin
python3 scripts/fim_fetch_streets.py --place "Lyon, France" --place "Villeurbanne, France" --pad-km 1 --slug lyon_east
```

This pulls named streets from OpenStreetMap into `data/modern/<slug>_streets_epsg<code>.geojson` in the right UTM
zone. The area is always a box, never a city boundary, so a map that runs across two municipalities needs nothing
special beyond a box that covers both. If your city publishes its own centrelines through an ArcGIS service, add
`--arcgis <layer url>` (municipal layers fit a little better than OSM). Any GeoJSON of named lines in a metric
projection works; the name field is detected automatically or given with `--name-field`.

**Don't know where the sheet is?** Let the sheet say. `fim_locate.py` takes the street names the OCR read (outside the
traced blocks), looks each one up in Nominatim (OpenStreetMap's place index, one request per second), and ranks the
places where the most of them lie within a few kilometres of each other, then asks, for the best few places, whether
the remaining names exist there too. It proposes; you choose.

```bash
python3 scripts/fim_locate.py runs/hunyuan/mysheet --list-only     # which names it would look up (no network)
python3 scripts/fim_locate.py runs/hunyuan/mysheet                 # ~1-2 minutes; prints ranked candidates
python3 scripts/fim_locate.py runs/hunyuan/mysheet --country ca    # narrow, if you know that much (--near "<region>" also works)
python3 scripts/fim_fetch_streets.py --from-locate runs/hunyuan/mysheet --candidate 1 --slug mysheet_area
```

A sheet is compact, so candidates are ranked by the names that lie within 1.5 km of one spot (the *core*; `9/25`),
not by how many exist somewhere in a metropolis, where nearly every common street name does. Each line shows that
core count, the count anywhere in the place, the place as Nominatim's addresses describe it (`A / B` when the names
straddle two municipalities), a box around the core padded by 1 km, and the exact fetch command. Nothing is fetched
until you run that command or `--from-locate --candidate N`. It needs a handful of correctly read names: on a tile
whose OCR garbled most street names it still found the right city from five of twenty-five, but with fewer than three
usable names it says so and stops. Names with a type word (`<NAME> ST.`) are the strongest evidence; bare names are
asked for with the type word the sheet itself uses most. For a key plan covering a whole town, raise `--core-km` and
`--pad-km`.

### Step 5. Fit

```bash
python3 scripts/fim_georef.py runs/hunyuan/mysheet --streets data/modern/lyon_streets_epsg32631.geojson
```

Read the printout. **It needs at least six street labels, on streets running in two different directions**, to
place a sheet. A plan without lot numbers or block numerals (a European city plan such as the Vienna Generalstadtplan)
needs `--lots none`, otherwise its blocks are rejected as "building outlines" for holding no lot numbers. Run `fim_blocks.py` first: a word whose centre sits inside a traced block is a building label even if it spells a
street name (a "LIME STORE" is not Store St), and the fit ignores it. Labels farther than 12 m from their street after the fit are reported as outliers and dropped: usually
a street that has been moved or renamed since, which is itself a finding.

Names are compared after historic spelling folds (TH→T, PH→F, hard C→K, Y→I: Rothenthurm matches Rotenturm, Carl
matches Karl; `--spelling exact` turns them off), and a matched street farther than 300 m from every other one is
dropped (`--lonely-m`). `--fuzzy` also accepts near-misses; on a sheet with thousands of words it adds wrong hits along
with the right ones, so try without it first.

If the sheet uses old street names, write them down once in a small file and pass `--alias`:

```json
{ "OLD NAME ON SHEET": ["MODERN NAME ST"], "BASTION": ["BASTION SQ", "BASTION ST"] }
```

See `configs/georef/aliases_victoria_1895.json`. Names are compared after normalising the type word (Street/ST,
Straße/Strasse, Avenue/AVE ...), case, accents and ß, so most spelling differences need no alias. `--fuzzy` also accepts
a label one letter away from a street name, or a fragment of one, when only one street fits (BLANCHARD → Blanshard,
OUGLAS → Douglas). After every fit the printout lists **alias candidates**: unmatched upper-case words that lie on a
modern centreline once the sheet is placed. Those are streets renamed since the plan (KANE → Broughton St on the 1895
Victoria sheets); check them and add them to the alias file, and the next fit uses them.

The sheet's rotation is read from the labels' **text direction**: a street name is printed along its street, so a wide
box runs along the scan's x axis, a tall one along y, and a rotated view gives the angle. Against the modern street's
bearing at the snapped point that fixes the rotation label by label (median over all of them); the labels' positions
then fix only scale and translation. A label's centre can sit anywhere across a 20 m street, and on a 300 m sheet that
scatter could otherwise tilt the whole sheet by a few degrees. `--rotation free` restores the position-only fit, which is
also used when fewer than three labels have a readable direction.

The fit ends with an affine step for paper shrink and scan skew, kept only when it is physically plausible (x/y scales
within 4 %, shear under 2°); otherwise the labels lie on streets of one direction only, and the similarity fit is kept.
The printout says which, and `<stem>_georef.json` records it under `transform`.

### Step 6. View and share

```bash
python3 scripts/fim_viewer.py runs/hunyuan/sheetA runs/hunyuan/sheetB -o runs/viewer.html --title "My book"
```

One tab per sheet. The GeoJSON files (`*_wgs84.geojson`) open in QGIS, geojson.io, ArcGIS or any web map.

## Run a whole book

`fim_batch.py` runs steps 2, 3 and 5 over many sheets and merges the results, so a book is one command:

```bash
python3 scripts/fim_batch.py data/1895/p04.jpg data/1895/p05.jpg data/1895/p06.jpg --crop 320,160,6880,7970 \
    --streets data/modern/victoria_city_streets_epsg26910.geojson --alias configs/georef/aliases_victoria_1895.json \
    --year 1895 --merge runs/hunyuan/victoria_1895_p04-p06
```

Every sheet is OCR'd (finished tiles are reused, so a re-run costs nothing), traced and fitted. A sheet whose fit is
refused for want of street labels gets a second pass **using the sheets around it**: their footprints limit where it can
be (`fim_georef.py --near`), their scale seeds the search, and near-miss spellings are accepted (`--fuzzy`). That
second pass exists only when several sheets are given; a single sheet has no neighbours and is never guessed. If it
still fails and the sheet was read upright only, it is re-OCR'd with 30° and 60° views and fitted once more.

`--merge PREFIX` then writes `PREFIX_blocks_wgs84.geojson`, `PREFIX_buildings_wgs84.geojson`, `PREFIX_page_wgs84.geojson`
and `PREFIX_street_names_wgs84.geojson` over the placed sheets (each feature carries its `sheet`), ready to drop on
geojson.io. `fim_merge.py` does the same for any set of runs. Run it in `tmux` if you will disconnect; a summary table
closes the run, and `--skip-ocr` re-does only the CPU stages (about 20 s per sheet), which is how to re-run after
changing an alias file, a legend or a flag: `--georef-arg=--lots=none`, `--georef-arg=--legend=configs/legend/x.json`
and `--blocks-arg=...` pass flags through to every sheet. The run directories are named by date; to re-use runs from an
earlier day pass `--name "<that date>_tiles_{stem}_t{tile}"`.

## What comes out

All in the run directory, `<stem>` = the scan's file name:

| File | What it is |
|---|---|
| `<stem>_tokens.csv`, `<stem>_tiles.json` | every word read, with its box in scan pixels; the JSON has per-tile stats |
| `<stem>_tile_overlay.jpg` | the words boxed on the sheet: the check for stage 1 |
| `<stem>_blocks_px.geojson`, `_blocks.csv`, `_blocks_overlay.jpg` | traced blocks with number, lot numbers, neighbouring streets, in scan pixels (rewritten by the fit's re-trace) |
| `<stem>_buildings_px.geojson` | every enclosed outline inside a block: `block_id`, `building_id`, the OCR text inside, `floors` (null unless a rule is chosen), measured wash and, with `--legend`, `material` |
| `<stem>_georef.json` | the transform (scan pixels → map metres), per-label residuals, RMS, scale, rotation |
| `<stem>.jgw`, `<stem>_georef.points` | ESRI world file and QGIS control points for the scan |
| `<stem>_blocks_wgs84.geojson`, `_blocks_epsg<code>.geojson` | the blocks on the Earth, with modern street names per side |
| `<stem>_blocks_rejected_*.geojson` | traced shapes judged not to be blocks, each with the reason |
| `<stem>_buildings_wgs84.geojson`, `_buildings_epsg<code>.geojson` | the outlines on the Earth, each re-linked to the block that finally holds it (`orphan` when that block was rejected) |
| `<stem>_tokens_wgs84.geojson`, `<stem>_page_wgs84.geojson` | every word, and the sheet outline, as polygons |
| `<stem>_street_names_wgs84.geojson` | the street-name changes the sheet shows: labels **renamed** since the plan (via `--alias`), **respelled** (`--fuzzy`), **moved** (fit outliers) and **candidates** (unmatched words lying on a modern centreline), each with the modern street's geometry on the sheet, the name on the plan, the plan year (`--year`) and the modern name. A log for linked data; `fim_merge.py` joins them across a book |
| `<stem>_georef_overlay.jpg` | modern streets drawn on the scan: the check for stage 4 |

## When something goes wrong

- **`error: ... no HunYuanVLForConditionalGeneration`**: the OCR is running under a Python without the model. Do the
  Setup step, or set `HUNYUAN_PY` to the right interpreter.
- **`CUDA out of memory`**: use `--tile 1024`. Close other GPU programs.
- **A warning about NVML or driver mismatch** at start-up is harmless.
- **`only N labels matched (< --min-labels 6)`**: too few street names were read or matched. Check `..._tile_overlay.jpg`
  (were the names read?), check the printout's list of unmatched words (renamed streets → alias file, near-misses →
  `--fuzzy`), and make sure the street layer covers the sheet's area. If the sheet is one of a book, run the book with
  `fim_batch.py`: sheets with too few labels are placed with the help of their neighbours (`--near`).
- **`affine rejected`** in the printout: the labels sit on streets of one direction only, so the similarity fit was kept.
  Harmless; more labels in the other direction (aliases, `--fuzzy`) would let the affine step through.
- **Most blocks rejected as "building outline or fragment"**: the plan has no lot numbers (European plans): pass
  `--lots none`. Otherwise read the reasons in `..._blocks_rejected_wgs84.geojson`.
- **The traced polygons are buildings, not blocks** (residential sheets with dashed lot lines): expected before the
  fit; the fit's re-trace fixes it. If the sheet cannot be placed, try `fim_blocks.py --neck-px 16`.
- **A real street was dropped as "farther than 300 m from every other named street"**: raise `--lonely-m`.
- **No network**: supply your own street GeoJSON to `--streets`; the model can be pre-downloaded with
  `huggingface-cli download tencent/HunyuanOCR`.
- **Many tiles come back nearly empty (`not answerable`) or hit the cap**: check `model_revision` in a tile's
  `_metadata.json`. The scripts pin a known-good Hub revision of HunyuanOCR because the current one misreads some tiles
  (tested 2026-09-15); `HUNYUAN_REVISION=main` overrides that if you want to try a newer checkpoint.

## Rights

The Victoria scans this was built on are under a legal protective order (research use at UVic only) and are **not**
in the repository, nor is anything derived from them: since 2026-09-17 no run output at all is tracked (`runs/` is
ignored), so results stay on the machine that made them. Do not add scans, crops, overlays or outputs of the Victoria
sheets. The Vancouver tile is public domain (City of Vancouver Open Data, Open Government Licence). The Vienna test
tile is CC BY 4.0 (Stadt Wien). See `RIGHTS.md` and `data/example/README.md`.

## Where the details are

- `docs/PIPELINE_NOTES.md`: how each stage works and why, per-sheet results, what was tried and rejected.
- `docs/HANDOFF_2026-09-14.md`: what is still manual, known limits, next steps.
- `docs/run_history.md`: every OCR run so far (names and statistics, no content), regenerated by `scripts/fim_run_history.py`.
- `configs/prompts/README.md`: the prompt presets.
- Table extraction from the books' index pages (Chandra, Surya) is a separate toolchain described in the notes; it is
  not part of the georeferencing pipeline.

### Scripts

| Script | Stage |
|---|---|
| `fim_tile_ocr.py` | 1 · tile the sheet, OCR each tile, stitch the words |
| `fim_blocks.py`, `fim_areas.py` | 2 · block polygons and the building footprints inside them from linework · tinted areas on key plans |
| `fim_fetch_streets.py`, `fim_crs.py` | 3 · modern street layer (OSM or ArcGIS) · UTM maths without pyproj |
| `fim_georef.py` | 4 · the fit, and everything in map coordinates |
| `fim_batch.py`, `fim_merge.py` | a whole book: every sheet through stages 1–4 with a neighbour-assisted second pass, then one GeoJSON per kind |
| `fim_viewer.py` | 5 · the HTML viewer |
| `fim_run_history.py` | regenerates `docs/run_history.md` |
| `_hunyuan_compat.py` | loads HunyuanOCR, finds the right Python, parses its output |
| `fim_hunyuan.py`, `fim_overlay.sh`, `fim_tickfilter.py`, `fim_rotation_probe.py` | single-image OCR experiments that led to the tiler (see notes) |
| `fim_surya_*.py`, `fim_gazetteer.py`, `fim_chandra.sh`, `fim_csvify.py` | the table/index toolchain (see notes) |
