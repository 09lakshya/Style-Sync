from app.modules.recommendations import style_rules


def test_metal_tone_follows_colour_temperature():
    assert style_rules.metal_tone("red", ["yellow"])[0] == style_rules.GOLD
    assert style_rules.metal_tone("blue", ["navy"])[0] == style_rules.SILVER


def test_metal_tone_defaults_on_neutral_palette():
    metal, reason = style_rules.metal_tone("black", ["white"])
    assert metal in (style_rules.GOLD, style_rules.SILVER)
    assert reason


def test_tags_are_derived_from_detected_attributes():
    tags = style_rules.build_tags("Party", "red", "floral", ["summer"])
    assert "#party" in tags
    assert "#red" in tags
    assert "#floral" in tags
    assert all(t.startswith("#") for t in tags)


def test_tags_do_not_leak_placeholder_values():
    tags = style_rules.build_tags("Casual", "blue", "user_review_needed", [])
    assert "#user_review_needed" not in tags


def test_every_classifier_category_has_styling_rules():
    """Guards against a category the model can predict but the rules cannot style."""
    categories = ["Casual", "Ethnic", "Formal", "Party", "Summer", "Western", "Winter"]
    for cat in categories:
        result = style_rules.recommend_accessories(cat, "unisex", "blue", [])
        assert result["available"], f"no styling rules for {cat}"
        for slot in ("earrings", "necklace", "bracelet", "watch", "footwear", "bag", "other"):
            assert result["slots"][slot], f"{cat} has no {slot} suggestions"


def test_unknown_category_returns_unavailable_rather_than_inventing_advice():
    result = style_rules.recommend_accessories("Beachwear", "female", "red", [])
    assert result["available"] is False
    assert result["slots"] == {}
    assert "Beachwear" in result["reason"]


def test_gender_changes_the_suggestions():
    female = style_rules.recommend_accessories("Casual", "female", "red", [])
    male = style_rules.recommend_accessories("Casual", "male", "red", [])
    assert female["slots"]["necklace"] != male["slots"]["necklace"]


def test_unrecognised_gender_falls_back_to_unisex():
    odd = style_rules.recommend_accessories("Casual", "not-a-gender", "red", [])
    unisex = style_rules.recommend_accessories("Casual", "unisex", "red", [])
    assert odd["slots"] == unisex["slots"]


def test_metal_tone_is_applied_to_jewellery_text():
    cool = style_rules.recommend_accessories("Party", "female", "blue", ["navy"])
    assert cool["metal_tone"] == style_rules.SILVER
    assert any("Silver" in option for option in cool["slots"]["earrings"])


def test_reasoning_is_present_so_advice_is_explainable():
    result = style_rules.recommend_accessories("Formal", "male", "black", [])
    assert result["reasoning"]
    assert any("Metal tone" in r for r in result["reasoning"])
