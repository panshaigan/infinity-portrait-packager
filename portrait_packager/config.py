from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_FORMATS = frozenset({"bmp", "webp"})


@dataclass(frozen=True)
class SizeMapping:
    width: int
    height: int


@dataclass(frozen=True)
class ThumbnailConfig:
    max_size: int


@dataclass(frozen=True)
class Destination:
    id: str
    path: Path
    format: str
    mappings: dict[str, SizeMapping]
    webp_quality: int = 85
    thumbnails: ThumbnailConfig | None = None


@dataclass(frozen=True)
class Config:
    sources_root: Path
    categories: list[str]
    destinations: list[Destination]


class ConfigError(Exception):
    """Raised when config validation fails."""


def _require_mapping(data: dict[str, Any], key: str, context: str) -> Any:
    if key not in data:
        raise ConfigError(f"{context}: missing required field '{key}'")
    return data[key]


def _parse_size_mapping(data: Any, context: str) -> SizeMapping:
    if not isinstance(data, dict):
        raise ConfigError(f"{context}: mapping must be an object with width and height")
    try:
        width = int(_require_mapping(data, "width", context))
        height = int(_require_mapping(data, "height", context))
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{context}: width and height must be integers") from exc
    if width <= 0 or height <= 0:
        raise ConfigError(f"{context}: width and height must be positive")
    return SizeMapping(width=width, height=height)


def _parse_thumbnail(data: Any, context: str) -> ThumbnailConfig:
    if not isinstance(data, dict):
        raise ConfigError(f"{context}: thumbnails must be an object")
    if "max_size" not in data:
        raise ConfigError(f"{context}: thumbnails must define max_size")
    extra_keys = set(data) - {"max_size"}
    if extra_keys:
        raise ConfigError(
            f"{context}: thumbnails only supports max_size, got: {', '.join(sorted(extra_keys))}"
        )
    try:
        max_size = int(data["max_size"])
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{context}: max_size must be an integer") from exc
    if max_size <= 0:
        raise ConfigError(f"{context}: max_size must be positive")
    return ThumbnailConfig(max_size=max_size)


def _parse_destination(data: Any, categories: list[str], index: int) -> Destination:
    context = f"destinations[{index}]"
    if not isinstance(data, dict):
        raise ConfigError(f"{context}: must be an object")

    dest_id = _require_mapping(data, "id", context)
    if not isinstance(dest_id, str) or not dest_id.strip():
        raise ConfigError(f"{context}: id must be a non-empty string")

    path_raw = _require_mapping(data, "path", context)
    if not isinstance(path_raw, str) or not path_raw.strip():
        raise ConfigError(f"{context}: path must be a non-empty string")

    fmt = _require_mapping(data, "format", context)
    if not isinstance(fmt, str) or fmt not in SUPPORTED_FORMATS:
        raise ConfigError(
            f"{context}: format must be one of: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    mappings_raw = _require_mapping(data, "mappings", context)
    if not isinstance(mappings_raw, dict):
        raise ConfigError(f"{context}: mappings must be an object")

    mappings: dict[str, SizeMapping] = {}
    for category in categories:
        if category not in mappings_raw:
            raise ConfigError(f"{context}: missing mapping for category '{category}'")
        mappings[category] = _parse_size_mapping(
            mappings_raw[category], f"{context}.mappings.{category}"
        )

    extra_categories = set(mappings_raw) - set(categories)
    if extra_categories:
        raise ConfigError(
            f"{context}: unknown mapping categories: {', '.join(sorted(extra_categories))}"
        )

    webp_quality = 85
    if "webp_quality" in data:
        try:
            webp_quality = int(data["webp_quality"])
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"{context}: webp_quality must be an integer") from exc
        if not 1 <= webp_quality <= 100:
            raise ConfigError(f"{context}: webp_quality must be between 1 and 100")

    thumbnails = None
    if "thumbnails" in data and data["thumbnails"] is not None:
        thumbnails = _parse_thumbnail(data["thumbnails"], f"{context}.thumbnails")

    return Destination(
        id=dest_id,
        path=Path(path_raw),
        format=fmt,
        mappings=mappings,
        webp_quality=webp_quality,
        thumbnails=thumbnails,
    )


def load_config(path: Path) -> Config:
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as handle:
        try:
            raw = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a mapping")

    sources = _require_mapping(raw, "sources", "config")
    if not isinstance(sources, dict):
        raise ConfigError("config.sources must be an object")
    root_raw = _require_mapping(sources, "root", "config.sources")
    if not isinstance(root_raw, str) or not root_raw.strip():
        raise ConfigError("config.sources.root must be a non-empty string")

    categories_raw = _require_mapping(raw, "categories", "config")
    if not isinstance(categories_raw, list) or not categories_raw:
        raise ConfigError("config.categories must be a non-empty list")
    categories: list[str] = []
    for index, category in enumerate(categories_raw):
        if not isinstance(category, str) or not category:
            raise ConfigError(f"config.categories[{index}] must be a non-empty string")
        categories.append(category)

    destinations_raw = _require_mapping(raw, "destinations", "config")
    if not isinstance(destinations_raw, list) or not destinations_raw:
        raise ConfigError("config.destinations must be a non-empty list")

    destinations = [
        _parse_destination(item, categories, index)
        for index, item in enumerate(destinations_raw)
    ]

    dest_ids = [dest.id for dest in destinations]
    if len(dest_ids) != len(set(dest_ids)):
        raise ConfigError("config.destinations: duplicate destination id")

    return Config(
        sources_root=Path(root_raw),
        categories=categories,
        destinations=destinations,
    )
