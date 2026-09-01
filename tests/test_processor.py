from pathlib import Path

import yaml
from PIL import Image

from portrait_packager.config import load_config
from portrait_packager.processor import process_group


def write_config(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data), encoding="utf-8")


def make_test_image(path: Path, size: tuple[int, int] = (840, 1320)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color="red").save(path)


def build_fixture(tmp_path: Path) -> tuple[Config, str]:
    source_root = tmp_path / "source"
    group = "party_bg1"
    group_dir = source_root / group

    make_test_image(group_dir / "M" / "portrait001.png")
    make_test_image(group_dir / "L" / "portrait001.png")
  # category r intentionally missing

    dest_bmp = tmp_path / "out" / "game"
    dest_webp = tmp_path / "out" / "web"

    config_data = {
        "sources": {"root": str(source_root)},
        "categories": ["M", "L", "r"],
        "destinations": [
            {
                "id": "game_bmp",
                "path": str(dest_bmp),
                "format": "bmp",
                "mappings": {
                    "M": {"width": 210, "height": 330},
                    "L": {"width": 420, "height": 660},
                    "r": {"width": 84, "height": 132},
                },
                "thumbnails": {"max_size": 105},
            },
            {
                "id": "web_preview",
                "path": str(dest_webp),
                "format": "webp",
                "mappings": {
                    "M": {"width": 105, "height": 165},
                    "L": {"width": 210, "height": 330},
                    "r": {"width": 42, "height": 66},
                },
            },
        ],
    }

    config_path = tmp_path / "config.yaml"
    write_config(config_path, config_data)
    return load_config(config_path), group


def test_process_group_writes_outputs(tmp_path: Path) -> None:
    config, group = build_fixture(tmp_path)

    result = process_group(config, group)

    assert result.ok
    assert result.files_written == 4
    assert result.thumbs_written == 2
    assert len(result.warnings) == 2

    bmp_dest = config.destinations[0].path
    assert (bmp_dest / "portrait001M.bmp").is_file()
    assert (bmp_dest / "portrait001L.bmp").is_file()
    assert (bmp_dest / "thumbs" / "portrait001M.bmp").is_file()
    assert (bmp_dest / "thumbs" / "portrait001L.bmp").is_file()

    webp_dest = config.destinations[1].path
    assert (webp_dest / "portrait001M.webp").is_file()
    assert (webp_dest / "portrait001L.webp").is_file()
    assert not (webp_dest / "thumbs").exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    config, group = build_fixture(tmp_path)

    result = process_group(config, group, dry_run=True)

    assert result.ok
    assert result.files_written == 4
    assert not config.destinations[0].path.exists()


def test_missing_group_returns_error(tmp_path: Path) -> None:
    config, _ = build_fixture(tmp_path)

    result = process_group(config, "missing_group")

    assert not result.ok
    assert any("Portrait group not found" in error for error in result.errors)


def test_dest_filter(tmp_path: Path) -> None:
    config, group = build_fixture(tmp_path)

    result = process_group(config, group, dest_filter="game_bmp")

    assert result.ok
    assert result.files_written == 2
    assert config.destinations[0].path.exists()
    assert not config.destinations[1].path.exists()
