from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portrait_packager import __version__
from portrait_packager.config import ConfigError, load_config
from portrait_packager.processor import ProcessResult, discover_groups, process_group


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
        nargs="?",
        default=None,
        help=(
            "Portrait group folder name under sources.root (e.g. party_bg1). "
            "If omitted, process all groups found under sources.root"
        ),
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
        "--cols",
        type=int,
        default=None,
        help="Override contact sheet column count for this group",
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


def _merge_results(total: ProcessResult, part: ProcessResult) -> None:
    total.files_written += part.files_written
    total.thumbs_written += part.thumbs_written
    total.contact_sheets_written += part.contact_sheets_written
    total.warnings.extend(part.warnings)
    total.errors.extend(part.errors)
    total.category_counts.update(part.category_counts)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = args.config or resolve_default_config()

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.cols is not None and args.cols <= 0:
        print("Config error: --cols must be a positive integer", file=sys.stderr)
        return 2

    if args.group is not None:
        groups = [args.group]
    else:
        groups = discover_groups(config)
        if not groups:
            print(
                f"ERROR: No portrait groups found under {config.sources_root}",
                file=sys.stderr,
            )
            return 1

    mode = " (dry run)" if args.dry_run else ""
    total = ProcessResult()

    for group in groups:
        print(f"Processing: {group}{mode}")
        result = process_group(
            config,
            group,
            dest_filter=args.dest_filter,
            cols_override=args.cols,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        _merge_results(total, result)

        for warning in result.warnings:
            if not warning.startswith("WARN:"):
                print(f"WARN: {warning}")

    if not total.ok:
        for error in total.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if any("Portrait group not found" in error for error in total.errors):
            return 1
        return 3

    summary_parts = [f"{total.files_written} files written"]
    if total.thumbs_written:
        summary_parts.append(f"{total.thumbs_written} thumbs")
    if total.contact_sheets_written:
        summary_parts.append(f"{total.contact_sheets_written} contact sheets")
    if total.warnings:
        summary_parts.append(f"{len(total.warnings)} warnings")
    print(f"Done: {', '.join(summary_parts)}")
    return 0
