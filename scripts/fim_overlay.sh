#!/usr/bin/env bash
# Draw HunyuanOCR word boxes onto the resized image using ~/projects/hunyuan/overlay_boxes.py (read-only dependency).
#
#   scripts/fim_overlay.sh <stem>_resized.png <stem>_content.txt [output-dir] [-- extra overlay_boxes args]
#
# Default output-dir is the directory holding the content file, subfolder overlays/. Coordinates are treated as
# HunyuanOCR 0-1000 normalised (--scaling norm1000, the overlay_boxes default); the .log and *_coordinates.json
# written next to the PNG record the exact transform.
set -euo pipefail
HUNYUAN_SRC="${HUNYUAN_SRC:-$HOME/projects/hunyuan}"
if [[ $# -lt 2 ]]; then sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 1; fi
img="$1"; content="$2"; shift 2
out=""
if [[ $# -gt 0 && "$1" != "--" ]]; then out="$1"; shift; fi
[[ "${1:-}" == "--" ]] && shift
out="${out:-$(dirname "$content")/overlays}"
mkdir -p "$out"
exec python3 "$HUNYUAN_SRC/overlay_boxes.py" "$img" --content-file "$content" --output-dir "$out" "$@"
