from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from portrait_packager.config import Config, ContactSheetConfig, Destination
from portrait_packager.converter import (
    SUPPORTED_INPUT_EXTENSIONS,
    build_contact_sheet,
    lookup_prefix,
    output_name,
    resize_exact,
    resize_max_side,
    resize_to_width,
    save_image,
)

MAX_STEM_LENGTH = 7


@dataclass
class ProcessResult:
    files_written: int = 0
    thumbs_written: int = 0
    contact_sheets_written: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    category_counts: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _iter_image_files(category_dir: Path) -> list[Path]:
    files = [
        path
        for path in sorted(category_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS
    ]
    return files


def _append_warning(result: ProcessResult, warning: str) -> None:
    result.warnings.append(warning)
    print(f"WARN: {warning}")


def _validate_source_filenames(
    source_group: Path,
    categories: list[str],
    result: ProcessResult,
) -> None:
    stems_by_category: dict[str, set[str]] = {}
    display_stem: dict[str, str] = {}

    for category in categories:
        category_dir = source_group / category
        if not category_dir.is_dir():
            continue

        stems: set[str] = set()
        for path in _iter_image_files(category_dir):
            if len(path.stem) > MAX_STEM_LENGTH:
                _append_warning(
                    result,
                    f"source filename stem longer than {MAX_STEM_LENGTH} characters: "
                    f"{category}/{path.name}",
                )
            key = path.stem.lower()
            stems.add(key)
            display_stem.setdefault(key, path.stem)
        stems_by_category[category] = stems

    if len(stems_by_category) < 2:
        return

    present_categories = list(stems_by_category)
    all_stems = set().union(*stems_by_category.values())
    for key in sorted(all_stems):
        missing = [cat for cat, stems in stems_by_category.items() if key not in stems]
        if not missing:
            continue
        present = [cat for cat in present_categories if key in stems_by_category[cat]]
        _append_warning(
            result,
            f"filename '{display_stem[key]}' missing from categories: "
            f"{', '.join(missing)} (present in: {', '.join(present)})",
        )


def _process_image(
    source_path: Path,
    category: str,
    destination: Destination,
    dest_dir: Path,
    thumbs_dir: Path | None,
    dry_run: bool,
    verbose: bool,
    result: ProcessResult,
    written_by_category: dict[str, list[Path]] | None = None,
) -> None:
    mapping = destination.mappings[category]
    prefix = lookup_prefix(destination.prefixes, source_path.stem)
    out_name = output_name(source_path.stem, category, destination.format, prefix)
    out_path = dest_dir / out_name

    try:
        with Image.open(source_path) as image:
            main_image = resize_exact(image, mapping.width, mapping.height)
    except (UnidentifiedImageError, OSError) as exc:
        result.errors.append(f"Failed to read {source_path}: {exc}")
        return

    if verbose:
        prefix_note = f" [prefix: {prefix!r}]" if prefix else ""
        print(
            f"  {source_path.name} -> {out_name} "
            f"({main_image.width}x{main_image.height}){prefix_note}"
        )

    if not dry_run:
        try:
            save_image(main_image, out_path, destination.format, destination.webp_quality)
        except OSError as exc:
            result.errors.append(f"Failed to write {out_path}: {exc}")
            return

    result.files_written += 1

    if written_by_category is not None:
        written_by_category.setdefault(category, []).append(out_path)

    if destination.thumbnails is None:
        return

    thumb_path = thumbs_dir / out_name
    thumb_image = resize_max_side(
        main_image,
        destination.thumbnails.max_size,
    )

    if not dry_run:
        try:
            save_image(thumb_image, thumb_path, destination.format, destination.webp_quality)
        except OSError as exc:
            result.errors.append(f"Failed to write {thumb_path}: {exc}")
            return

    result.thumbs_written += 1


def _resolve_contact_sheet_cols(
    contact_sheet: ContactSheetConfig,
    group: str,
    *,
    cols_override: int | None,
) -> int | None:
    if cols_override is not None:
        return cols_override
    return contact_sheet.cols.get(group)


def _generate_contact_sheets(
    destination: Destination,
    group: str,
    written_by_category: dict[str, list[Path]],
    *,
    cols_override: int | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    result: ProcessResult,
) -> None:
    contact_sheet = destination.contact_sheet
    if contact_sheet is None:
        return

    cols = _resolve_contact_sheet_cols(contact_sheet, group, cols_override=cols_override)
    if cols is None:
        result.errors.append(
            f"[{destination.id}] contact_sheet.cols has no entry for group '{group}'"
        )
        return

    label = f"[{destination.id}]"
    output_dir = contact_sheet.path

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    for category, image_paths in sorted(written_by_category.items()):
        if not image_paths:
            continue

        sheet_name = f"{group}_{category}.webp"
        thumb_name = f"{group}_{category}_thumb.webp"
        sheet_path = output_dir / sheet_name
        thumb_path = output_dir / thumb_name

        if verbose or dry_run:
            print(
                f"{label} contact sheet {category}: {len(image_paths)} images, "
                f"{cols} cols -> {sheet_path.name}, {thumb_path.name}"
            )

        if dry_run:
            result.contact_sheets_written += 1
            continue

        try:
            sheet = build_contact_sheet(
                sorted(image_paths),
                cols,
            )
            sheet = resize_to_width(sheet, contact_sheet.width)
            save_image(sheet, sheet_path, "webp", destination.webp_quality)
            thumb = resize_to_width(sheet, contact_sheet.thumb_width)
            save_image(thumb, thumb_path, "webp", destination.webp_quality)
        except (OSError, ValueError) as exc:
            result.errors.append(
                f"Failed to build contact sheet for {category}: {exc}"
            )
            continue

        result.contact_sheets_written += 1


def process_group(
    config: Config,
    group: str,
    *,
    dest_filter: str | None = None,
    cols_override: int | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> ProcessResult:
    result = ProcessResult()
    source_group = config.sources_root / group

    if not source_group.is_dir():
        result.errors.append(f"Portrait group not found: {source_group}")
        return result

    destinations = config.destinations
    if dest_filter is not None:
        destinations = [dest for dest in destinations if dest.id == dest_filter]
        if not destinations:
            result.errors.append(f"Unknown destination id: {dest_filter}")
            return result

    for destination in destinations:
        dest_counts: dict[str, int] = {}
        written_by_category: dict[str, list[Path]] = {}
        dest_dir = destination.path / group
        thumbs_dir = dest_dir / "thumbs" if destination.thumbnails else None

        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if thumbs_dir is not None:
                thumbs_dir.mkdir(parents=True, exist_ok=True)

        label = f"[{destination.id}]"
        if verbose or dry_run:
            print(f"{label} -> {dest_dir} ({destination.format})")

        for category in config.categories:
            if category not in destination.mappings:
                if verbose:
                    print(f"{label} {category}: skipped (no mapping configured)")
                continue

            category_dir = source_group / category
            if not category_dir.is_dir():
                _append_warning(
                    result,
                    f"{label} category '{category}' not found, skipping",
                )
                continue

            image_files = _iter_image_files(category_dir)
            dest_counts[category] = len(image_files)

            if verbose or dry_run:
                mapping = destination.mappings[category]
                print(
                    f"{label} {category}: {len(image_files)} files "
                    f"-> {mapping.width}x{mapping.height} {destination.format}"
                )

            for source_path in image_files:
                _process_image(
                    source_path,
                    category,
                    destination,
                    dest_dir,
                    thumbs_dir,
                    dry_run,
                    verbose,
                    result,
                    written_by_category if destination.contact_sheet else None,
                )

        if destination.thumbnails and dest_counts:
            thumb_total = sum(dest_counts.values())
            if verbose or dry_run:
                print(
                    f"{label} thumbs: {thumb_total} files "
                    f"-> max {destination.thumbnails.max_size}px"
                )

        _generate_contact_sheets(
            destination,
            group,
            written_by_category,
            cols_override=cols_override,
            dry_run=dry_run,
            verbose=verbose,
            result=result,
        )

        result.category_counts[destination.id] = dest_counts

    _validate_source_filenames(source_group, config.categories, result)

    return result
