"""Styling rules for outfit accessory suggestions.

IMPORTANT: this module is a deterministic rule set, not a model. Nothing here is
learned or predicted -- the suggestions are looked up from the attributes the AI
pipeline detects (category, colour, pattern). It is kept separate from the model
code so the distinction stays visible: the API labels these as rule-based, and
the UI must not present them as model output.

Each suggestion carries the reason it was chosen, so the advice is explainable
rather than arbitrary.
"""

from typing import Any

# Colour temperature drives metal tone -- the one genuinely well-established
# rule in accessory styling.
WARM_COLORS = {"red", "orange", "yellow", "beige", "brown", "pink"}
COOL_COLORS = {"blue", "navy", "green", "purple", "grey"}
NEUTRAL_COLORS = {"black", "white", "beige", "grey"}

GOLD = "gold"
SILVER = "silver"

# Per-category styling direction, keyed on the classifier's seven categories.
CATEGORY_STYLE: dict[str, dict[str, Any]] = {
    "Casual": {
        "style": "Relaxed everyday",
        "tags": ["casual", "everyday", "comfort"],
        "footwear": ["White leather sneakers", "Canvas slip-ons", "Tan suede loafers"],
        "bag": ["Canvas tote bag", "Compact crossbody bag", "Leather backpack"],
        "other": ["Minimal sunglasses", "Woven belt", "Baseball cap"],
    },
    "Formal": {
        "style": "Tailored and structured",
        "tags": ["formal", "office", "tailored"],
        "footwear": ["Leather oxfords", "Polished derby shoes", "Pointed court shoes"],
        "bag": ["Structured leather briefcase", "Slim portfolio", "Structured handbag"],
        "other": ["Silk pocket square", "Leather belt matching the shoes", "Classic tie"],
    },
    "Party": {
        "style": "Evening and statement",
        "tags": ["party", "evening", "statement"],
        "footwear": ["Heeled sandals", "Patent leather shoes", "Embellished flats"],
        "bag": ["Compact clutch", "Chain-strap evening bag", "Beaded minaudiere"],
        "other": ["Statement sunglasses", "Bold cuff", "Sheer scarf"],
    },
    "Ethnic": {
        "style": "Traditional and ornamental",
        "tags": ["ethnic", "traditional", "festive"],
        "footwear": ["Embroidered juttis", "Kolhapuri chappals", "Embellished sandals"],
        "bag": ["Potli bag", "Embroidered clutch", "Brocade sling bag"],
        "other": ["Contrast dupatta", "Bindi", "Embroidered stole"],
    },
    "Western": {
        "style": "Contemporary western",
        "tags": ["western", "modern", "smart-casual"],
        "footwear": ["Ankle boots", "Chelsea boots", "Leather sneakers"],
        "bag": ["Structured satchel", "Leather sling bag", "Bucket bag"],
        "other": ["Wide belt", "Layered scarf", "Aviator sunglasses"],
    },
    "Summer": {
        "style": "Light and breathable",
        "tags": ["summer", "light", "warm-weather"],
        "footwear": ["Leather sandals", "Espadrilles", "White slip-on shoes"],
        "bag": ["Woven straw bag", "Canvas tote bag", "Light crossbody bag"],
        "other": ["Wide-brim hat", "Light sunglasses", "Linen scarf"],
    },
    "Winter": {
        "style": "Layered and insulating",
        "tags": ["winter", "layered", "cold-weather"],
        "footwear": ["Leather boots", "Chelsea boots", "Insulated high-tops"],
        "bag": ["Leather shoulder bag", "Structured backpack", "Felt tote"],
        "other": ["Wool scarf", "Knit beanie", "Leather gloves"],
    },
}

# Jewellery by slot. Split by gender because the conventional options differ;
# 'unisex' is used when the user does not specify.
JEWELLERY: dict[str, dict[str, list[str]]] = {
    "earrings": {
        "female": ["{metal} hoop earrings", "{metal} stud earrings", "Pearl drop earrings"],
        "male": ["Small {metal} hoop", "{metal} stud earring", "Minimal black stud"],
        "unisex": ["{metal} stud earrings", "Small {metal} hoop", "Minimal geometric studs"],
    },
    "necklace": {
        "female": ["{metal} pendant chain", "Pearl necklace", "Layered {metal} chain"],
        "male": ["{metal} chain", "Leather cord necklace", "Beaded necklace"],
        "unisex": ["{metal} pendant chain", "Simple {metal} chain", "Beaded necklace"],
    },
    "bracelet": {
        "female": ["{metal} chain bracelet", "Beaded bracelet", "Slim bangle"],
        "male": ["Leather bracelet", "{metal} chain bracelet", "Beaded bracelet"],
        "unisex": ["{metal} chain bracelet", "Leather bracelet", "Beaded bracelet"],
    },
    "watch": {
        "female": ["{metal} mesh watch", "Slim leather-strap watch", "Minimal dial watch"],
        "male": ["{metal} case watch", "Brown leather watch", "Steel bracelet watch"],
        "unisex": ["{metal} case watch", "Leather-strap watch", "Minimal dial watch"],
    },
}

VALID_GENDERS = {"female", "male", "unisex"}


def metal_tone(primary_color: str, secondary_colors: list[str]) -> tuple[str, str]:
    """Pick a metal tone from colour temperature. Returns (metal, reason)."""
    palette = [primary_color, *secondary_colors]
    warm = sum(1 for c in palette if c in WARM_COLORS)
    cool = sum(1 for c in palette if c in COOL_COLORS)

    if warm > cool:
        return GOLD, f"warm tones ({primary_color}) sit better with gold"
    if cool > warm:
        return SILVER, f"cool tones ({primary_color}) sit better with silver"
    return GOLD, "a neutral palette takes either metal; gold is the warmer default"


def build_tags(category: str, primary_color: str, pattern: str, seasons: list[str]) -> list[str]:
    """Derive hashtags from detected attributes. Deterministic, not predicted."""
    style = CATEGORY_STYLE.get(category, {})
    tags: list[str] = list(style.get("tags", []))
    for extra in (primary_color, pattern, *seasons):
        if extra and extra not in ("user_review_needed",):
            tags.append(extra.replace("_", "-"))

    seen, ordered = set(), []
    for t in tags:
        t = t.lower().replace(" ", "-")
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return [f"#{t}" for t in ordered[:6]]


def recommend_accessories(
    category: str,
    gender: str,
    primary_color: str,
    secondary_colors: list[str],
) -> dict[str, Any]:
    """Look up accessory suggestions for the detected attributes.

    Returns slots of suggestions plus the reasoning behind them. Every value is
    rule-derived; none of it is model output.
    """
    gender = gender if gender in VALID_GENDERS else "unisex"
    style = CATEGORY_STYLE.get(category)
    if style is None:
        # Unknown category -- say so rather than inventing advice.
        return {
            "available": False,
            "reason": f"No styling rules defined for category '{category}'.",
            "slots": {},
        }

    metal, metal_reason = metal_tone(primary_color, secondary_colors)

    slots: dict[str, list[str]] = {}
    for slot, by_gender in JEWELLERY.items():
        options = by_gender.get(gender, by_gender["unisex"])
        slots[slot] = [o.format(metal=metal.capitalize()) for o in options]

    slots["footwear"] = list(style["footwear"])
    slots["bag"] = list(style["bag"])
    slots["other"] = list(style["other"])

    return {
        "available": True,
        "style": style["style"],
        "metal_tone": metal,
        "reasoning": [
            f"Category '{category}' suggests a {style['style'].lower()} direction.",
            f"Metal tone: {metal_reason}.",
            f"Options shown for '{gender}'.",
        ],
        "slots": slots,
    }
