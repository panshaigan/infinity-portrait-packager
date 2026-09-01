from pathlib import Path

from PIL import Image

from portrait_packager.converter import output_name, resize_fit, save_image


def test_output_name() -> None:
    assert output_name("portrait001", "L", "bmp") == "portrait001L.bmp"
    assert output_name("portrait001", "r", "webp") == "portrait001r.webp"


def test_resize_fit_downscales_large_image() -> None:
    image = Image.new("RGB", (840, 1320), color="red")
    result = resize_fit(image, 420, 660)

    assert result.size == (420, 660)


def test_resize_fit_does_not_upscale() -> None:
    image = Image.new("RGB", (100, 150), color="blue")
    result = resize_fit(image, 420, 660)

    assert result.size == (100, 150)


def test_resize_fit_preserves_aspect_ratio() -> None:
    image = Image.new("RGB", (800, 400), color="green")
    result = resize_fit(image, 200, 200)

    assert result.size == (200, 100)


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


def test_thumbnail_max_size_behavior() -> None:
    image = Image.new("RGB", (420, 660), color="white")
    thumb = resize_fit(image, 105, 105)

    assert thumb.size == (67, 105)
