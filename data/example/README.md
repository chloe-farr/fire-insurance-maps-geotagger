# data/example — a public-domain Goad sheet for demos and tests

The Victoria scans in `../1885` and `../1895` are RBCM research-only images and are never committed
(see `../../RIGHTS.md`). This directory holds the one map that **is** committed and may be shown freely.

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

These two rasters are the only ones whitelisted in `.gitignore`. The City serves the zip from behind Cloudflare,
which refuses non-browser clients, so re-downloading means a browser; the inner file is named `MAP342a.04.tif`.

## Vienna 1912, Generalstadtplan, Innere Stadt (a European test case, added 2026-09-15)

| | |
|---|---|
| Source | Stadt Wien open data, WMS layer `GENLPLAN1912OGD` ("Generalstadtplan 1912") at <https://data.wien.gv.at/daten/wms>, georeferenced by the City (Wien Kulturgut) |
| Rights | CC BY 4.0. Required attribution: *Datenquelle: Stadt Wien – data.wien.gv.at* |
| The plan | Generalstadtplan of Vienna, 1912 edition (Josef Lenobel, state as of 30 April 1912), lithograph at 1:3,500 reduced from the 1:2,880 sheets; street and square names, house numbers, parcel and building-line linework, construction dates. Black and white, Antiqua lettering, irregular medieval street network |
| The original | *General-Stadt-Plan der Gemeinde Wien. Atlas zum Häuser-Kataster der k. k. Reichshaupt- und Residenzstadt Wien*, 2nd ed., Stadtbauamt / Josef Lenobel, 1912. Sheets held by the Wiener Stadt- und Landesarchiv, Kartographische Sammlung, Sammelbestand P2.1: 309; the archive's scan is viewable in Wien Kulturgut: <https://www.wien.gv.at/kulturportal/public/grafik.aspx?bookmark=LvBMRUz1i0V-aLrRGOXowRhwpYlDf> (1904 edition: `...pYpBm`). Background: <https://www.geschichtewiki.wien.gv.at/Generalstadtplan> |
| Files | `vienna_1912_generalstadtplan_innere_stadt.png` — 4800 × 4800 px, 0.25 m/px (the service's native resolution; requests above 2400 px are refused, so this is 2 × 2 GetMap tiles stitched), EPSG:32633 (WGS 84 / UTM 33N), bbox 601350,5339800 – 602550,5341000; `.pgw` world file. Centre 48.2086 N, 16.3723 E (Stephansplatz) |
| Ground truth | the City's georeferencing, i.e. the world file, as with the Vancouver tile |
| Modern layer | `../modern/vienna_innere_stadt_streets_epsg32633.geojson` (OpenStreetMap via `fim_fetch_streets.py --bbox 48.195,16.355,48.222,16.395 --slug vienna_innere_stadt`) |

Known matching gaps before `fim_georef.py` can fit it: the plan writes "Singer-Strasse" / "Rothenthurm-Strasse" where OSM has
"Singerstraße" / "Rotenturmstraße" (type words fused to the name, ß, pre-1901 spelling); no feet-per-inch scale statement.
The raster is not whitelisted in `.gitignore` yet (re-create it with the WMS request above).
