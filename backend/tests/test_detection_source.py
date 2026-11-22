"""The add form has to know which detector answered, so it can warn the user."""

import time

import pytest

from app.modules.ai.gemini_service import GeminiVisionService, gemini_service
from app.modules.wardrobe import service as wardrobe


@pytest.fixture
def local_models(monkeypatch):
    monkeypatch.setattr(
        wardrobe.ai_service,
        "extract_clothing_metadata",
        lambda file_bytes, filename: {"type": "jacket", "primary_color": "gold", "pattern": "geometric"},
    )
    monkeypatch.setattr(wardrobe, "_classify", lambda _: ("formal", 0.9, {}, "classifier-v3"))


@pytest.mark.asyncio
async def test_gemini_answer_is_labelled(monkeypatch, local_models):
    monkeypatch.setattr(GeminiVisionService, "is_configured", property(lambda self: True))

    async def fake_detect(**_):
        return {"name": "Silk Kurta", "type": "kurta", "model_version": "gemini-x"}

    monkeypatch.setattr(gemini_service, "detect_clothing_item", fake_detect)
    result = await wardrobe.wardrobe_service.detect_item_metadata(b"img", "kurta.jpg")
    assert result["detected_by"] == "gemini"


@pytest.mark.asyncio
async def test_quota_fallback_says_so(monkeypatch, local_models):
    monkeypatch.setattr(GeminiVisionService, "is_configured", property(lambda self: True))

    async def quota_hit(**_):
        gemini_service._paused_until = time.monotonic() + 60
        return None

    monkeypatch.setattr(gemini_service, "detect_clothing_item", quota_hit)
    try:
        result = await wardrobe.wardrobe_service.detect_item_metadata(b"img", "kurta.jpg")
    finally:
        gemini_service._paused_until = 0.0
    assert result["detected_by"] == "backup"
    assert result["backup_reason"] == "quota"


@pytest.mark.asyncio
async def test_unconfigured_gemini_is_reported(monkeypatch, local_models):
    monkeypatch.setattr(GeminiVisionService, "is_configured", property(lambda self: False))
    result = await wardrobe.wardrobe_service.detect_item_metadata(b"img", "kurta.jpg")
    assert result["detected_by"] == "backup"
    assert result["backup_reason"] == "not_configured"


def test_saved_item_records_gemini_not_the_classifier():
    assert wardrobe._from_gemini({"detected_by": "gemini"})
    assert wardrobe._from_gemini({"model_version": "gemini-2.5-flash"})
    assert not wardrobe._from_gemini({"detected_by": "backup", "model_version": "classifier-v3"})
    assert not wardrobe._from_gemini(None)
