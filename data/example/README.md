# data/example — public-domain sheets for demos and tests

The Victoria scans in `../1885` and `../1895` are RBCM research-only images and are never committed
(see *Licence, citation and rights* in the top-level `README.md`). This directory holds the maps that **are**
committed and may be shown freely: a Vancouver 1912 Goad tile (input only; the README's walk-through runs it) and a
Tampa 1889 Sanborn sheet with the complete output of one run (`tampa_1889_sheet3/`, its own `README.md`).

## Vancouver 1912, Goad's Atlas, tile MAP342a_04 (downtown / Gastown)

| | |
|---|---|
| Source | City of Vancouver Open Data, dataset *Goad's Fire Insurance Map 1912 (georectified)* — <https://opendata.vancouver.ca/explore/dataset/goads-fire-insurance-map-1912-georectified/> |
| Rights | The dataset page states "This map is in the public domain." Distributed under the Open Government Licence – Vancouver (<https://opendata.vancouver.ca/pages/licence/>). Attribution: *Contains information licensed under the Open Government Licence – Vancouver; original plan by Chas. E. Goad Co., 1912.* |
| Publisher of the plan | Chas. E. Goad Co., data current to 3 July 1912 — same firm, drafting conventions and symbol key as the Victoria 1885/1895 books |
| Files | `https://webtransfer.vancouver.ca/opendata/1912tiff/MAP342a_04.zip` (GeoTIFF, UTM zone 10 N, NAD83 (CSRS)); an ECW twin exists. Georectified by the City in December 2014, so the tile carries its own ground truth for judging `fim_georef.py`. |
| Tile centre | 49.2846 N, 123.1079 W |
| All 100 tiles | `vancouver_1912_tiles.csv` — id, centre, TIFF and ECW URLs, pulled from the dataset's records API |

### Files here

| File | What |
|---|---|
| `vancouver_1912_MAP342a_04.tif` | the City's GeoTIFF as downloaded (13 MB, 5991 × 5719 px RGB, LZW, 0.1737 m/px, UTM zone 10 N NAD83 (CSRS)); the sheet sits rotated inside a north-up frame with a white margin, as the City georectified it |
| `vancouver_1912_MAP342a_04.tfw` | its world file (same georeferencing as the GeoTIFF tags) |
| `vancouver_1912_tiles.csv` | index of all 100 tiles |

These two rasters, and the JPEGs in `tampa_1889_sheet3/`, are the only ones whitelisted in `.gitignore`. The City
serves the zip from behind Cloudflare, which refuses non-browser clients, so re-downloading means a browser; the inner
file is named `MAP342a.04.tif`.

## Tampa 1889, Sanborn map no. 01352, sheet 3 (Library of Congress) — with the pipeline's output

See `tampa_1889_sheet3/README.md`: source handle, rights, every file, the parameters and results of the run, and the
commands that reproduce it.
