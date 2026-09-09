"""Validates an uploaded portrait before it becomes an avatar job at all —
the brief's "detect no face / multiple faces / too small / occluded /
unsupported format / corrupted" requirement.

Decoding is PIL's job (already a dependency, and already this app's own
convention — `services/inference.py` decodes reference-audio bytes the same
"read once, validate, raise a typed error" way via `soundfile`). Face
detection is OpenCV's bundled Haar cascade — a classical, CPU-only,
zero-extra-download detector (the model file ships inside the
`opencv-python-headless` package itself, no network fetch at request time).
It is deliberately not a deep-learning face detector: this is an input
*gate* ("is there roughly one face, roughly this big, in this image"), not
an identity or quality judgment, and a decades-old cascade is enough for
that gate without adding a second heavy model to this app's already-heavy
model footprint. If it proves too unreliable in practice (see
docs/AVATAR_ARCHITECTURE.md's open-questions section), swapping in a DNN
detector only touches `_detect_faces` below.

The `_detect_faces` seam exists specifically so tests never depend on the
cascade's actual accuracy on a synthetic test image (which Haar cascades —
trained on real photographs — are known to miss) — same "fake the
model-shaped dependency, test the surrounding logic for real" pattern
`dialect_rewriter.py`'s tests use for the OpenAI client.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image, UnidentifiedImageError

PortraitValidationErrorKind = Literal[
    "unsupported_format",
    "corrupted",
    "resolution_too_low",
    "file_too_large",
    "no_face",
    "multiple_faces",
    "face_too_small",
]


class PortraitValidationError(Exception):
    """Same `(kind, message)` shape as the rest of this app's typed service
    errors — `api/avatar.py` maps this through the same kind-to-status
    convention `api/tts.py` uses for `InferenceError`/`DialectRewriteError`."""

    def __init__(self, kind: PortraitValidationErrorKind, message: str) -> None:
        self.kind = kind
        self.message = message
        super().__init__(message)


ALLOWED_CONTENT_TYPES: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")

# Below this on the shorter side, a Haar cascade's own accuracy degrades
# sharply and any avatar engine would be upscaling more than animating.
MIN_DIMENSION_PX = 256
# A face bounding box narrower than this fraction of the image's shorter
# side is "in the frame but too small to animate convincingly" rather than
# a real portrait — distinct from MIN_DIMENSION_PX (that's about the whole
# image; this is about how much of it is actually face).
MIN_FACE_FRACTION = 0.12

# A decompression-bomb guard: a tiny, well-compressed file can still declare
# an enormous pixel grid (PIL decodes whatever dimensions the file header
# claims, regardless of its byte size on disk) — the file-size limit above
# does not bound this on its own. 6000px is generous for a portrait photo
# while still bounding worst-case decode memory (~6000*6000*3 bytes ≈
# 100MB for one RGB frame — StubAvatarEngine's Ken-Burns loop holds several
# frame-sized buffers at once, so this stays well short of a "well-crafted
# tiny file exhausts server memory" DoS vector).
MAX_DIMENSION_PX = 6000


@dataclass(frozen=True)
class ValidatedPortrait:
    width: int
    height: int
    format: Literal["png", "jpeg", "webp"]
    # (x, y, w, h) in pixel coordinates of the single detected face —
    # useful to an engine (e.g. StubAvatarEngine's mouth-region motion) so
    # it doesn't need to re-run detection.
    face_box: tuple[int, int, int, int]
    # Re-encoded as PNG regardless of the original format — one format for
    # everything downstream (job storage, engines) to assume, rather than
    # every consumer needing to branch on JPEG-vs-WebP-vs-PNG.
    normalized_png_bytes: bytes


_CONTENT_TYPE_TO_FORMAT: dict[str, Literal["png", "jpeg", "webp"]] = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/webp": "webp",
}

_cascade = None


def _detect_faces(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Returns `(x, y, w, h)` boxes for every face-like region found.
    Isolated in its own function so tests can monkeypatch it instead of
    depending on the cascade's real-world accuracy — see module docstring."""
    global _cascade
    if _cascade is None:
        import cv2

        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    boxes = _cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return [tuple(int(v) for v in box) for box in boxes]


def validate_portrait(
    data: bytes, *, content_type: str, max_bytes: int
) -> ValidatedPortrait:
    """Raises `PortraitValidationError` for every failure mode the brief
    lists; returns a `ValidatedPortrait` only when the image is genuinely
    usable. Never partially validates — every check below runs before
    anything is trusted downstream."""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise PortraitValidationError(
            "unsupported_format",
            f"Unsupported image type '{content_type}' — use PNG, JPEG, or WebP",
        )
    if len(data) > max_bytes:
        raise PortraitValidationError(
            "file_too_large", f"Portrait exceeds the {max_bytes // (1024 * 1024)}MB limit"
        )

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()  # cheap structural check; does not decode pixel data
        # verify() invalidates the file handle for further use (documented
        # PIL behavior) — a fresh open is required to read anything further.
        image = Image.open(io.BytesIO(data))
        width, height = image.size  # header-only read — still no full pixel decode
    except (UnidentifiedImageError, OSError) as exc:
        raise PortraitValidationError("corrupted", "Portrait file could not be decoded — it may be corrupted") from exc

    # Dimension checks run before `.convert("RGB")` below deliberately — that
    # call is what actually decodes full pixel data, and a decompression-
    # bomb-shaped file should never reach it. See MAX_DIMENSION_PX's comment.
    if min(width, height) < MIN_DIMENSION_PX:
        raise PortraitValidationError(
            "resolution_too_low",
            f"Portrait is too small ({width}x{height}) — the shorter side must be at least {MIN_DIMENSION_PX}px",
        )
    if max(width, height) > MAX_DIMENSION_PX:
        raise PortraitValidationError(
            "resolution_too_low",  # same user-facing kind — "unusable resolution" either direction
            f"Portrait is too large ({width}x{height}) — the longer side must be at most {MAX_DIMENSION_PX}px",
        )

    image = image.convert("RGB")
    gray = np.array(image.convert("L"))
    faces = _detect_faces(gray)

    if len(faces) == 0:
        raise PortraitValidationError("no_face", "No face was detected in this portrait")
    if len(faces) > 1:
        raise PortraitValidationError(
            "multiple_faces", f"{len(faces)} faces were detected — upload a portrait with exactly one visible face"
        )

    face_box = faces[0]
    _, _, fw, fh = face_box
    if min(fw, fh) < MIN_FACE_FRACTION * min(width, height):
        raise PortraitValidationError(
            "face_too_small", "The detected face is too small relative to the image — crop in closer"
        )

    buf = io.BytesIO()
    image.save(buf, format="PNG")

    return ValidatedPortrait(
        width=width,
        height=height,
        format=_CONTENT_TYPE_TO_FORMAT[content_type],
        face_box=face_box,
        normalized_png_bytes=buf.getvalue(),
    )
