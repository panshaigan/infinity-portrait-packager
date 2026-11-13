from __future__ import annotations

import math
from pathlib import Path

from PIL import Image

SUPPORTED_INPUT_EXTENSIONS = frozenset({".png", ".bmp", ".webp", ".jpg", ".jpeg"})
FORMAT_EXTENSIONS = {"bmp": ".bmp", "webp": ".webp"}


def normalize_stem_for_category(stem: str, category: str) -> tuple[str, str]:
    """Return (stem, category) with Infinity Engine casing: L/M upper, r lower."""
    cat = category.lower()
    if cat in ("l", "m"):
        return stem.upper(), category.upper()
    if cat == "r":
        return stem.lower(), "r"
    return stem, category


def output_name(stem: str, category: str, dest_format: str, prefix: str = "") -> str:
    if category == "special":
        return f"{stem}{FORMAT_EXTENSIONS[dest_format]}"
    stem, category = normalize_stem_for_category(stem, category)
    ext = FORMAT_EXTENSIONS[dest_format]
    return f"{prefix}{stem}{category}{ext}"


def lookup_prefix(prefixes: dict[str, str], stem: str) -> str:
    if stem in prefixes:
        return prefixes[stem]
    stem_lower = stem.lower()
    for key, value in prefixes.items():
        if key.lower() == stem_lower:
            return value
    return ""


RESAMPLING_FILTERS = {
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


def _prepare_for_resize(image: Image.Image) -> Image.Image:
    # Pillow forces nearest-neighbor for indexed and 1-bit images.
    if image.mode in {"1", "P", "PA"}:
        has_alpha = image.mode == "PA" or "transparency" in image.info
        return image.convert("RGBA" if has_alpha else "RGB")
    return image


def resize_exact(
    image: Image.Image, width: int, height: int, resampling: str = "bicubic"
) -> Image.Image:
    if image.size == (width, height):
        return image.copy()
    return _prepare_for_resize(image).resize(
        (width, height), RESAMPLING_FILTERS[resampling]
    )


def resize_max_side(
    image: Image.Image, max_size: int, resampling: str = "bicubic"
) -> Image.Image:
    resized = _prepare_for_resize(image).copy()
    resized.thumbnail((max_size, max_size), RESAMPLING_FILTERS[resampling])
    return resized


def save_image(
    image: Image.Image,
    path: Path,
    dest_format: str,
    webp_quality: int = 85,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if dest_format == "bmp":
        image.convert("RGB").save(path, format="BMP")
    elif dest_format == "webp":
        image.save(path, format="WEBP", quality=webp_quality)
    else:
        raise ValueError(f"Unsupported format: {dest_format}")


def resize_to_width(
    image: Image.Image, width: int, resampling: str = "bicubic"
) -> Image.Image:
    if image.width == width:
        return image.copy()
    ratio = width / image.width
    new_height = max(1, round(image.height * ratio))
    return _prepare_for_resize(image).resize(
        (width, new_height), RESAMPLING_FILTERS[resampling]
    )


def build_contact_sheet(
    image_paths: list[Path],
    cols: int,
    *,
    gap: int = 1,
) -> Image.Image:
    if not image_paths:
        raise ValueError("image_paths must not be empty")
    if cols <= 0:
        raise ValueError("cols must be positive")

    images: list[Image.Image] = []
    cell_width = 0
    cell_height = 0
    for path in image_paths:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            if cell_width == 0:
                cell_width, cell_height = rgb.size
            elif rgb.size != (cell_width, cell_height):
                raise ValueError(
                    f"Contact sheet images must share the same size; "
                    f"expected {cell_width}x{cell_height}, got {rgb.size} in {path.name}"
                )
            images.append(rgb.copy())

    rows = math.ceil(len(images) / cols)
    sheet_width = cols * cell_width + (cols - 1) * gap
    sheet_height = rows * cell_height + (rows - 1) * gap
    sheet = Image.new("RGB", (sheet_width, sheet_height), color=(0, 0, 0))

    for index, image in enumerate(images):
        row = index // cols
        col_in_row = index % cols
        count_in_row = len(images) - row * cols
        if count_in_row < cols:
            row_content_width = count_in_row * cell_width + (count_in_row - 1) * gap
            x_offset = (sheet_width - row_content_width) // 2
        else:
            x_offset = 0
        x = x_offset + col_in_row * (cell_width + gap)
        y = row * (cell_height + gap)
        sheet.paste(image, (x, y))

    return sheet
