# MANIFEST — where everything in this project came from

Generated 2026-09-10 when the project was assembled. Run artifacts were **moved** (copied with `cp -p`, verified byte-identical with `cmp`, originals deleted). Each old location has a `FIREINSURANCE_MOVED.md` pointing here: `~/projects/hunyuan/input/`, `~/projects/hunyuan/output/`, `~/projects/chandra/output/`, plus `~/projects/recast/configs/README_fireinsurance.md` and a section in `~/projects/hunyuan/README.md`.

## Dataset consolidation (moves, not copies)

| Action | From | To |
|---|---|---|
| mv | `~/projects/datasets/1895/` (3 292 files, 209 GB) | `~/projects/datasets/fire_insurance_maps/1895/` |
| ln -s | `~/projects/datasets/1895` | `-> fire_insurance_maps/1895` (compat symlink for old hard-coded paths) |
| (left) | `~/projects/datasets/dynamicocr_training_data/victoria-fire-insurance-plans/1895/` | byte-identical duplicate of the 37 page JPGs; DynamicOCR's configured dataset |

## Moved run artifacts (source paths no longer exist)

| Destination (this repo) | Former location | Bytes |
|---|---|---|
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot000_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot000_content.txt` | 24037 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot000_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot000_metadata.json` | 499 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot000_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot000_resized.png` | 1516279 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot019_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot019_content.txt` | 4436 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot019_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot019_metadata.json` | 497 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot019_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot019_resized.png` | 1096667 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot050_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot050_content.txt` | 1436 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot050_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot050_metadata.json` | 498 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot050_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot050_resized.png` | 968482 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot085_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot085_content.txt` | 1760 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot085_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot085_metadata.json` | 497 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot085_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot085_resized.png` | 1370167 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot096_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot096_content.txt` | 925 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot096_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot096_metadata.json` | 495 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot096_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot096_resized.png` | 1333466 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot114_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot114_content.txt` | 21833 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot114_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot114_metadata.json` | 500 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot114_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot114_resized.png` | 1045400 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot126_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot126_content.txt` | 536 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot126_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot126_metadata.json` | 496 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot126_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot126_resized.png` | 975313 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot127_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot127_content.txt` | 2003 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot127_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot127_metadata.json` | 498 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p02_rot127_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p02_rot127_resized.png` | 972015 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot000_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot000_content.txt` | 1 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot000_cropped_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot000_cropped_content.txt` | 24522 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot000_cropped_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot000_cropped_metadata.json` | 373 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot000_cropped_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot000_cropped_resized.png` | 2253724 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | 394 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot000_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot000_resized.png` | 2646393 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot090_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot090_content.txt` | 23512 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot090_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot090_metadata.json` | 404 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot090_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot090_resized.png` | 4527466 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot105_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot105_content.txt` | 24141 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot105_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot105_metadata.json` | 404 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot105_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot105_resized.png` | 3581103 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot112_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot112_content.txt` | 4065 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot112_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot112_metadata.json` | 401 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot112_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot112_resized.png` | 919844 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot180_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot180_content.txt` | 406 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot180_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot180_metadata.json` | 488 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06b_rot180_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06b_rot180_resized.png` | 1295325 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot090_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot090_content.txt` | 2098 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot090_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot090_metadata.json` | 496 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot090_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot090_resized.png` | 1543629 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot105_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot105_content.txt` | 1807 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot105_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot105_metadata.json` | 497 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot105_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot105_resized.png` | 1168421 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot112_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot112_content.txt` | 23926 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot112_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot112_metadata.json` | 500 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot112_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot112_resized.png` | 1090923 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot180_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot180_content.txt` | 22921 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot180_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot180_metadata.json` | 491 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot180_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot180_resized.png` | 1550036 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot200_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot200_content.txt` | 8269 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot200_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot200_metadata.json` | 497 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot200_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot200_resized.png` | 1117963 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot270_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot270_content.txt` | 2251 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot270_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot270_metadata.json` | 496 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot270_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot270_resized.png` | 1543949 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot359_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot359_content.txt` | 25049 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot359_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot359_metadata.json` | 499 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p06_rot359_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p06_rot359_resized.png` | 1523894 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot000_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot000_content.txt` | 2368 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot000_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot000_metadata.json` | 423 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot000_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot000_resized.png` | 3295863 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot087_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot087_content.txt` | 13 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot087_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot087_metadata.json` | 496 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot087_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot087_resized.png` | 5270143 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot356_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot356_content.txt` | 25138 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot356_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot356_metadata.json` | 501 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot356_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot356_resized.png` | 5153041 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot358_content.txt` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot358_content.txt` | 23313 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot358_metadata.json` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot358_metadata.json` | 501 |
| `runs/hunyuan/single_page/fireinsurance_victoria_1895_p25_rot358_resized.png` | `~/projects/hunyuan/input/fireinsurance_victoria_1895_p25_rot358_resized.png` | 5372940 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v1_coordinates.json` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v1_coordinates.json` | 57878 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v1.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v1.log` | 47915 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v1.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v1.png` | 1053551 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v2_coordinates.json` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v2_coordinates.json` | 441879 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v2.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v2.log` | 356624 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v2.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_cropped_resized_overlay_v2.png` | 2215987 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v1.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v1.log` | 69629 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v1.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v1.png` | 4421689 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v2.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v2.log` | 85999 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v2.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v2.png` | 4417660 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v3.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v3.log` | 85999 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v3.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v3.png` | 4417660 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v4.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v4.log` | 85937 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v4.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot000_resized_overlay_v4.png` | 4405731 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot090_resized_overlay_v1.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot090_resized_overlay_v1.log` | 278819 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot090_resized_overlay_v1.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot090_resized_overlay_v1.png` | 4464018 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v1.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v1.log` | 256780 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v1.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v1.png` | 3497113 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v2.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v2.log` | 272823 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v2.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v2.png` | 3532894 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v3.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v3.log` | 256667 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v3.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v3.png` | 3543794 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v4.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v4.log` | 256667 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v4.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v4.png` | 3543794 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v5.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v5.log` | 272823 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v5.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v5.png` | 3532894 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v6.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v6.log` | 272823 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v6.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v6.png` | 3532894 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v7.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v7.log` | 272823 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v7.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v7.png` | 3532894 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v8.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v8.log` | 276039 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v8.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot105_resized_overlay_v8.png` | 3534657 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot112_resized_overlay_v1.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot112_resized_overlay_v1.log` | 48572 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p06b_rot112_resized_overlay_v1.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p06b_rot112_resized_overlay_v1.png` | 902204 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p25_rot000_resized_overlay_v1_coordinates.json` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p25_rot000_resized_overlay_v1_coordinates.json` | 37452 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p25_rot000_resized_overlay_v1.log` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p25_rot000_resized_overlay_v1.log` | 32081 |
| `runs/hunyuan/single_page/overlays/fireinsurance_victoria_1895_p25_rot000_resized_overlay_v1.png` | `~/projects/hunyuan/output/fireinsurance_victoria_1895_p25_rot000_resized_overlay_v1.png` | 3235559 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot000_content.txt` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot000_content.txt` | 17706 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | 1110 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot000_resized.png` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot000_resized.png` | 1295321 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot090_content.txt` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot090_content.txt` | 1337 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot090_metadata.json` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot090_metadata.json` | 1114 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot090_resized.png` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot090_resized.png` | 1301429 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot105_content.txt` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot105_content.txt` | 24537 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot105_metadata.json` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot105_metadata.json` | 1118 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot105_resized.png` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot105_resized.png` | 1022968 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot112_content.txt` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot112_content.txt` | 19725 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot112_metadata.json` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot112_metadata.json` | 1119 |
| `runs/hunyuan/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot112_resized.png` | `~/projects/hunyuan/input/p06b_rot_coords_run/fireinsurance_victoria_1895_p06b_rot112_resized.png` | 960751 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col2/fireinsurance_victoria_1885_Index_col2.html` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col2/fireinsurance_victoria_1885_Index_col2.html` | 9335 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col2/fireinsurance_victoria_1885_Index_col2.md` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col2/fireinsurance_victoria_1885_Index_col2.md` | 6123 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col2/fireinsurance_victoria_1885_Index_col2_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col2/fireinsurance_victoria_1885_Index_col2_metadata.json` | 353 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col3/fireinsurance_victoria_1885_Index_col3.html` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col3/fireinsurance_victoria_1885_Index_col3.html` | 7605 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col3/fireinsurance_victoria_1885_Index_col3.md` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col3/fireinsurance_victoria_1885_Index_col3.md` | 4275 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col3/fireinsurance_victoria_1885_Index_col3_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col3/fireinsurance_victoria_1885_Index_col3_metadata.json` | 353 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col4/fireinsurance_victoria_1885_Index_col4.html` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col4/fireinsurance_victoria_1885_Index_col4.html` | 2366 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col4/fireinsurance_victoria_1885_Index_col4.md` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col4/fireinsurance_victoria_1885_Index_col4.md` | 4539 |
| `runs/chandra/fireinsurance_victoria_1885_Index_col4/fireinsurance_victoria_1885_Index_col4_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_col4/fireinsurance_victoria_1885_Index_col4_metadata.json` | 351 |
| `runs/chandra/fireinsurance_victoria_1885_Index_table/chandra_run.log` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_table/chandra_run.log` | 1714 |
| `runs/chandra/fireinsurance_victoria_1885_Index_table_col1/chandra_run.log` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_table_col1/chandra_run.log` | 3107 |
| `runs/chandra/fireinsurance_victoria_1885_Index_table_col1/fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1.html` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_table_col1/fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1.html` | 2214 |
| `runs/chandra/fireinsurance_victoria_1885_Index_table_col1/fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1.md` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_table_col1/fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1.md` | 1923 |
| `runs/chandra/fireinsurance_victoria_1885_Index_table_col1/fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_table_col1/fireinsurance_victoria_1885_Index_col1/fireinsurance_victoria_1885_Index_col1_metadata.json` | 351 |
| `runs/chandra/fireinsurance_victoria_1885_Index_table/fireinsurance_victoria_1885_Index/fireinsurance_victoria_1885_Index.html` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_table/fireinsurance_victoria_1885_Index/fireinsurance_victoria_1885_Index.html` | 8239 |
| `runs/chandra/fireinsurance_victoria_1885_Index_table/fireinsurance_victoria_1885_Index/fireinsurance_victoria_1885_Index.md` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_table/fireinsurance_victoria_1885_Index/fireinsurance_victoria_1885_Index.md` | 142922 |
| `runs/chandra/fireinsurance_victoria_1885_Index_table/fireinsurance_victoria_1885_Index/fireinsurance_victoria_1885_Index_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1885_Index_table/fireinsurance_victoria_1885_Index/fireinsurance_victoria_1885_Index_metadata.json` | 350 |
| `runs/chandra/fireinsurance_victoria_1885_Key_description/chandra_run.log` | `~/projects/chandra/output/fireinsurance_victoria_1885_Key_description/chandra_run.log` | 971 |
| `runs/chandra/fireinsurance_victoria_1885_Key_description/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.html` | `~/projects/chandra/output/fireinsurance_victoria_1885_Key_description/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.html` | 3719 |
| `runs/chandra/fireinsurance_victoria_1885_Key_description/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.md` | `~/projects/chandra/output/fireinsurance_victoria_1885_Key_description/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.md` | 2157 |
| `runs/chandra/fireinsurance_victoria_1885_Key_description/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1885_Key_description/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key_metadata.json` | 344 |
| `runs/chandra/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.html` | `~/projects/chandra/output/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.html` | 4838 |
| `runs/chandra/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.md` | `~/projects/chandra/output/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key.md` | 2683 |
| `runs/chandra/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1885_Key/fireinsurance_victoria_1885_Key_metadata.json` | 346 |
| `runs/chandra/fireinsurance_victoria_1895_p01/fireinsurance_victoria_1895_p01.html` | `~/projects/chandra/output/fireinsurance_victoria_1895_p01/fireinsurance_victoria_1895_p01.html` | 5343 |
| `runs/chandra/fireinsurance_victoria_1895_p01/fireinsurance_victoria_1895_p01.md` | `~/projects/chandra/output/fireinsurance_victoria_1895_p01/fireinsurance_victoria_1895_p01.md` | 4357 |
| `runs/chandra/fireinsurance_victoria_1895_p01/fireinsurance_victoria_1895_p01_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1895_p01/fireinsurance_victoria_1895_p01_metadata.json` | 346 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/chandra_run.log` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/chandra_run.log` | 3084 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.html` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.html` | 0 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.md` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.md` | 0 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | 352 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.html` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.html` | 1882 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.md` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.md` | 1811 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | 352 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/output/chandra_run.log` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/output/chandra_run.log` | 1030 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.html` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.html` | 0 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.md` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000.md` | 0 |
| `runs/chandra/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000/output/fireinsurance_victoria_1895_p06b_rot000/fireinsurance_victoria_1895_p06b_rot000_metadata.json` | 352 |
| `runs/chandra/fireinsurance_victoria_1895_p25_rot000/fireinsurance_victoria_1895_p25_rot000.html` | `~/projects/chandra/output/fireinsurance_victoria_1895_p25_rot000/fireinsurance_victoria_1895_p25_rot000.html` | 19884 |
| `runs/chandra/fireinsurance_victoria_1895_p25_rot000/fireinsurance_victoria_1895_p25_rot000.md` | `~/projects/chandra/output/fireinsurance_victoria_1895_p25_rot000/fireinsurance_victoria_1895_p25_rot000.md` | 14933 |
| `runs/chandra/fireinsurance_victoria_1895_p25_rot000/fireinsurance_victoria_1895_p25_rot000_metadata.json` | `~/projects/chandra/output/fireinsurance_victoria_1895_p25_rot000/fireinsurance_victoria_1895_p25_rot000_metadata.json` | 355 |

## Code lineage (nothing copied — imported/called in place)

| This repo | Depends on | Notes |
|---|---|---|
| `scripts/fim_hunyuan.py` | `~/projects/hunyuan/hepworth_hunyuan_batch.py` (`load_pil`, `resize_max_edge`, `hunyuan_infer_one`) | supersedes the hard-coded `~/projects/hunyuan/hunyuan_transformers.py` for this dataset |
| `scripts/fim_overlay.sh` | `~/projects/hunyuan/overlay_boxes.py` | |
| `scripts/fim_chandra.sh` | `~/projects/chandra` CLI with local `--prompt` patch (`chandra/scripts/cli.py`, uncommitted there) | |
| `scripts/fim_csvify.py` | `~/projects/recast` (`recast.config`, `recast.converter`) | configs come from `configs/recast/` here, not recast's |
| `configs/recast/*.yaml` | — | reconstructed; the originals (`fireinsurance_1885/1895/key`) were deleted from recast/configs |
| `configs/prompts/*.txt` | — | recovered verbatim from `*_metadata.json` / `chandra_run.log` |
