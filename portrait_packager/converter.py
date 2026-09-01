from __future__ import annotations

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
