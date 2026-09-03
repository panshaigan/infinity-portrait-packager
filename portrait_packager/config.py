from __future__ import annotations

from dataclasses import dataclass, field
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
class ContactSheetConfig:
    width: int
    thumb_width: int
    cols: dict[str, int]
    path: Path


@dataclass(frozen=True)
class Destination:
    id: str
    path: Path
    format: str
    mappings: dict[str, SizeMapping]
    webp_quality: int = 85
    thumbnails: ThumbnailConfig | None = None
    contact_sheet: ContactSheetConfig | None = None
    prefixes: dict[str, str] = field(default_factory=dict)


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


def _parse_contact_sheet_cols(data: Any, context: str) -> dict[str, int]:
    if not isinstance(data, dict) or not data:
        raise ConfigError(
            f"{context}: cols must be a non-empty object mapping group names to "
            "column counts"
        )
    cols: dict[str, int] = {}
    for group, value in data.items():
        if not isinstance(group, str) or not group:
            raise ConfigError(
                f"{context}.cols: group keys must be non-empty strings"
            )
        try:
            column_count = int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(
                f"{context}.cols.{group}: column count must be an integer"
            ) from exc
        if column_count <= 0:
            raise ConfigError(f"{context}.cols.{group}: column count must be positive")
        cols[group] = column_count
    return cols


def _parse_contact_sheet(data: Any, context: str) -> ContactSheetConfig:
    if not isinstance(data, dict):
        raise ConfigError(f"{context}: contact_sheet must be an object")
    required = {"width", "thumb_width", "cols", "path"}
    missing = required - set(data)
    if missing:
        raise ConfigError(
            f"{context}: contact_sheet missing required fields: "
            f"{', '.join(sorted(missing))}"
        )
    extra_keys = set(data) - required
    if extra_keys:
        raise ConfigError(
            f"{context}: contact_sheet only supports width, thumb_width, cols, "
            f"and path, got: {', '.join(sorted(extra_keys))}"
        )
    try:
        width = int(data["width"])
        thumb_width = int(data["thumb_width"])
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            f"{context}: width and thumb_width must be integers"
        ) from exc
    if width <= 0:
        raise ConfigError(f"{context}: width must be positive")
    if thumb_width <= 0:
        raise ConfigError(f"{context}: thumb_width must be positive")
    cols = _parse_contact_sheet_cols(data["cols"], context)
    path_raw = data["path"]
    if not isinstance(path_raw, str) or not path_raw.strip():
        raise ConfigError(f"{context}: path must be a non-empty string")
    return ContactSheetConfig(
        width=width,
        thumb_width=thumb_width,
        cols=cols,
        path=Path(path_raw),
    )


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


def _parse_prefixes(data: Any, context: str) -> dict[str, str]:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{context}: prefixes must be an object")
    prefixes: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not key:
            raise ConfigError(f"{context}.prefixes: keys must be non-empty strings")
        if not isinstance(value, str) or not value:
            raise ConfigError(
                f"{context}.prefixes.{key}: prefix value must be a non-empty string"
            )
        prefixes[key] = value
    return prefixes


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
    if not isinstance(mappings_raw, dict) or not mappings_raw:
        raise ConfigError(f"{context}: mappings must be a non-empty object")

    mappings: dict[str, SizeMapping] = {}
    for category, mapping_data in mappings_raw.items():
        if category not in categories:
            raise ConfigError(f"{context}: unknown mapping category '{category}'")
        mappings[category] = _parse_size_mapping(
            mapping_data, f"{context}.mappings.{category}"
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

    contact_sheet = None
    if "contact_sheet" in data and data["contact_sheet"] is not None:
        contact_sheet = _parse_contact_sheet(
            data["contact_sheet"],
            f"{context}.contact_sheet",
        )

    prefixes = _parse_prefixes(
        data.get("prefixes"),
        context,
    )

    return Destination(
        id=dest_id,
        path=Path(path_raw),
        format=fmt,
        mappings=mappings,
        webp_quality=webp_quality,
        thumbnails=thumbnails,
        contact_sheet=contact_sheet,
        prefixes=prefixes,
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
