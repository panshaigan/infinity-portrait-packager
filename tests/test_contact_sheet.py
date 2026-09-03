from pathlib import Path

import pytest
import yaml
from PIL import Image

from portrait_packager.config import ConfigError, load_config
from portrait_packager.converter import build_contact_sheet, resize_to_width
from portrait_packager.processor import process_group


def write_config(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data), encoding="utf-8")


def make_test_image(path: Path, size: tuple[int, int], color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path)


def test_contact_sheet_config_parsed(tmp_path: Path) -> None:
    config_data = {
        "sources": {"root": "/tmp/source"},
        "categories": ["M", "L"],
        "destinations": [
            {
                "id": "web",
                "path": "/tmp/out/web",
                "format": "webp",
                "mappings": {"L": {"width": 100, "height": 200}},
                "contact_sheet": {
                    "width": 1200,
                    "thumb_width": 800,
                    "cols": {"party_bg1": 9},
                    "path": "/tmp/out/sheets",
                },
            }
        ],
    }
    config_path = tmp_path / "config.yaml"
    write_config(config_path, config_data)

    config = load_config(config_path)
    sheet = config.destinations[0].contact_sheet

    assert sheet is not None
    assert sheet.width == 1200
    assert sheet.thumb_width == 800
    assert sheet.cols == {"party_bg1": 9}
    assert sheet.path == Path("/tmp/out/sheets")


def test_contact_sheet_config_rejects_missing_fields(tmp_path: Path) -> None:
    config_data = {
        "sources": {"root": "/tmp/source"},
        "categories": ["L"],
        "destinations": [
            {
                "id": "web",
                "path": "/tmp/out/web",
                "format": "webp",
                "mappings": {"L": {"width": 100, "height": 200}},
                "contact_sheet": {"width": 1200, "path": "/tmp/out/sheets"},
            }
        ],
    }
    config_path = tmp_path / "config.yaml"
    write_config(config_path, config_data)

    with pytest.raises(ConfigError, match="missing required fields"):
        load_config(config_path)


def test_build_contact_sheet_layout(tmp_path: Path) -> None:
    colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255))
    paths = []
    for index, color in enumerate(colors):
        path = tmp_path / f"portrait{index:03d}L.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 20), color=color).save(path)
        paths.append(path)

    sheet = build_contact_sheet(paths, cols=2)

    assert sheet.size == (21, 41)
    assert sheet.getpixel((10, 0)) == (0, 0, 0)
    assert sheet.getpixel((0, 0)) == colors[0]
    assert sheet.getpixel((11, 0)) == colors[1]
    assert sheet.getpixel((0, 21)) == colors[2]


def test_resize_to_width() -> None:
    image = Image.new("RGB", (100, 50), color="white")
    resized = resize_to_width(image, 200)

    assert resized.size == (200, 100)


def test_process_group_writes_contact_sheets(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    group = "party_bg1"
    group_dir = source_root / group
    make_test_image(group_dir / "M" / "portrait001.png", (840, 1320), "red")
    make_test_image(group_dir / "M" / "portrait002.png", (840, 1320), "blue")
    make_test_image(group_dir / "L" / "portrait001.png", (840, 1320), "green")

    dest_webp = tmp_path / "out" / "web"
    sheet_dir = tmp_path / "out" / "sheets"
    config_data = {
        "sources": {"root": str(source_root)},
        "categories": ["M", "L", "r"],
        "destinations": [
            {
                "id": "web_preview",
                "path": str(dest_webp),
                "format": "webp",
                "mappings": {
                    "M": {"width": 42, "height": 66},
                    "L": {"width": 42, "height": 66},
                },
                "contact_sheet": {
                    "width": 120,
                    "thumb_width": 80,
                    "cols": {"party_bg1": 2},
                    "path": str(sheet_dir),
                },
            }
        ],
    }
    config_path = tmp_path / "config.yaml"
    write_config(config_path, config_data)
    config = load_config(config_path)

    result = process_group(config, group, verbose=True)

    assert result.ok
    assert result.contact_sheets_written == 2

    sheet_m = sheet_dir / f"{group}_M.webp"
    thumb_m = sheet_dir / f"{group}_M_thumb.webp"
    sheet_l = sheet_dir / f"{group}_L.webp"
    thumb_l = sheet_dir / f"{group}_L_thumb.webp"

    assert sheet_m.is_file()
    assert thumb_m.is_file()
    assert sheet_l.is_file()
    assert thumb_l.is_file()

    with Image.open(sheet_m) as image:
        assert image.format == "WEBP"
        assert image.width == 120
    with Image.open(thumb_m) as image:
        assert image.width == 80


def test_contact_sheet_missing_group_cols(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    group = "party_bg1"
    make_test_image(source_root / group / "L" / "portrait001.png", (840, 1320), "red")

    config_data = {
        "sources": {"root": str(source_root)},
        "categories": ["L"],
        "destinations": [
            {
                "id": "web_preview",
                "path": str(tmp_path / "out" / "web"),
                "format": "webp",
                "mappings": {"L": {"width": 42, "height": 66}},
                "contact_sheet": {
                    "width": 120,
                    "thumb_width": 80,
                    "cols": {"party_bg2": 6},
                    "path": str(tmp_path / "out" / "sheets"),
                },
            }
        ],
    }
    config_path = tmp_path / "config.yaml"
    write_config(config_path, config_data)
    config = load_config(config_path)

    result = process_group(config, group)

    assert not result.ok
    assert any("no entry for group 'party_bg1'" in error for error in result.errors)


def test_cols_override(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    group = "party_bg1"
    group_dir = source_root / group
    for index in range(3):
        make_test_image(
            group_dir / "L" / f"portrait{index:03d}.png",
            (840, 1320),
            "red",
        )

    sheet_dir = tmp_path / "out" / "sheets"
    config_data = {
        "sources": {"root": str(source_root)},
        "categories": ["L"],
        "destinations": [
            {
                "id": "web_preview",
                "path": str(tmp_path / "out" / "web"),
                "format": "webp",
                "mappings": {"L": {"width": 10, "height": 20}},
                "contact_sheet": {
                    "width": 120,
                    "thumb_width": 80,
                    "cols": {"party_bg1": 2},
                    "path": str(sheet_dir),
                },
            }
        ],
    }
    config_path = tmp_path / "config.yaml"
    write_config(config_path, config_data)
    config = load_config(config_path)

    result = process_group(config, group, cols_override=3)

    assert result.ok
    with Image.open(sheet_dir / f"{group}_L.webp") as image:
        # 3 cols x 10px + 2 gaps = 32px before resize to width 120
        assert image.width == 120
