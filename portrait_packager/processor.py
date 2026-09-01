from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from portrait_packager.config import Config, Destination
from portrait_packager.converter import (
    SUPPORTED_INPUT_EXTENSIONS,
    output_name,
    resize_fit,
    save_image,
)


@dataclass
class ProcessResult:
    files_written: int = 0
    thumbs_written: int = 0
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


def _process_image(
    source_path: Path,
    category: str,
    destination: Destination,
    dest_dir: Path,
    thumbs_dir: Path | None,
    dry_run: bool,
    verbose: bool,
    result: ProcessResult,
) -> None:
    mapping = destination.mappings[category]
    out_name = output_name(source_path.stem, category, destination.format)
    out_path = dest_dir / out_name

    try:
        with Image.open(source_path) as image:
            main_image = resize_fit(image, mapping.width, mapping.height)
    except (UnidentifiedImageError, OSError) as exc:
        result.errors.append(f"Failed to read {source_path}: {exc}")
        return

    if verbose:
        print(f"  {source_path.name} -> {out_name} ({main_image.width}x{main_image.height})")

    if not dry_run:
        try:
            save_image(main_image, out_path, destination.format, destination.webp_quality)
        except OSError as exc:
            result.errors.append(f"Failed to write {out_path}: {exc}")
            return

    result.files_written += 1

    if destination.thumbnails is None:
        return

    thumb_path = thumbs_dir / out_name
    thumb_image = resize_fit(
        main_image,
        destination.thumbnails.max_size,
        destination.thumbnails.max_size,
    )

    if not dry_run:
        try:
            save_image(thumb_image, thumb_path, destination.format, destination.webp_quality)
        except OSError as exc:
            result.errors.append(f"Failed to write {thumb_path}: {exc}")
            return

    result.thumbs_written += 1


def process_group(
    config: Config,
    group: str,
    *,
    dest_filter: str | None = None,
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
            category_dir = source_group / category
            if not category_dir.is_dir():
                warning = f"{label} category '{category}' not found, skipping"
                result.warnings.append(warning)
                print(f"WARN: {warning}")
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
                )

        if destination.thumbnails and dest_counts:
            thumb_total = sum(dest_counts.values())
            if verbose or dry_run:
                print(
                    f"{label} thumbs: {thumb_total} files "
                    f"-> max {destination.thumbnails.max_size}px"
                )

        result.category_counts[destination.id] = dest_counts

    return result
