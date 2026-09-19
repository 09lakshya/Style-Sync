import io

import numpy as np
from PIL import Image

from app.modules.ai.preprocessor import preprocessor
from app.modules.ai.subject_detector import SubjectDetector, subject_detector


def _image_bytes(colour=(200, 60, 120), size=(256, 256)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, colour)
    # A flat image gives CLAHE nothing to do, so add structure.
    px = img.load()
    for x in range(size[0]):
        for y in range(0, size[1], 8):
            px[x, y] = (colour[0] // 2, colour[1] // 2, colour[2] // 2)
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_enhance_override_changes_the_image():
    """Colour is read from the un-enhanced variant, so the override must work."""
    raw = _image_bytes()
    enhanced = np.asarray(preprocessor.preprocess_for_clip(raw, enhance=True), dtype=int)
    plain = np.asarray(preprocessor.preprocess_for_clip(raw, enhance=False), dtype=int)
    assert enhanced.shape == plain.shape
    assert not np.array_equal(enhanced, plain), "enhance=False still applied CLAHE"


def test_enhance_default_matches_enhanced():
    raw = _image_bytes()
    default = np.asarray(preprocessor.preprocess_for_clip(raw), dtype=int)
    enhanced = np.asarray(preprocessor.preprocess_for_clip(raw, enhance=True), dtype=int)
    assert np.array_equal(default, enhanced)


def test_crop_gate_stays_conservative():
    """Cropping normally framed photos measurably hurt accuracy (0.575 -> 0.475).

    The gate exists so only full-scene shots are cropped. Loosening it without
    re-measuring would reintroduce that regression.
    """
    from app.modules.ai import subject_detector as module

    assert module.MAX_COVERAGE_TO_CROP <= 0.30


def test_crop_falls_back_to_full_frame_when_detector_unavailable():
    detector = SubjectDetector()
    detector._load_failed = True  # simulate torchvision/model unavailable
    img = Image.new("RGB", (128, 128), (10, 20, 30))
    out, info = detector.crop_to_subject(img)
    assert out is img
    assert info["cropped"] is False
    assert info["reason"]


def test_crop_returns_info_shape():
    """Callers branch on these keys; they must always be present."""
    detector = SubjectDetector()
    detector._load_failed = True
    _, info = detector.crop_to_subject(Image.new("RGB", (64, 64)))
    for key in ("cropped", "reason", "coverage", "score"):
        assert key in info


def test_singleton_is_a_subject_detector():
    assert isinstance(subject_detector, SubjectDetector)
