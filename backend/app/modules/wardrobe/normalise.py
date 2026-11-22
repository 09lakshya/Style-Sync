"""One canonical spelling for every wardrobe attribute.

Values reach the database from three places - Gemini ("Maroon", "Solid",
"office"), CLIP (lowercase labels from its own vocabulary) and the user's own
edits - and the rest of the app compares them as plain strings. Without a single
spelling, "Maroon" and "maroon" are counted as two colours and a "trouser" never
lands in an outfit because only "pants" is a bottom. Every write goes through
here, and scripts/normalise_wardrobe.py applies the same rules to old rows.
"""

from typing import Any, Iterable

from app.modules.ai.service import (
    ACCESSORY_TYPES,
    CANDIDATE_OCCASIONS,
    CANDIDATE_SEASONS,
    CANDIDATE_SLEEVES,
    ETHNIC_TYPES,
    ONE_PIECE_TYPES,
    OUTERWEAR_TYPES,
)

# Everyday words for garments the app already knows under another name.
TYPE_SYNONYMS = {
    "trouser": "pants",
    "trousers": "pants",
    "chinos": "pants",
    "chino": "pants",
    "slacks": "pants",
    "pant": "pants",
    "leggings": "pants",
    "joggers": "pants",
    "jean": "jeans",
    "denim": "jeans",
    "tee": "t-shirt",
    "tshirt": "t-shirt",
    "t shirt": "t-shirt",
    "tank top": "top",
    "crop top": "top",
    "sweatshirt": "hoodie",
    "pullover": "sweater",
    "jumper": "sweater",
    "maxi dress": "dress",
    "ball gown": "gown",
    "overcoat": "coat",
    "trench coat": "coat",
    "vest": "waistcoat",
    "short": "shorts",
    "sari": "saree",
    "kameez": "kurta",
    "palazzos": "palazzo",
    "palazzo pants": "palazzo",
    "stole": "dupatta",
}

# Occasion words Gemini and older versions of the form use, mapped onto the
# vocabulary the outfit builder ranks and groups by.
OCCASION_SYNONYMS = {
    "office": "work",
    "college": "casual",
    "everyday": "casual",
    "travel": "day_out",
    "day out": "day_out",
    "sport": "sports",
    "gym": "sports",
    "festival": "festive",
    "evening out": "evening",
    "traditional": "festive",
}

SEASON_SYNONYMS = {
    "autumn": "fall",
    "all season": "all_season",
    "all seasons": "all_season",
    "all-season": "all_season",
    "all year": "all_season",
}

SLEEVE_SYNONYMS = {
    "short sleeve": "short_sleeve",
    "long sleeve": "long_sleeve",
    "three quarter": "three_quarter",
    "3/4": "three_quarter",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def normalise_color(value: Any) -> str | None:
    cleaned = _clean(value)
    return cleaned or None


def normalise_pattern(value: Any) -> str | None:
    cleaned = _clean(value).replace("_", " ")
    return cleaned or None


def normalise_type(value: Any) -> str | None:
    cleaned = _clean(value).replace("_", " ")
    if not cleaned:
        return None
    return TYPE_SYNONYMS.get(cleaned, cleaned)


def normalise_fabric(value: Any) -> str | None:
    cleaned = _clean(value)
    return cleaned or None


def normalise_sleeve(value: Any) -> str | None:
    cleaned = _clean(value).replace("-", " ")
    cleaned = SLEEVE_SYNONYMS.get(cleaned, cleaned.replace(" ", "_"))
    return cleaned if cleaned in CANDIDATE_SLEEVES else None


def _normalise_list(values: Any, synonyms: dict[str, str], allowed: Iterable[str]) -> list[str]:
    if isinstance(values, str):
        values = [values]
    allowed_set = set(allowed)
    out: list[str] = []
    for value in values or []:
        cleaned = _clean(value).replace("-", " ")
        cleaned = synonyms.get(cleaned, cleaned.replace(" ", "_"))
        if cleaned in allowed_set and cleaned not in out:
            out.append(cleaned)
    return out


def normalise_occasions(values: Any) -> list[str]:
    return _normalise_list(values, OCCASION_SYNONYMS, CANDIDATE_OCCASIONS)


def normalise_seasons(values: Any) -> list[str]:
    return _normalise_list(values, SEASON_SYNONYMS, CANDIDATE_SEASONS)


def normalise_colors(values: Any) -> list[str]:
    if isinstance(values, str):
        values = [values]
    out: list[str] = []
    for value in values or []:
        color = normalise_color(value)
        if color and color not in out:
            out.append(color)
    return out


def category_for(garment: str) -> str:
    if garment in ONE_PIECE_TYPES:
        return "one_piece"
    if garment in OUTERWEAR_TYPES:
        return "outerwear"
    if garment in ACCESSORY_TYPES:
        return "accessories"
    return "separates"


def tags_for_type(tags: Iterable[Any], old_type: Any, new_type: str) -> list[str]:
    """Swap the garment tag and the ethnic tag over to a new type."""
    # Both spellings of the old type: the stored one ("trouser") and the one it
    # maps to ("pants").
    stale = {"ethnic", new_type, _clean(old_type), normalise_type(old_type)}
    kept = [str(t) for t in tags or [] if _clean(t) not in stale]
    kept.append(new_type)
    if new_type in ETHNIC_TYPES:
        kept.append("ethnic")
    return kept


def normalise_item(item: dict[str, Any]) -> dict[str, Any]:
    """Return the fields of a stored item whose canonical spelling differs."""
    changes: dict[str, Any] = {}

    def update(field: str, value: Any) -> None:
        if value is not None and value != item.get(field):
            changes[field] = value

    update("primary_color", normalise_color(item.get("primary_color")))
    update("pattern", normalise_pattern(item.get("pattern")))
    update("fabric", normalise_fabric(item.get("fabric")))
    if item.get("secondary_colors") is not None:
        update("secondary_colors", normalise_colors(item.get("secondary_colors")))
    if item.get("occasion"):
        update("occasion", normalise_occasions(item.get("occasion")) or ["casual"])
    if item.get("season"):
        update("season", normalise_seasons(item.get("season")) or ["all_season"])

    garment = normalise_type(item.get("type"))
    if garment and garment != item.get("type"):
        changes["type"] = garment
        changes["category"] = category_for(garment)
        changes["tags"] = tags_for_type(item.get("tags") or [], item.get("type"), garment)
    return changes
