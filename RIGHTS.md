# Rights and what this repository does and does not contain

## Source images

The scans are the Chas. E. Goad fire insurance plans of Victoria, B.C. (1885 index/key and the 1891→1895
revised book), digitised by the Royal BC Museum (RBCM) and made available through UVic Vault.

The Vault record carries the rights statement **"No copyright – Other known legal restrictions"**
([rightsstatements.org NoC-OKLR](https://rightsstatements.org/vocab/NoC-OKLR/1.0/)). That means two
separate things:

1. **The plans themselves are out of copyright.** Goad's 1885–1895 drawings are public domain.
2. **The digital images are not freely reusable — they are under a legal protective order.** The record states that RBCM provided them to UVic for
   dissemination **for research purposes only**, under licence, and that they **cannot be duplicated,
   shared, or transferred in any format**. That is a contractual restriction on the scan files, not a
   copyright claim on the maps. Higher-resolution TIFFs and publication/commercial use are handled by RBCM
   directly, with fees.

## What follows for this repository

- **No scan, crop, tile, resized input, or overlay is committed.** `.gitignore` excludes every raster
  format. Every such image contains the RBCM scan and is covered by the restriction above. The scans
  live outside the repository (`data/` holds symlinks; see `data/README.md`) and are not part of any push.
- **Derived data is not committed either (since 2026-09-17).** OCR tokens with coordinates, block and
  building polygons, georeferenced GeoJSON, run logs and viewer pages are text and JSON produced by this
  pipeline and describe the public-domain plans rather than reproduce the image files — but the Victoria
  scans are under a legal protective order, so until their derived outputs are cleared for release nothing
  under `runs/` is tracked (`.gitignore`). Results stay on the machine that made them. The repository
  holds the code, the configs, the modern street layers and the two public test sheets' inputs; run the
  pipeline to regenerate any output.
- **Modern reference layers** under `data/modern/` come from the City of Victoria and Capital Regional
  District open-data ArcGIS services and OpenStreetMap (ODbL). Attribute them if you reuse them.
- **The code is city-agnostic.** Nothing here requires the RBCM scans; point it at any fire insurance
  plan you have rights to.

## Using this work

Treat the repository as **research use only**. To test the pipeline, download any Sanborn map and process using the appropriate cities' modern geo data.

This is a summary by the maintainer, not legal advice.
