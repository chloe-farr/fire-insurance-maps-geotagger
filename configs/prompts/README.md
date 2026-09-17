# Prompt presets

One prompt per file; `scripts/fim_hunyuan.py --preset NAME` and `scripts/fim_chandra.sh --preset NAME`
read `NAME.txt` from this directory. These are the exact prompts used in the runs under `runs/`
(recovered from `*_metadata.json` and `chandra_run.log`), so re-runs are comparable.

| Preset | Used with | Purpose |
|---|---|---|
| `text_coords` | HunyuanOCR | words + bounding boxes, `word(x1,y1),(x2,y2)` in 0–1000 normalised coords (p06b cropped run; the p06b rot090/105/112 runs used the same text with "texts") |
| `text_coords_vancouver_1912` | HunyuanOCR | same request for the public-domain Vancouver 1912 Goad tile (`data/example/`) |
| `text_coords_vienna_1912` | HunyuanOCR | same request for the Vienna 1912 Generalstadtplan test tile, German street names |
| `text_coords_generic` | HunyuanOCR | the same request with no city, year or language named — for a sheet whose location is unknown (then `fim_locate.py`) |
| `text_coords_rotated` | HunyuanOCR | the prompt behind most of `runs/hunyuan/single_page` (19 runs: p02, p06, p25 sweeps) — tells the model the page has been rotated |
| `text_coords_rotated_verbose` | HunyuanOCR | longer variant used for `runs/hunyuan/p06b_rot_coords_run` (4 runs) |
| `words_block_numbers` | HunyuanOCR | asks explicitly for the bold block numbers (uncropped p06b_rot000 run — returned only `6`) |
| `hunyuan_default_zh` | HunyuanOCR | HunyuanOCR's stock Chinese "detect text + coordinates" prompt; used once (p25_rot000) |
| `furniture_list` | HunyuanOCR | list cartographic furniture (north arrow, scale, tape) |
| `furniture_coords` | Chandra | coordinates of north arrow / colour patch / scale / tape |
| `map_description` | Chandra | prose description + feature list of a sheet |
| `index_1885_streets` | Chandra | 1885 index column → 3-col markdown table (street, relative_position, sheet) |
| `index_1885_dittos` | Chandra | 1885 full index page → table, expanding `"` ditto marks |
| `key_1885_description` | Chandra | 1885 symbol key → prose |

To OCR a new city, copy one of the `text_coords_*` files, change the city, year and language, keep the sentence
"Return the text with coordinates." unchanged, and pass the new file name to `--preset`. The city and language are a
hint to the model, not a requirement: `text_coords_generic` names none and works when the location is unknown.
