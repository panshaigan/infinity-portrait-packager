from pathlib import Path

import pytest
import yaml

from portrait_packager.config import ConfigError, load_config


def write_config(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data), encoding="utf-8")


def minimal_config(**overrides) -> dict:
    config = {
        "sources": {"root": "/tmp/source"},
        "categories": ["M", "L", "r"],
        "destinations": [
            {
                "id": "game_bmp",
                "path": "/tmp/out/game",
                "format": "bmp",
                "mappings": {
                    "M": {"width": 210, "height": 330},
                    "L": {"width": 420, "height": 660},
                    "r": {"width": 84, "height": 132},
                },
            }
        ],
    }
    config.update(overrides)
    return config


def test_load_valid_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_config(config_path, minimal_config())

    config = load_config(config_path)

    assert config.sources_root == Path("/tmp/source")
    assert config.categories == ["M", "L", "r"]
    assert len(config.destinations) == 1
    assert config.destinations[0].id == "game_bmp"
    assert config.destinations[0].format == "bmp"
    assert config.destinations[0].mappings["L"].width == 420


def test_missing_mapping_for_category(tmp_path: Path) -> None:
    data = minimal_config()
    del data["destinations"][0]["mappings"]["r"]
    config_path = tmp_path / "config.yaml"
    write_config(config_path, data)

    with pytest.raises(ConfigError, match="missing mapping for category 'r'"):
        load_config(config_path)


def test_invalid_format(tmp_path: Path) -> None:
    data = minimal_config()
    data["destinations"][0]["format"] = "gif"
    config_path = tmp_path / "config.yaml"
    write_config(config_path, data)

    with pytest.raises(ConfigError, match="format must be one of"):
        load_config(config_path)


def test_thumbnail_requires_max_size(tmp_path: Path) -> None:
    data = minimal_config()
    data["destinations"][0]["thumbnails"] = {"width": 105, "height": 165}
    config_path = tmp_path / "config.yaml"
    write_config(config_path, data)

    with pytest.raises(ConfigError, match="thumbnails must define max_size"):
        load_config(config_path)


def test_thumbnail_rejects_extra_keys(tmp_path: Path) -> None:
    data = minimal_config()
    data["destinations"][0]["thumbnails"] = {"max_size": 105, "format": "bmp"}
    config_path = tmp_path / "config.yaml"
    write_config(config_path, data)

    with pytest.raises(ConfigError, match="only supports max_size"):
        load_config(config_path)


def test_webp_quality_out_of_range(tmp_path: Path) -> None:
    data = minimal_config()
    data["destinations"][0]["format"] = "webp"
    data["destinations"][0]["webp_quality"] = 200
    config_path = tmp_path / "config.yaml"
    write_config(config_path, data)

    with pytest.raises(ConfigError, match="webp_quality must be between"):
        load_config(config_path)


def test_duplicate_destination_ids(tmp_path: Path) -> None:
    data = minimal_config()
    data["destinations"].append(data["destinations"][0].copy())
    config_path = tmp_path / "config.yaml"
    write_config(config_path, data)

    with pytest.raises(ConfigError, match="duplicate destination id"):
        load_config(config_path)
