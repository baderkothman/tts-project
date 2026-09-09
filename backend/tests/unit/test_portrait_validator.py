"""Unit tests for portrait upload validation. Face *detection* is
monkeypatched (`_detect_faces`) throughout — see the module's own docstring
for why a Haar cascade's real accuracy on a synthetic test image isn't what
these tests are checking; everything else (format/size/corruption/face-count/
face-size logic) is exercised for real."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from backend.app.services import portrait_validator as pv

_MAX_BYTES = 8 * 1024 * 1024


def _png_bytes(size: tuple[int, int] = (400, 400)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (180, 140, 110)).save(buf, format="PNG")
    return buf.getvalue()


def test_rejects_unsupported_content_type():
    with pytest.raises(pv.PortraitValidationError) as exc_info:
        pv.validate_portrait(_png_bytes(), content_type="image/gif", max_bytes=_MAX_BYTES)
    assert exc_info.value.kind == "unsupported_format"


def test_rejects_oversized_file():
    data = _png_bytes()
    with pytest.raises(pv.PortraitValidationError) as exc_info:
        pv.validate_portrait(data, content_type="image/png", max_bytes=len(data) - 1)
    assert exc_info.value.kind == "file_too_large"


def test_rejects_corrupted_image():
    with pytest.raises(pv.PortraitValidationError) as exc_info:
        pv.validate_portrait(b"not a real image", content_type="image/png", max_bytes=_MAX_BYTES)
    assert exc_info.value.kind == "corrupted"


def test_rejects_resolution_too_low():
    with pytest.raises(pv.PortraitValidationError) as exc_info:
        pv.validate_portrait(_png_bytes((100, 100)), content_type="image/png", max_bytes=_MAX_BYTES)
    assert exc_info.value.kind == "resolution_too_low"


def test_rejects_resolution_too_high_without_fully_decoding(monkeypatch):
    # A real decompression-bomb guard: the dimension check must reject
    # before `.convert("RGB")` would fully decode pixel data. Verified here
    # by making a full decode explode if it's ever reached — the test fails
    # loudly (not just silently slow) if that ordering regresses.
    from PIL import Image as PILImage

    original_convert = PILImage.Image.convert

    def exploding_convert(self, *args, **kwargs):
        if args and args[0] == "RGB":
            raise AssertionError("full pixel decode was reached — dimension check ran too late")
        return original_convert(self, *args, **kwargs)

    monkeypatch.setattr(PILImage.Image, "convert", exploding_convert)
    with pytest.raises(pv.PortraitValidationError) as exc_info:
        pv.validate_portrait(_png_bytes((7000, 7000)), content_type="image/png", max_bytes=50 * 1024 * 1024)
    assert exc_info.value.kind == "resolution_too_low"


def test_rejects_no_face_detected(monkeypatch):
    monkeypatch.setattr(pv, "_detect_faces", lambda gray: [])
    with pytest.raises(pv.PortraitValidationError) as exc_info:
        pv.validate_portrait(_png_bytes(), content_type="image/png", max_bytes=_MAX_BYTES)
    assert exc_info.value.kind == "no_face"


def test_rejects_multiple_faces_detected(monkeypatch):
    monkeypatch.setattr(pv, "_detect_faces", lambda gray: [(10, 10, 100, 100), (200, 200, 100, 100)])
    with pytest.raises(pv.PortraitValidationError) as exc_info:
        pv.validate_portrait(_png_bytes(), content_type="image/png", max_bytes=_MAX_BYTES)
    assert exc_info.value.kind == "multiple_faces"


def test_rejects_face_too_small(monkeypatch):
    # 400x400 image, a 20x20 "face" is well under MIN_FACE_FRACTION (0.12) of 400.
    monkeypatch.setattr(pv, "_detect_faces", lambda gray: [(10, 10, 20, 20)])
    with pytest.raises(pv.PortraitValidationError) as exc_info:
        pv.validate_portrait(_png_bytes(), content_type="image/png", max_bytes=_MAX_BYTES)
    assert exc_info.value.kind == "face_too_small"


def test_accepts_a_valid_portrait(monkeypatch):
    monkeypatch.setattr(pv, "_detect_faces", lambda gray: [(100, 80, 200, 200)])
    result = pv.validate_portrait(_png_bytes(), content_type="image/png", max_bytes=_MAX_BYTES)
    assert result.width == 400
    assert result.height == 400
    assert result.format == "png"
    assert result.face_box == (100, 80, 200, 200)
    assert result.normalized_png_bytes.startswith(b"\x89PNG")


def test_normalizes_jpeg_and_webp_to_png_bytes(monkeypatch):
    monkeypatch.setattr(pv, "_detect_faces", lambda gray: [(100, 80, 200, 200)])
    for content_type, fmt in [("image/jpeg", "JPEG"), ("image/webp", "WEBP")]:
        buf = io.BytesIO()
        Image.new("RGB", (400, 400), (180, 140, 110)).save(buf, format=fmt)
        result = pv.validate_portrait(buf.getvalue(), content_type=content_type, max_bytes=_MAX_BYTES)
        assert result.normalized_png_bytes.startswith(b"\x89PNG")
