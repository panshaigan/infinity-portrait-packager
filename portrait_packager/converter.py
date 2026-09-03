from __future__ import annotations

import math
from pathlib import Path

from PIL import Image

SUPPORTED_INPUT_EXTENSIONS = frozenset({".png", ".bmp", ".webp", ".jpg", ".jpeg"})
FORMAT_EXTENSIONS = {"bmp": ".bmp", "webp": ".webp"}


def output_name(stem: str, category: str, dest_format: str, prefix: str = "") -> str:
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


def resize_exact(image: Image.Image, width: int, height: int) -> Image.Image:
    if image.size == (width, height):
        return image.copy()
    return image.resize((width, height), Image.Resampling.LANCZOS)


def resize_max_side(image: Image.Image, max_size: int) -> Image.Image:
    resized = image.copy()
    resized.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
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


def resize_to_width(image: Image.Image, width: int) -> Image.Image:
    if image.width == width:
        return image.copy()
    ratio = width / image.width
    new_height = max(1, round(image.height * ratio))
    return image.resize((width, new_height), Image.Resampling.LANCZOS)


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
