"""Тесты core/image_optimization.py — оптимизация PIL/Pillow."""

import io

import pytest
from PIL import Image

from core.image_optimization import convert_to_webp, generate_thumbnails, optimize_image


def _make_image(size=(2000, 2000), mode="RGB", color=(255, 0, 0)):
    """Создать in-memory PNG/JPEG для тестов."""
    img = Image.new(mode, size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────
# optimize_image
# ─────────────────────────────────────────────────────────────────────


def test_optimize_image_shrinks_oversize():
    """Картинка больше max_size уменьшается через thumbnail."""
    src = _make_image(size=(3000, 3000))
    result = optimize_image(src, max_size=(1920, 1920))

    out = Image.open(result)
    assert max(out.size) <= 1920


def test_optimize_image_keeps_small_picture_size():
    """Меньше max_size — не растягивает."""
    src = _make_image(size=(500, 500))
    result = optimize_image(src, max_size=(1920, 1920))

    out = Image.open(result)
    # Pillow может не uпсайз'ить — должен быть точно тот же размер
    assert out.size == (500, 500)


def test_optimize_image_converts_rgba_to_rgb():
    """Прозрачный RGBA конвертируется в RGB (JPEG не поддерживает alpha)."""
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    result = optimize_image(buf)
    out = Image.open(result)
    assert out.mode == "RGB"


def test_optimize_image_returns_bytesio():
    """Возвращает BytesIO с JPEG-данными."""
    src = _make_image()
    result = optimize_image(src)
    assert isinstance(result, io.BytesIO)
    # Можно открыть как картинку
    out = Image.open(result)
    assert out.format == "JPEG"


# ─────────────────────────────────────────────────────────────────────
# convert_to_webp
# ─────────────────────────────────────────────────────────────────────


def test_convert_to_webp_format():
    """Результат — WebP."""
    src = _make_image()
    result = convert_to_webp(src)

    out = Image.open(result)
    assert out.format == "WEBP"


def test_convert_to_webp_preserves_dimensions():
    """Размер не меняется при конвертации."""
    src = _make_image(size=(640, 480))
    result = convert_to_webp(src)

    out = Image.open(result)
    assert out.size == (640, 480)


# ─────────────────────────────────────────────────────────────────────
# generate_thumbnails
# ─────────────────────────────────────────────────────────────────────


def test_generate_thumbnails_default_sizes():
    """Без sizes — генерирует 150/300/600."""
    src = _make_image(size=(1000, 1000))
    thumbs = generate_thumbnails(src)

    assert "150x150" in thumbs
    assert "300x300" in thumbs
    assert "600x600" in thumbs


def test_generate_thumbnails_custom_sizes():
    """С пользовательскими sizes — генерирует именно их."""
    src = _make_image(size=(1000, 1000))
    thumbs = generate_thumbnails(src, sizes=[(50, 50), (100, 200)])

    assert "50x50" in thumbs
    assert "100x200" in thumbs
    assert "150x150" not in thumbs


def test_generate_thumbnails_respects_max_size():
    """Размеры тумбнейлов не превышают заданные."""
    src = _make_image(size=(1000, 1000))
    thumbs = generate_thumbnails(src, sizes=[(150, 150)])

    out = Image.open(thumbs["150x150"])
    assert max(out.size) <= 150


def test_generate_thumbnails_returns_empty_on_error():
    """Битый input → пустой dict (с логом)."""
    broken = io.BytesIO(b"not an image")
    thumbs = generate_thumbnails(broken)
    assert thumbs == {}
