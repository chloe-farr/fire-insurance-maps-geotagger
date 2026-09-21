# data/ — raw scans (symlinks into ~/projects/datasets)

Nothing here is a copy. Every entry is a symlink into `~/projects/datasets/fire_insurance_maps/`,
which is the single home for the Victoria fire insurance plan scans (~230 GB).

| Link | Target | Contents |
|---|---|---|
| `1885/` | `fire_insurance_maps/1885/` | 6 JPG crops of the 1885 book: `Index.jpg` (full index page), `Index_col1..col4.jpg` (one index column each), `Key.jpg` (symbol key) |
| `1895/` | `fire_insurance_maps/1895/` | 1895 book. Originals: `p01..p31.jpg` (+ `p06b`, `p07b`), `front_cover`, `back_cover`, `inside-front-cover`, `inside-back-cover`; crops of the inside front cover (`-index`, `-index-to-streets[-colN]`, `-block-numbers[_colN]`, `-specials[...]`, `_top`); and 360° rotation sweeps `fireinsurance_victoria_1895_p{02..10}_rot000..359.png` (3 240 PNGs, ~209 GB) |
| `1895_p06b_rotations/` | `fire_insurance_maps/fireinsurance_victoria_1895_p06b_rotations/rotated/` | sheet 6b at every degree (361 PNGs, incl. `rot000_cropped`) |
| `1895_p25_rotations/` | `fire_insurance_maps/fireinsurance_victoria_1895_p25_rotations/rotated/` | sheet 25 at 0°, 87°, 356°, 358° |

Source: Victoria, British Columbia [Fire Insurance Plans], May 1891, revised 1895 (Chas. E. Goad). 37 pages, 34 usable.
UVic Vault: https://vault.library.uvic.ca/concern/generic_works/2efc7335-9bb0-4b4c-b0a0-d7535104571d

## Provenance notes

- `~/projects/datasets/1895` was moved to `fire_insurance_maps/1895` on 2026-09-10 when this project was
  created. A symlink `datasets/1895 -> fire_insurance_maps/1895` was left behind so old hard-coded paths keep resolving.
- `~/projects/datasets/dynamicocr_training_data/victoria-fire-insurance-plans/1895/` holds a **byte-identical
  duplicate** of the 37 original page JPGs (248 MB). It was left in place because `~/projects/DynamicOCR/config.yaml`
  points at `dynamicocr_training_data` as its training set. It is not linked here.
- `~/projects/datasets/1884/1884_TPL_CityofVictoria.jpg` is an 1884 city plan (not a fire insurance plan) that was
  OCR'd alongside these in the same HunyuanOCR sessions. Not linked here.
- Rotation sweeps were generated to test OCR sensitivity to page orientation; the originals are rotated by N degrees
  on a white canvas, so rotated PNGs are larger than the source JPGs.

## `Sanborn_Hillsborough-County/` — Library of Congress Sanborn sheets (real files, not symlinks; not tracked)

Public-domain Sanborn fire insurance maps from the Library of Congress, fetched with `scripts/fim_fetch_loc.py`, which
also writes a `loc_manifest.json` (source URLs, SHA-256, sizes, catalogue record when available) into each directory.
The rasters are ignored by git like every other image here; each directory has a `SOURCE.md` with the handle and the
one command that re-creates it (`SOURCE.md` and `loc_manifest.json` are tracked, the PNGs are not). All are Tampa, Hillsborough County, Florida, Sanborn map no. 01352, every sheet
6450 × 7650 px, fetched 2026-09-17 (166 sheets, 8.2 GB of PNG). Catalogue records and rights statements still to be
added from a browser-saved `?fo=json` (see any `SOURCE.md`). **Layout: one folder per county, one subdirectory per edition year**
(`Sanborn_<County>/<year>/`), the same file set in each: one PNG per sheet, `SOURCE.md`, `loc_manifest.json`. No JP2
masters and no GIF thumbnails are kept (the fetcher decodes the master and deletes it; `--keep-jp2` / `--thumbnails` opt in).

| Directory | Item | Contents |
|---|---|---|
| `Sanborn_Hillsborough-County/1884/` | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521884> | 2 sheets, `01352_1884-0001.png` … `-0002.png` |
| `Sanborn_Hillsborough-County/1887/` | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521887> | 3 sheets, `01352_1887-0001.png` … `-0003.png` |
| `Sanborn_Hillsborough-County/1889/` | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521889> | 7 sheets, `01352_1889-0001.png` … `-0007.png` |
| `Sanborn_Hillsborough-County/1892/` | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521892> | 10 sheets, `01352_1892-0001.png` … `-0010.png` |
| `Sanborn_Hillsborough-County/1895/` | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521895> | 17 sheets, `01352_1895-0005.png` … `-0021.png` |
| `Sanborn_Hillsborough-County/1899/` | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521899> | 33 sheets, `01352_1899-0001.png` … `-0033.png` |
| `Sanborn_Hillsborough-County/1915/` | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521915> | 94 sheets, `01352_1915-0001.png` … `-0094.png` |

`www.loc.gov` (item pages, `?fo=json` API) refuses non-browser clients from this host with a Cloudflare challenge; the
fetcher falls back to the open storage host `tile.loc.gov` and takes the catalogue record from a browser-saved
`?fo=json` via `--from-json`.

## `gcp/` and `modern/` — real files, not symlinks (small; tracked in git)

### `gcp/` — QGIS Georeferencer `.points` files

| File | Made against | Notes |
|---|---|---|
| `1884_TPL_CityofVictoria_GEO_FINAL.tif.points` | `1884_TPL_CityofVictoria_GEO_FINAL.tif` (**not on this machine**; the raw scan `datasets/1884/1884_TPL_CityofVictoria.jpg`, 7026×6409, is) | Received 2026-09-14. CRS NAD83 / UTM 10N (EPSG:26910). 4 GCPs, 3 enabled. **`sourceX/sourceY` are UTM metres, not pixels** — the file was made on an already-georeferenced TIFF, so it refines that TIFF's placement; it cannot by itself map the raw JPG's pixels to the world, and GCPs are image-specific anyway (they cannot be reused on another sheet or year). Kept for reference; not used by any script. |

`scripts/fim_georef.py` writes its own `.points` per sheet into the run dir (`runs/…/<stem>_georef.points`, pixel ↔ snapped centreline) — that is the file to open in QGIS if you want to inspect or hand-refine the automatic fit.

### `modern/` — present-day named-street layers (metric CRS; `crs` member in each file)

Made by `scripts/fim_fetch_streets.py`, consumed by `scripts/fim_georef.py --streets`. Any city: OpenStreetMap for
anywhere, or a municipal ArcGIS layer where one exists. File names carry the EPSG code.

| File | Source | Notes |
|---|---|---|
| `victoria_city_streets_epsg26910.geojson` | City of Victoria Open Data, *Streets* (`maps.victoria.ca/server/rest/services/OpenData/OpenData_Transportation/MapServer/25`) via `fim_fetch_streets.py --arcgis`, fetched 2026-09-14 for the whole city (bbox 48.395,-123.42,48.46,-123.29; 2539 segments, 625 names, paged past the 2000-feature limit). Fields `StreetSegmentID, StreetName, STNAME, STTYPE, …`. NAD83 / UTM 10N. | best reference for the 1895 book: RMS 2.1 m on 6b, 5.0 m on p25. (The service also has an *Intersections* layer 15; not needed — `fim_georef.py` derives intersections from the centrelines and gets the same fit.) |
| `capital_region_crd_streets_epsg26910.geojson` | CRD (Capital Regional District) *Roads* MapServer layer 14 "All Road Types" (`mapservices.crd.bc.ca/arcgis/rest/services/Roads/MapServer/14`) via `fim_fetch_streets.py --arcgis`, bbox 48.40,-123.46,48.475,-123.30, fetched 2026-09-14: 8786 segments, name field `STRUCTURED_NAME_1` ("Esquimalt Rd", "Burnside Rd E"). NAD83 / UTM 10N. | reference for sheets reaching outside the city (p02, p03: Esquimalt, Vic West, Saanich) |
| `capital_region_osm_streets_epsg32610.geojson` | OpenStreetMap for the same bbox (5368 segments, 1652 names). WGS 84 / UTM 10N. | alternative; p02 fits it at 9.7 m vs 12.8 m on CRD (fewer labels kept) |
| `tampa_streets_epsg32617.geojson` | OpenStreetMap via Overpass (`fim_fetch_streets.py --place "Tampa, Florida" --slug tampa`), fetched 2026-09-17: 34 495 named ways, 12 823 names, bbox 27.81,-82.65,28.17,-82.25 (1550 km², the whole city). WGS 84 / UTM 17N. © OpenStreetMap contributors, ODbL. | reference for the Library of Congress Sanborn sheets of Tampa; a layer this wide needs the alias file to pin bare names (`TAMPA`, `FRANKLIN`) to the downtown streets, see `configs/georef/aliases_tampa.json` |
| `victoria_osm_streets_epsg32610.geojson` | OpenStreetMap via Overpass (`fim_fetch_streets.py --bbox 48.405,-123.40,48.45,-123.32 --slug victoria_osm`), fetched 2026-09-14: 2265 named highway ways, 635 names; footways/paths/steps/cycleways excluded. WGS 84 / UTM 10N. © OpenStreetMap contributors, ODbL. | RMS 3.2 m on 6b — alleys and the pedestrian square are approximate in OSM |
| `BLOCK_VERTICES.csv` | Received 2026-09-14 (assessment-block polygons as vertex lists: `OBJECTID, BlockRoll, …, x/lng, y/lat` in UTM 10N; 814 polygons, 733 roll numbers). | unused. **`BlockRoll` is not the Goad block number**: modern 024/023/016/008 lie 100–400 m from the 1895 blocks 24/23/16/8 and are ~4× their area; downtown blocks carry roll numbers in the 030s–070s. Could serve as a modern *shape* layer to match 1895 block polygons against, now that they are georeferenced. |
| `ROADS_AZIMUTH.csv` | Received 2026-09-14 (CRD road segments: name, municipality, address ranges, length, azimuth; 19 747 rows). | unused — **no coordinates** in the export. |

Re-fetch / other cities:

```bash
python3 scripts/fim_fetch_streets.py --place "Victoria, British Columbia" --slug victoria_osm      # OSM, bbox from Nominatim
python3 scripts/fim_fetch_streets.py --bbox S,W,N,E --slug <city>                                  # OSM, explicit box (degrees)
python3 scripts/fim_fetch_streets.py --bbox 48.40,-123.40,48.45,-123.32 --slug victoria_city --epsg 26910 \
    --arcgis https://maps.victoria.ca/server/rest/services/OpenData/OpenData_Transportation/MapServer/25   # municipal layer
```

Overpass mirrors are tried in turn (`maps.mail.ru` answered from this host; `overpass-api.de` returned 504 and two
others timed out on 2026-09-14). Nominatim and Overpass are public services: keep boxes to a city, not a province.
