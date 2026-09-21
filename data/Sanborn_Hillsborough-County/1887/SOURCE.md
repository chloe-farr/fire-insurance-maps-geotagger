# Sanborn fire insurance map, Tampa, Hillsborough County, Florida — 1887 (Library of Congress)

Downloaded 2026-09-17 with `scripts/fim_fetch_loc.py`; machine-readable provenance (URLs, sizes, SHA-256 of the
Library's JPEG 2000 masters and of the PNGs, HTTP Last-Modified, pixel sizes) is in `loc_manifest.json` beside this file.

| | |
|---|---|
| Holding institution | Library of Congress, Geography and Map Division, *Sanborn Maps* collection |
| Persistent handle | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521887> |
| Resource page | <https://www.loc.gov/resource/g3934tm.g3934tm_g013521887/> |
| Digital id | `g3934tm_g013521887` (Sanborn map no. 01352, 1887 edition) |
| Sheets | 3, each 6450 × 7650 px RGB; file numbers 0001–0003 |
| Files on the LOC storage host | `https://tile.loc.gov/storage-services/service/gmd/gmd393m/g3934m/g3934tm/g3934tm_g013521887/01352_1887-NNNN.jp2` (JPEG 2000 masters, not kept here) |

URLs as given by Chloe (kept verbatim in the manifest's `requested_url`):
  - <https://www.loc.gov/resource/g3934tm.g3934tm_g013521887/?st=gallery>
  - <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521887>

## Files here

`01352_1887-0001.png` … `01352_1887-0003.png`: the Library's JPEG 2000 masters decoded once to lossless PNG, full resolution, nothing else changed.
The masters and the GIF thumbnails are not kept; each master's size, server date and SHA-256 are in `loc_manifest.json`.
Not tracked in git (`.gitignore` excludes all rasters); re-create the directory with

```bash
python3 scripts/fim_fetch_loc.py http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521887 --out data/Sanborn_Hillsborough-County/1887
```

## Rights and catalogue record

Not yet fetched: `www.loc.gov` refuses non-browser clients from this machine (Cloudflare challenge). To complete it,
save <https://www.loc.gov/resource/g3934tm.g3934tm_g013521887/?fo=json> from a browser as `loc_resource.json` in this directory and run the fetcher again
with `--from-json loc_resource.json --metadata-only`; the title, contributors, date, notes and the Library's rights
advisory are then merged into `loc_manifest.json`. Same procedure as in `../1884/SOURCE.md`.
