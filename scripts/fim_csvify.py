#!/usr/bin/env python3
"""
Convert a Chandra markdown/HTML table run into CSV using the fire insurance configs in configs/recast/.

Thin wrapper over ~/projects/recast (RECAST_SRC to override): the recast CLI only looks in its own
configs/ directory, and the fire insurance configs used to live there and were lost, so this script
points recast at this project's configs instead. recast itself is not modified.

    scripts/fim_csvify.py runs/chandra/fireinsurance_victoria_1885_Index_col2            # auto-detect config
    scripts/fim_csvify.py runs/chandra/fireinsurance_victoria_1885_Index_table -c fireinsurance_1885_blocks -o out.csv
    scripts/fim_csvify.py --list-configs
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs" / "recast"
RECAST_SRC = Path(os.environ.get("RECAST_SRC", "~/projects/recast")).expanduser().resolve()
sys.path.insert(0, str(RECAST_SRC))

try:
    from recast.config import get_config, list_configs  # noqa: E402
    from recast.converter import convert_file  # noqa: E402
except ImportError:
    # System python may lack yaml/bs4/click; re-exec under recast's own venv.
    venv_py = RECAST_SRC / ".venv" / "bin" / "python"
    if venv_py.is_file() and os.environ.get("FIM_CSVIFY_REEXEC") != "1":
        os.environ["FIM_CSVIFY_REEXEC"] = "1"
        os.execv(str(venv_py), [str(venv_py), __file__, *sys.argv[1:]])
    raise


def resolve_targets(path: Path) -> list[tuple[Path, str]]:
    """(md_path, name) pairs — mirrors recast.cli._resolve_targets plus Chandra's nested <run>/<stem>/<stem>.md."""
    path = path.resolve()
    if path.is_file():
        return [(path, path.stem)] if path.suffix.lower() in (".md", ".html") else []
    found: list[tuple[Path, str]] = []
    for item in sorted(path.iterdir()):
        if item.is_dir() and (item / f"{item.name}.md").exists():
            found.append((item / f"{item.name}.md", item.name))
    if not found and (path / f"{path.name}.md").exists():
        found.append((path / f"{path.name}.md", path.name))
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", type=Path, help="Chandra run dir, <stem>/<stem>.md dir, or .md file")
    ap.add_argument("-c", "--config", help="Config name in configs/recast/ (default: auto-detect from path)")
    ap.add_argument("-o", "--output", type=Path, help="CSV file (single target) or directory")
    ap.add_argument("--list-configs", action="store_true")
    args = ap.parse_args()

    if args.list_configs:
        for cfg in sorted(list_configs(CONFIGS_DIR), key=lambda c: c.name):
            print(f"{cfg.name}: columns={cfg.columns} matches={cfg.filename_patterns} priority={cfg.match_priority}")
        return
    if not args.path:
        ap.error("path is required (or --list-configs)")

    targets = resolve_targets(args.path)
    if not targets:
        sys.exit(f"no <name>/<name>.md found under {args.path}")

    for md, name in targets:
        cfg = get_config(args.config, md, CONFIGS_DIR)
        if cfg is None:
            sys.exit(f"no config in {CONFIGS_DIR} matches {name!r}; pass -c")
        if args.output and len(targets) == 1 and args.output.suffix.lower() == ".csv":
            out = args.output
        elif args.output:
            out = args.output / f"{name}.csv"
        else:
            out = md.with_suffix(".csv")
        out.parent.mkdir(parents=True, exist_ok=True)
        n = convert_file(md, out, cfg)
        print(f"{name} [{cfg.name}] -> {out} ({n} rows)")


if __name__ == "__main__":
    main()
