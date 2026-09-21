# Sanborn fire insurance map, Tampa, Hillsborough County, Florida — 1884 (Library of Congress)

Downloaded 2026-09-17 with `scripts/fim_fetch_loc.py`; machine-readable provenance (URLs, sizes, SHA-256 of the
Library's masters and of the PNGs, HTTP Last-Modified, pixel sizes) is in `loc_manifest.json` beside this file.

| | |
|---|---|
| Holding institution | Library of Congress, Geography and Map Division, *Sanborn Maps* collection |
| Persistent handle | <http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521884> |
| Resource page | <https://www.loc.gov/resource/g3934tm.g3934tm_g013521884/> (`?sp=1`, `?sp=2` for the two sheets) |
| Digital id | `g3934tm g013521884` (LOC G-schedule class G3934, Tampa; Sanborn map no. 01352, 1884 edition) |
| Sheets | 2, each 6450 × 7650 px RGB. Sheet 1 (`?sp=1`) and sheet 2 (`?sp=2`, the one linked in the request) |
| Files on the LOC storage host | `https://tile.loc.gov/storage-services/service/gmd/gmd393m/g3934m/g3934tm/g3934tm_g013521884/01352_1884-000{1,2}.jp2` (JPEG 2000 masters, 10.4 MB and 10.1 MB, server Last-Modified 19 June 2017) and `.gif` (126 × 150 thumbnails) |
| IIIF image service | `https://tile.loc.gov/image-services/iiif/service:gmd:gmd393m:g3934m:g3934tm:g3934tm_g013521884:01352_1884-0002/info.json` (Image API 2, level 2; tiles, regions and other formats on request) |

## Files here

| File | What |
|---|---|
| `01352_1884-0001.png`, `01352_1884-0002.png` | the Library's JPEG 2000 masters decoded once to lossless PNG (55 MB each), full 6450 × 7650 px, nothing else changed. The masters themselves are not kept (they open in no ordinary viewer); their size, server date and SHA-256 are in `loc_manifest.json` so the download can be verified against the Library's copy |
| `loc_manifest.json` | provenance record written by the fetcher (URLs, master and PNG SHA-256, IIIF pixel sizes, retrieval time) |

Not kept: the `.jp2` masters and the 126 × 150 `.gif` thumbnails (`--keep-jp2` / `--thumbnails` would keep them).
None of these are tracked in git (`.gitignore` excludes all rasters); re-create the directory with

```bash
python3 scripts/fim_fetch_loc.py http://hdl.loc.gov/loc.gmd/g3934tm.g3934tm_g013521884 --out data/Sanborn_Hillsborough-County/1884
```

## Rights and catalogue record

The Library's own catalogue record (title, contributors, date, notes, the "Rights Advisory" / "Rights & Access"
statement shown on the item page) could **not** be fetched from this machine on 2026-09-17: `www.loc.gov` answers
non-browser clients with a Cloudflare challenge (HTTP 403), and the record is not in the LC catalogue's SRU
service. The storage host `tile.loc.gov`, which serves the images, is open.

To complete the record, open the JSON view of the resource in a browser and save it here, then rerun the fetcher
so the metadata is merged into `loc_manifest.json`:

```
https://www.loc.gov/resource/g3934tm.g3934tm_g013521884/?fo=json     ->  save as  data/Sanborn_Hillsborough-County/1884/loc_resource.json
python3 scripts/fim_fetch_loc.py g3934tm.g3934tm_g013521884 --out data/Sanborn_Hillsborough-County/1884 --from-json data/Sanborn_Hillsborough-County/1884/loc_resource.json --metadata-only
```

Until then the rights section is deliberately left blank rather than paraphrased from memory. What can be said
without the record: the Sanborn Map Company published this sheet in 1884, so the map itself is out of
copyright in the United States and Canada; the terms the Library attaches to its digital copies are what the
record will state.
