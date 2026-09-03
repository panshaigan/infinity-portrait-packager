from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portrait_packager import __version__
from portrait_packager.config import ConfigError, load_config
from portrait_packager.processor import process_group


def resolve_default_config() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path.cwd()
    return base_dir / "config.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ppackage",
        description="Convert portrait groups for distribution and promotion.",
    )
    parser.add_argument(
        "group",
        help="Portrait group folder name under sources.root (e.g. party_bg1)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config.yaml (default: config.yaml next to executable or CWD)",
    )
    parser.add_argument(
        "--dest",
        dest="dest_filter",
        help="Process only the destination with this id",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be converted without writing files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-file conversion details",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = args.config or resolve_default_config()

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    mode = " (dry run)" if args.dry_run else ""
    print(f"Processing: {args.group}{mode}")

    result = process_group(
        config,
        args.group,
        dest_filter=args.dest_filter,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    for warning in result.warnings:
        if not warning.startswith("WARN:"):
            print(f"WARN: {warning}")

    if not result.ok:
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if any("Portrait group not found" in error for error in result.errors):
            return 1
        return 3

    summary_parts = [f"{result.files_written} files written"]
    if result.thumbs_written:
        summary_parts.append(f"{result.thumbs_written} thumbs")
    if result.contact_sheets_written:
        summary_parts.append(f"{result.contact_sheets_written} contact sheets")
    if result.warnings:
        summary_parts.append(f"{len(result.warnings)} warnings")
    print(f"Done: {', '.join(summary_parts)}")
    return 0
