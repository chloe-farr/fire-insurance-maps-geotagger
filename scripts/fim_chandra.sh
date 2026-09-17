#!/usr/bin/env bash
# Run Chandra (Datalab) on a fire insurance scan with a custom prompt, via the local checkout's CLI.
# Requires the --prompt option added to ~/projects/chandra/chandra/scripts/cli.py (local modification, uncommitted
# there) — that CLI also writes chandra_run.log into the output dir, which docs/run_history.md is built from.
#
#   scripts/fim_chandra.sh <input image|dir> <output-dir> (--preset NAME | --prompt "text") [-- extra chandra args]
#
#   scripts/fim_chandra.sh data/1885/fireinsurance_victoria_1885_Index_col1.jpg runs/chandra/2026-09-10_Index_col1 \
#       --preset index_1885_streets
#
# Output layout is Chandra's: <output-dir>/<stem>/<stem>.md + .html + _metadata.json (+ chandra_run.log).
set -euo pipefail
CHANDRA_SRC="${CHANDRA_SRC:-$HOME/projects/chandra}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
if [[ $# -lt 3 ]]; then sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 1; fi
in="$(readlink -f "$1")"; out="$(readlink -f -m "$2")"; shift 2
prompt=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preset) f="$HERE/configs/prompts/$2.txt"; [[ -f "$f" ]] || { echo "no preset $2 in configs/prompts/" >&2; exit 1; }
              prompt="$(cat "$f")"; shift 2;;
    --prompt) prompt="$2"; shift 2;;
    --) shift; break;;
    *) break;;
  esac
done
[[ -n "$prompt" ]] || { echo "need --preset or --prompt" >&2; exit 1; }
mkdir -p "$out"
cd "$CHANDRA_SRC"
exec uv run chandra "$in" "$out" --method hf --prompt "$prompt" "$@"
