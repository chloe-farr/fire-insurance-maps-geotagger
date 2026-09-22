# Tampa, Florida, 1889 — Sanborn map no. 01352, sheet 3, with everything the pipeline wrote for it

One complete run, copied out of `runs/` so the output can be looked at without a GPU. Nothing here is hand-edited
except that the machine's home directory was removed from the paths recorded in the JSON. Six traced shapes the fit
judged not to be blocks (`*_blocks_rejected_*`), the 41 per-tile files (`tiles/`) and the run log are not included.

## The sheet

| | |
|---|---|
| Holding institution | Library of Congress, Geography and Map Division, *Sanborn Maps* collection |
| Persistent handle | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521889> |
| Resource page | <https://www.loc.gov/resource/g3934tm.g3934tm_g013521889/?sp=3> (sheet 3 of 7) |
| Master file | `https://tile.loc.gov/storage-services/service/gmd/gmd393m/g3934m/g3934tm/g3934tm_g013521889/01352_1889-0003.jp2` (JPEG 2000, 10.4 MB, SHA-256 `3d2a4956be0ba0d2…`; 6450 × 7650 px) |
| The plan | Sanborn Map & Publishing Co., *Tampa, Hillsborough Co., Florida*, April 1889, 50 feet to the inch; downtown between the Hillsborough River and Franklin Street, Madison to Whiting Streets |
| Rights | Published in 1889, so out of copyright. The Library's catalogue record and rights advisory were not fetched from this machine ; read them on the resource page before reusing the image beyond this repository |
| Fetched | 2026-09-17 with `scripts/fim_fetch_loc.py`, which writes a `loc_manifest.json` (source URLs, SHA-256, sizes) beside the sheets it downloads |

`01352_1889-0003.jpg` here is the Library's master decoded and re-encoded as JPEG (quality 90, 6.6 MB) so that it fits
the repository; the run itself read the lossless PNG (56 MB) that `fim_fetch_loc.py` writes. Pixel coordinates are
identical; a re-run on the JPEG may differ by a word or two.

## Files

| File | What |
|---|---|
| `01352_1889-0003.jpg` | the scan (input) |
| `01352_1889-0003.jgw` | ESRI world file for the scan (written by the fit; QGIS reads the JPEG georeferenced with it beside it) |
| `01352_1889-0003_tokens.csv`, `_tiles.json` | 587 words with their boxes in scan pixels; the JSON also holds the per-tile statistics and the prompt |
| `01352_1889-0003_tile_overlay.jpg` | every word boxed on the sheet |
| `01352_1889-0003_blocks_px.geojson`, `_blocks.csv`, `_blocks_overlay.jpg` | 12 city blocks in scan pixels with their lot numbers and neighbouring streets, and every enclosed outline inside them in magenta |
| `01352_1889-0003_buildings_px.geojson` | 93 building outlines: block id, the text the OCR read inside each, `floors` (null: no rule was chosen), measured wash colour (no `--legend` was passed, so no `material`) |
| `01352_1889-0003_areas_px.geojson`, `_areas.csv`, `_areas_overlay.jpg` | 27 colour-washed areas in three tints (yellow, blue, pink), from `fim_areas.py` |
| `01352_1889-0003_georef.json`, `_georef.points` | the transform scan pixels → EPSG:32617, per-label residuals, alias candidates, the parameters; QGIS control points |
| `01352_1889-0003_georef_overlay.jpg` | today's streets drawn back onto the sheet |
| `*_wgs84.geojson`, `*_epsg32617.geojson` | blocks, buildings, areas, words and the sheet outline (`_page_`) on the Earth, in WGS 84 and in UTM zone 17N |
| `01352_1889-0003_street_names_wgs84.geojson` | 17 street-name records: labels matched through the alias file (renamed streets), labels inside blocks that spell a street name (building labels), and unmatched words that lie on a modern centreline (candidates) |

## The run

| Stage | Settings | Result |
|---|---|---|
| OCR (`fim_tile_ocr.py`) | HunyuanOCR, preset `text_coords_tampa_1889`, work size 3453 × 4096, 768 px tiles with 192 px overlap (7 × 6), upright only, 4096-token cap | 41 of 42 tiles read (one blank), 905 boxes parsed → 587 kept (200 duplicates across overlaps, 52 fragments, 66 conflicts dropped; one tile hit the cap and its repeated tail was dropped); 230 s of model time on an RTX 6000 Ada |
| Areas (`fim_areas.py`) | defaults | 27 tinted areas, tints yellow / blue / pink |
| Street layer | OpenStreetMap for "Tampa, Florida" (`tampa_streets_epsg32617.geojson` here, 34 495 named ways) | |
| Fit (`fim_georef.py`) | `--alias configs/georef/aliases_tampa.json --year 1889 --scales 0.045,0.05,0.065,0.1`, otherwise defaults (`--lots numbered`, `--rotation labels`, `--retrace seeded`) | 6 labels placed the sheet: MADISON, ASHLEY, WHITING by name, TAMPA (twice) and WASHINGTON through the alias file. Similarity transform; the affine step was rejected because the labels lie on streets of one direction only. Rotation 20.7°, 0.0515 m/px (50 ft/in at about 296 dpi). Median residual 4.1 m; RMS 63.7 m because one of the two TAMPA labels lands 156 m from the street it was snapped to and is still counted as an inlier. 12 blocks kept, 6 rejected; 93 building outlines re-linked; 7 alias candidates, among them LAFAYETTE → East Kennedy Blvd (renamed 1964) |

Read the fit as a rough placement, not a survey: six labels on a sheet this size, half of them through aliases, is
the minimum the script accepts. More labels in the other direction (the alias candidates, once checked) would let the
affine step through and pull the RMS down.

## Reproduce it

```bash
python3 scripts/fim_fetch_loc.py http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521889 --out data/Sanborn_Hillsborough-County/1889
python3 scripts/fim_tile_ocr.py data/Sanborn_Hillsborough-County/1889/01352_1889-0003.png \
    --tile 768 --max-new-tokens 4096 --preset text_coords_tampa_1889 -o runs/hunyuan/Sanborn_Hillsborough-County/1889/0003
python3 scripts/fim_blocks.py runs/hunyuan/Sanborn_Hillsborough-County/1889/0003
python3 scripts/fim_areas.py  runs/hunyuan/Sanborn_Hillsborough-County/1889/0003
python3 scripts/fim_fetch_streets.py --place "Tampa, Florida" --slug tampa      # once; the layer is included
python3 scripts/fim_georef.py runs/hunyuan/Sanborn_Hillsborough-County/1889/0003 \
    --streets data/example/tampa_1889_sheet3/tampa_streets_epsg32617.geojson --alias configs/georef/aliases_tampa.json \
    --year 1889 --scales 0.045,0.05,0.065,0.1
```

Or start from the JPEG in this directory: `python3 scripts/fim_tile_ocr.py data/example/tampa_1889_sheet3/01352_1889-0003.jpg ...`.
