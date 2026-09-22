import pytest

from app.modules.ai import service as ai


def test_lower_body_garments_report_no_sleeve():
    """A sleeve reading on trousers is meaningless, not merely uncertain."""
    assert "pants" in ai.SLEEVELESS_GARMENT_TYPES
    assert "churidar" in ai.SLEEVELESS_GARMENT_TYPES
    assert "kurta" not in ai.SLEEVELESS_GARMENT_TYPES
    meta = ai.infer_metadata("white-linen-pant.jpg")
    assert meta["sleeve_type"] is None


def test_embellishment_needs_real_confidence():
    """Creased plain linen reads as embroidery at ~0.42; genuine zari at ~0.75."""
    assert ai.EMBELLISHMENT_MIN_CONFIDENCE > 0.42
    assert ai.EMBELLISHMENT_MIN_CONFIDENCE < 0.70


def test_suggested_name_skips_a_weak_pattern():
    name = ai.suggest_item_name({"primary_color": "white", "type": "pants", "pattern": "solid"})
    assert name == "White Pants"


def test_every_garment_type_has_a_prompt_and_a_home():
    for garment in ai.TYPE_PROMPTS:
        assert ai.TYPE_PROMPTS[garment], garment
    # Each type must resolve to exactly one wardrobe category.
    for garment in ai.TYPE_PROMPTS:
        homes = sum(
            garment in group
            for group in (ai.ONE_PIECE_TYPES, ai.OUTERWEAR_TYPES, ai.ACCESSORY_TYPES)
        )
        assert homes <= 1, f"{garment} is in more than one category set"


# --- preprocessing geometry ---------------------------------------------

def test_preprocessing_does_not_distort_the_garment():
    """A plain resize squashed tall photos, which is how wide-leg linen
    trousers came to be read as a churidar."""
    from PIL import Image

    from app.modules.ai.preprocessor import preprocessor

    tall = Image.new("RGB", (100, 400), (200, 60, 60))
    fitted = preprocessor.fit_to_canvas(tall, (224, 224))

    assert fitted.size == (224, 224)
    # The garment keeps its 1:4 proportions inside the padded canvas.
    pixels = fitted.load()
    assert pixels[112, 112] == (200, 60, 60), "subject should sit in the centre"
    assert pixels[5, 112] == (255, 255, 255), "sides should be padding, not stretched subject"


def test_fit_to_canvas_handles_wide_images_too():
    from PIL import Image

    from app.modules.ai.preprocessor import preprocessor

    wide = preprocessor.fit_to_canvas(Image.new("RGB", (400, 100), (10, 20, 30)), (224, 224))
    assert wide.size == (224, 224)
    assert wide.load()[112, 5] == (255, 255, 255), "top should be padding"
