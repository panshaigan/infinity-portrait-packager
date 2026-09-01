from pathlib import Path

from PIL import Image

from portrait_packager.converter import (
    lookup_prefix,
    output_name,
    resize_exact,
    resize_max_side,
    save_image,
)


def test_output_name() -> None:
    assert output_name("portrait001", "L", "bmp") == "portrait001L.bmp"
    assert output_name("portrait001", "r", "webp") == "portrait001r.webp"


def test_output_name_with_prefix() -> None:
    assert output_name("bdimoen", "L", "webp", "z_sod_") == "z_sod_bdimoenL.webp"
    assert output_name("bdmain", "M", "bmp", "") == "bdmainM.bmp"


def test_lookup_prefix_case_insensitive() -> None:
    prefixes = {"bdimoen": "z_sod_"}
    assert lookup_prefix(prefixes, "BDIMOEN") == "z_sod_"
    assert lookup_prefix(prefixes, "bdimoen") == "z_sod_"
    assert lookup_prefix(prefixes, "unknown") == ""


def test_resize_exact_always_matches_target() -> None:
    image = Image.new("RGB", (840, 1320), color="red")
    result = resize_exact(image, 420, 660)

    assert result.size == (420, 660)


def test_resize_exact_upscales_small_image() -> None:
    image = Image.new("RGB", (100, 150), color="blue")
    result = resize_exact(image, 420, 660)

    assert result.size == (420, 660)


def test_resize_exact_stretches_non_matching_aspect() -> None:
    image = Image.new("RGB", (800, 400), color="green")
    result = resize_exact(image, 200, 200)

    assert result.size == (200, 200)


def test_save_bmp_is_24bit_rgb(tmp_path: Path) -> None:
    image = Image.new("RGBA", (10, 10), color=(255, 0, 0, 128))
    out_path = tmp_path / "testM.bmp"

    save_image(image, out_path, "bmp")

    with Image.open(out_path) as saved:
        assert saved.mode == "RGB"
        assert saved.format == "BMP"


def test_save_webp(tmp_path: Path) -> None:
    image = Image.new("RGB", (10, 10), color="yellow")
    out_path = tmp_path / "testL.webp"

    save_image(image, out_path, "webp", webp_quality=80)

    assert out_path.is_file()
    with Image.open(out_path) as saved:
        assert saved.format == "WEBP"


def test_resize_max_side_behavior() -> None:
    image = Image.new("RGB", (420, 660), color="white")
    thumb = resize_max_side(image, 105)

    assert thumb.size == (67, 105)
