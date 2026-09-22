# Vancouver, British Columbia, 1912 — Goad's Atlas, tile MAP342a_04, with everything the pipeline wrote for it

One complete run, copied out of `runs/` so the output can be looked at without a GPU. Nothing here is hand-edited
except that the machine's home directory was removed from the paths recorded in the JSON. The 25 per-tile files
(`tiles/`), the run log and the built viewer are not included.

This tile is the pipeline's only self-checking example: the City of Vancouver georectified it in 2014, so the
GeoTIFF carries its own ground truth and the fit can be judged against it rather than by eye.

## The sheet

| | |
|---|---|
| Source | City of Vancouver Open Data, *Goad's Fire Insurance Map 1912 (georectified)* — <https://opendata.vancouver.ca/explore/dataset/goads-fire-insurance-map-1912-georectified/> |
| Rights | The dataset page states "This map is in the public domain." Distributed under the Open Government Licence – Vancouver (<https://opendata.vancouver.ca/pages/licence/>). Attribution: *Contains information licensed under the Open Government Licence – Vancouver; original plan by Chas. E. Goad Co., 1912.* |
| The plan | Chas. E. Goad Co., data current to 3 July 1912. Downtown and Gastown; tile centre 49.2846 N, 123.1079 W |
| Master file | `https://webtransfer.vancouver.ca/opendata/1912tiff/MAP342a_04.zip` (GeoTIFF, UTM zone 10 N, NAD83 (CSRS)); an ECW twin exists. The City serves the zip from behind Cloudflare, which refuses non-browser clients, so re-downloading means a browser; the file inside is named `MAP342a.04.tif` |
| Georectified | by the City, December 2014 — this is the ground truth the fit is measured against |
| All 100 tiles | `vancouver_1912_MAP342a_04_tiles.csv` — id, centre, TIFF and ECW URLs, from the dataset's records API |

The sheet sits rotated inside a north-up frame with a white margin, as the City georectified it; the fit has to find
that rotation for itself.

## Files

| File | What |
|---|---|
| `..._MAP342a_04.tif`, `.tfw` | the City's GeoTIFF as downloaded (13 MB, 5991 × 5719 px RGB, LZW, 0.174 m/px) and its world file |
| `..._tiles.csv` | index of all 100 tiles of the atlas |
| `..._tokens.csv`, `_tiles.json` | 2 910 words with their boxes in scan pixels; the JSON also holds the per-tile statistics and the prompt |
| `..._tile_overlay.jpg` | every word boxed on the sheet |
| `..._blocks_px.geojson`, `_blocks.csv`, `_blocks_overlay.jpg` | 15 traced city blocks in scan pixels, with their numbers, lot numbers and neighbouring street labels |
| `..._blocks_rejected_*.geojson` | 8 traced shapes the fit judged not to be blocks, kept so the decision can be inspected |
| `..._outlines_px.geojson` | 286 enclosed outlines inside those blocks, each linked to its block, carrying only the OCR tokens inside it |
| `..._locate.json` | what `fim_locate.py` made of the sheet from its street names alone, before any street layer was fetched |
| `..._georef.json`, `_georef.points` | the affine fit both ways, per-label residuals, RMS; the `.points` file opens in the QGIS Georeferencer |
| `..._georef_overlay.jpg` | today's streets drawn back onto the 1912 sheet — the picture that says whether it worked |
| `..._MAP342a_04.jgw` | ESRI world file for the scan, written by the fit |
| `..._blocks_epsg32610/_wgs84.geojson`, `_outlines_*`, `_page_*`, `_street_names_wgs84`, `_tokens_wgs84` | the same features on the Earth, in the layer's CRS and in WGS 84 |
| `vancouver_streets_epsg32610.geojson` | the modern street centrelines the sheet was fitted to (OpenStreetMap, © OpenStreetMap contributors, **ODbL**) |

## The run

```bash
python3 scripts/fim_tile_ocr.py data/example/vancouver_1912_MAP342a_04/vancouver_1912_MAP342a_04.tif \
    --work-max-edge 0 --tile 1536 --overlap 192 --rotations 0,30,60 --max-new-tokens 8192 \
    --preset text_coords_vancouver_1912 -o runs/hunyuan/demo_vancouver

python3 scripts/fim_blocks.py runs/hunyuan/demo_vancouver

python3 scripts/fim_georef.py runs/hunyuan/demo_vancouver \
    --streets data/example/vancouver_1912_MAP342a_04/vancouver_streets_epsg32610.geojson
```

OCR: `tencent/HunyuanOCR`, a 5 × 5 grid of 1536 px tiles with 192 px overlap, read upright and at 30° and 60°.

## What came out

| | |
|---|---|
| Words read | 2 910 |
| Street labels matched to the modern layer | 12 used, 1 rejected as an outlier |
| Labels set aside as building labels | 44 (inside a traced block, so not street names) |
| Fit | affine, **RMS 0.49 m**, 0.173 m per scan pixel |
| Blocks | 15 traced, 8 shapes rejected |
| Outlines | 286 enclosed outlines |
| CRS | EPSG:32610 (WGS 84 / UTM 10 N) |

0.49 m RMS is about three scan pixels. Because the City's own georectification is in the GeoTIFF, that number is a
measurement against an independent reference rather than a self-assessment — which is why this tile, and not one of
the larger books, is the example to trust.
