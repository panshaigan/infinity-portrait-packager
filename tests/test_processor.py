from pathlib import Path

import yaml
from PIL import Image

from portrait_packager.config import Config, load_config
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

    make_test_image(group_dir / "M" / "port001.png")
    make_test_image(group_dir / "L" / "port001.png")
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

    bmp_dest = config.destinations[0].path / group
    assert (bmp_dest / "PORT001M.bmp").is_file()
    assert (bmp_dest / "PORT001L.bmp").is_file()
    assert (bmp_dest / "thumbs" / "PORT001M.bmp").is_file()
    assert (bmp_dest / "thumbs" / "PORT001L.bmp").is_file()

    webp_dest = config.destinations[1].path / group
    assert (webp_dest / "PORT001M.webp").is_file()
    assert (webp_dest / "PORT001L.webp").is_file()
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
    assert (config.destinations[0].path / group).exists()
    assert not (config.destinations[1].path / group).exists()


def test_skips_unmapped_categories(tmp_path: Path) -> None:
    config, group = build_fixture(tmp_path)
    # web_preview only maps L in this test config
    config_data = {
        "sources": {"root": str(config.sources_root)},
        "categories": ["M", "L", "r"],
        "destinations": [
            {
                "id": "l_only",
                "path": str(tmp_path / "out" / "lonly"),
                "format": "bmp",
                "mappings": {"L": {"width": 420, "height": 660}},
            }
        ],
    }
    write_config(tmp_path / "lonly.yaml", config_data)
    lonly_config = load_config(tmp_path / "lonly.yaml")

    result = process_group(lonly_config, group)

    assert result.ok
    assert result.files_written == 1
    dest = lonly_config.destinations[0].path / group
    assert (dest / "PORT001L.bmp").is_file()
    assert not (dest / "PORT001M.bmp").exists()


def test_applies_filename_prefix(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    group = "party_bg1"
    make_test_image(source_root / group / "L" / "bdimoen.png")
    make_test_image(source_root / group / "L" / "bdmain.png")

    config_data = {
        "sources": {"root": str(source_root)},
        "categories": ["M", "L", "r"],
        "destinations": [
            {
                "id": "prefixed",
                "path": str(tmp_path / "out"),
                "format": "bmp",
                "mappings": {"L": {"width": 420, "height": 660}},
                "prefixes": {"bdimoen": "z_sod_"},
            }
        ],
    }
    write_config(tmp_path / "prefix.yaml", config_data)
    prefix_config = load_config(tmp_path / "prefix.yaml")

    result = process_group(prefix_config, group)

    assert result.ok
    assert result.files_written == 2
    dest = prefix_config.destinations[0].path / group
    assert (dest / "z_sod_BDIMOENL.bmp").is_file()
    assert (dest / "BDMAINL.bmp").is_file()


def test_normalizes_stem_case_by_category(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    group = "party_bg1"
    make_test_image(source_root / group / "L" / "Nalia.png")
    make_test_image(source_root / group / "M" / "nalia.png")
    make_test_image(source_root / group / "r" / "NALIA.png")

    config_data = {
        "sources": {"root": str(source_root)},
        "categories": ["M", "L", "r"],
        "destinations": [
            {
                "id": "game_bmp",
                "path": str(tmp_path / "out"),
                "format": "bmp",
                "mappings": {
                    "M": {"width": 210, "height": 330},
                    "L": {"width": 420, "height": 660},
                    "r": {"width": 84, "height": 132},
                },
            }
        ],
    }
    write_config(tmp_path / "case.yaml", config_data)
    config = load_config(tmp_path / "case.yaml")

    result = process_group(config, group)

    assert result.ok
    assert result.files_written == 3
    assert not any("missing from categories" in w for w in result.warnings)
    dest = config.destinations[0].path / group
    assert (dest / "NALIAL.bmp").is_file()
    assert (dest / "NALIAM.bmp").is_file()
    assert (dest / "naliar.bmp").is_file()


def test_warns_on_long_source_stem(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    group = "party_bg1"
    make_test_image(source_root / group / "L" / "toolongname.png")
    make_test_image(source_root / group / "M" / "toolongname.png")
    make_test_image(source_root / group / "r" / "toolongname.png")

    config_data = {
        "sources": {"root": str(source_root)},
        "categories": ["M", "L", "r"],
        "destinations": [
            {
                "id": "game_bmp",
                "path": str(tmp_path / "out"),
                "format": "bmp",
                "mappings": {
                    "M": {"width": 210, "height": 330},
                    "L": {"width": 420, "height": 660},
                    "r": {"width": 84, "height": 132},
                },
            }
        ],
    }
    write_config(tmp_path / "long.yaml", config_data)
    config = load_config(tmp_path / "long.yaml")

    result = process_group(config, group)

    assert result.ok
    long_warnings = [
        w for w in result.warnings if "longer than 7 characters" in w
    ]
    assert len(long_warnings) == 3
    assert any("L/toolongname.png" in w for w in long_warnings)


def test_warns_when_stem_missing_from_category(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    group = "party_bg1"
    make_test_image(source_root / group / "L" / "nalia.png")
    make_test_image(source_root / group / "M" / "nalia.png")
    make_test_image(source_root / group / "L" / "imoen.png")
    make_test_image(source_root / group / "r" / "nalia.png")
    # imoen missing from M and r

    config_data = {
        "sources": {"root": str(source_root)},
        "categories": ["M", "L", "r"],
        "destinations": [
            {
                "id": "game_bmp",
                "path": str(tmp_path / "out"),
                "format": "bmp",
                "mappings": {
                    "M": {"width": 210, "height": 330},
                    "L": {"width": 420, "height": 660},
                    "r": {"width": 84, "height": 132},
                },
            }
        ],
    }
    write_config(tmp_path / "missing.yaml", config_data)
    config = load_config(tmp_path / "missing.yaml")

    result = process_group(config, group)

    assert result.ok
    missing = [w for w in result.warnings if "missing from categories" in w]
    assert len(missing) == 1
    assert "imoen" in missing[0]
    assert "M" in missing[0] and "r" in missing[0]
    assert "present in: L" in missing[0]
