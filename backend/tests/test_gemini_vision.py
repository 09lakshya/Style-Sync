import asyncio
import io
import json
import pytest
from PIL import Image
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
from app.modules.ai.gemini_service import gemini_service
from app.modules.recommendations.service import outfit_analysis_service


def _sample_image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color="navy").save(buffer, format="JPEG")
    return buffer.getvalue()


MOCK_GEMINI_OUTPUT = {
    "aesthetic": "Old Money / Quiet Luxury",
    "category": "Formal",
    "outfit_score": 92,
    "summary": "An impeccably tailored navy blazer paired with cream trousers.",
    "detected_pieces": [
        {
            "slot": "outerwear",
            "name": "Navy hopsack tailored blazer",
            "color": "navy",
            "pattern": "solid",
            "details": "Double-vented, horn buttons",
        },
        {
            "slot": "bottom",
            "name": "Cream pleated wool trousers",
            "color": "cream",
            "pattern": "solid",
            "details": "High-rise, cuffed hem",
        },
    ],
    "color_palette": {
        "primary_color": "navy",
        "secondary_colors": ["cream", "brown"],
        "color_chips": [
            {"name": "Navy Blue", "hex": "#1B2A4A"},
            {"name": "Cream", "hex": "#F5F2EB"},
        ],
        "harmony_type": "Neutral Contrast",
        "harmony_evaluation": "Timeless coastal prep contrast.",
    },
    "silhouette_and_proportions": {
        "fit": "Structured",
        "evaluation": "Broadened shoulders balanced by high-waisted trousers.",
    },
    "occasions": ["Cocktails", "Business Casual", "Gallery Opening"],
    "seasons": ["Spring", "Autumn"],
    "gender": "male",
    "stylist_critique": {
        "strengths": ["Flawless color harmony", "High quality tailoring"],
        "elevation_tips": ["Add a silk printed pocket square", "Pair with dark brown suede loafers"],
    },
    "styling_recommendations": {
        "footwear": ["Dark brown suede penny loafers", "Oxblood derbies"],
        "bag": ["Vintage leather attache case"],
        "jewellery_and_watches": ["Gold dress watch with alligator leather strap"],
        "layers_and_outerwear": ["Cashmere scarf in camel"],
        "other_accessories": ["Silk pocket square in burnt orange"],
    },
    "tags": ["#old-money", "#quiet-luxury", "#navy", "#cream", "#tailored"],
}


def test_gemini_configuration_detection(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert not gemini_service.is_configured

    monkeypatch.setattr(settings, "gemini_api_key", "test-api-key-123")
    assert gemini_service.is_configured
    assert settings.effective_gemini_api_key == "test-api-key-123"


def test_gemini_service_parses_successful_response(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(MOCK_GEMINI_OUTPUT)}]
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = asyncio.run(
            gemini_service.analyze_outfit(_sample_image_bytes(), "image/jpeg")
        )
        assert result is not None
        assert result["aesthetic"] == "Old Money / Quiet Luxury"
        assert result["outfit_score"] == 92
        assert len(result["detected_pieces"]) == 2


def test_outfit_analysis_uses_gemini_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    async def fake_gemini_analyze(*args, **kwargs):
        return dict(MOCK_GEMINI_OUTPUT, model_used="gemini-2.5-flash")

    monkeypatch.setattr(gemini_service, "analyze_outfit", fake_gemini_analyze)

    result = asyncio.run(
        outfit_analysis_service.analyze(_sample_image_bytes(), "outfit.jpg")
    )

    assert result["engine"] == "gemini_multimodal_vision"
    assert result["outfit_score"] == 92
    assert result["aesthetic"] == "Old Money / Quiet Luxury"
    assert len(result["detected_pieces"]) == 2
    assert result["detected_pieces"][0]["slot"] == "outerwear"
    assert "elevation_tips" in result["stylist_critique"]
    assert "Gemini" in result["source_note"]
    assert result["classification"]["available"] is True
    assert result["classification"]["predicted_category"] == "Formal"
    assert result["styling"]["available"] is True
