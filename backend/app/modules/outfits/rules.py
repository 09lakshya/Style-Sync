"""Pairing rules for building outfits out of a user's own wardrobe.

IMPORTANT: deterministic rules, not a model. Nothing here is inferred from
photos - it reads the metadata already stored on each item (type, colour,
pattern, occasion, season) and decides whether two pieces work together, and
what the pair is for.

The rules are written so every decision can be explained in a sentence, because
a suggestion the user cannot argue with is a suggestion they will not trust.
"""

from typing import Any

from app.modules.ai.service import (
    ACCESSORY_TYPES,
    BOTTOM_TYPES,
    ETHNIC_TYPES,
    ONE_PIECE_TYPES,
    OUTERWEAR_TYPES,
    TOP_TYPES,
)

# Colours that sit under anything.
NEUTRALS = {"black", "white", "cream", "grey", "beige", "navy", "brown", "silver"}

# Rough temperature, used only to spot two loud colours fighting.
WARM = {"red", "maroon", "orange", "peach", "yellow", "mustard", "gold", "brown", "beige"}
COOL = {"blue", "navy", "teal", "green", "olive", "purple", "grey", "silver"}

# Colours that read as the same family when worn together.
TONAL_FAMILIES = [
    {"beige", "cream", "brown", "white", "gold"},
    {"black", "grey", "silver", "white"},
    {"blue", "navy", "teal"},
    {"green", "olive", "teal"},
    {"red", "maroon", "pink", "magenta"},
    {"purple", "magenta", "maroon"},
    {"yellow", "mustard", "gold", "orange", "peach"},
]

# Patterns quiet enough to sit next to another pattern.
QUIET_PATTERNS = {"solid", "striped", "checked"}

# Ethnic tops that have genuinely crossed over to western bottoms. Without this
# the rules would reject the kurta-with-jeans pairing that half the wardrobes
# in the country are built on.
CROSSOVER_TOPS = {"kurta", "kurti"}
CROSSOVER_BOTTOMS = {"jeans", "pants", "skirt"}

# How formal each occasion reads, for deciding what a pairing is *for*.
OCCASION_RANK = {
    "sports": 0,
    "casual": 1,
    "day_out": 2,
    "work": 3,
    "evening": 4,
    "party": 5,
    "festive": 6,
    "formal": 7,
    "wedding": 8,
}

OCCASION_LABELS = {
    "sports": "Sport or the gym",
    "casual": "Everyday casual",
    "day_out": "A day out",
    "work": "The office",
    "evening": "An evening out",
    "party": "A party",
    "festive": "A festival or celebration",
    "formal": "Something formal",
    "wedding": "A wedding",
}


# The tradition axis, which runs independently of the occasion one: a kurta with
# jeans is everyday casual *and* leans traditional, while the same kurta with a
# churidar is traditional outright. An outfit is listed under every style it
# genuinely belongs to rather than being forced onto one.
STYLE_LABELS = {
    "western": "Western",
    "fusion": "Indo-western",
    "traditional": "Traditional",
}

STYLE_ORDER = ["western", "fusion", "traditional"]

# Short ethnic tops read as everyday wear over western bottoms; the long ones
# keep more of their traditional weight.
SHORT_ETHNIC_TOPS = {"kurti", "choli"}

# Bottoms that make a traditional top read as a full traditional outfit.
TRADITIONAL_BOTTOMS = {
    "churidar", "dhoti", "palazzo", "sharara", "gharara", "patiala salwar", "lungi",
}


def slot_of(item: dict[str, Any]) -> str | None:
    """Which part of an outfit this garment fills."""
    garment = str(item.get("type") or "").lower()
    if garment in ONE_PIECE_TYPES:
        return "one_piece"
    if garment in TOP_TYPES:
        return "top"
    if garment in BOTTOM_TYPES:
        return "bottom"
    if garment in OUTERWEAR_TYPES:
        return "layer"
    if garment in ACCESSORY_TYPES:
        return "accessory"
    return None


def colors_of(item: dict[str, Any]) -> set[str]:
    colors = {str(item.get("primary_color") or item.get("color") or "").lower()}
    colors |= {str(c).lower() for c in (item.get("secondary_colors") or [])}
    return {c for c in colors if c}


def is_neutral(item: dict[str, Any]) -> bool:
    return bool(colors_of(item) & NEUTRALS)


def same_family(a: set[str], b: set[str]) -> bool:
    return any(a & family and b & family for family in TONAL_FAMILIES)


def clashes(a: set[str], b: set[str]) -> bool:
    """Two saturated colours from opposite temperatures, with no neutral to rest on."""
    if a & NEUTRALS or b & NEUTRALS:
        return False
    if same_family(a, b):
        return False
    return bool((a & WARM and b & COOL) or (a & COOL and b & WARM))


def pattern_of(item: dict[str, Any]) -> str:
    return str(item.get("pattern") or "solid").lower()


def is_ethnic(item: dict[str, Any]) -> bool:
    garment = str(item.get("type") or "").lower()
    return garment in ETHNIC_TYPES or "ethnic" in {
        str(t).lower() for t in (item.get("tags") or [])
    }


def occasions_of(item: dict[str, Any]) -> set[str]:
    return {str(o).lower().replace(" ", "_") for o in (item.get("occasion") or []) if o}


def seasons_of(item: dict[str, Any]) -> set[str]:
    return {str(s).lower().replace(" ", "_") for s in (item.get("season") or []) if s}


def shared_seasons(pieces: list[dict[str, Any]]) -> set[str]:
    """Seasons every piece can be worn in; all_season never rules anything out."""
    shared: set[str] | None = None
    for piece in pieces:
        seasons = seasons_of(piece)
        if not seasons or seasons == {"all_season"}:
            continue
        seasons = seasons - {"all_season"}
        shared = seasons if shared is None else shared & seasons
    return shared if shared is not None else {"all_season"}


def resolve_styles(pieces: list[dict[str, Any]]) -> tuple[str, list[str], str]:
    """The outfit's headline style, every style it can be listed under, and why.

    Mixed pairings are the interesting case. A kurta over jeans is not western
    and not fully traditional, so it is listed as indo-western *and* under
    traditional, where someone looking for ethnic wear would expect to find it.
    How far it leans depends on the ethnic piece: a short kurti reads as
    everyday, a full-length kurta carries more of the tradition with it.
    """
    ethnic = [piece for piece in pieces if is_ethnic(piece)]

    if not ethnic:
        return "western", ["western"], ""

    if len(ethnic) == len(pieces):
        return "traditional", ["traditional"], "Every piece is traditional."

    top_type = str(pieces[0].get("type") or "").lower()
    bottom_type = str(pieces[1].get("type") or "").lower() if len(pieces) > 1 else ""

    if bottom_type in TRADITIONAL_BOTTOMS:
        return "traditional", ["traditional"], f"A {top_type} over a {bottom_type} reads traditional."

    if top_type in SHORT_ETHNIC_TOPS:
        note = f"A short {top_type} over {bottom_type} is everyday wear with a traditional note."
    else:
        note = f"A {top_type} over {bottom_type} leans traditional without being formal ethnic wear."

    return "fusion", ["fusion", "traditional"], note


def resolve_occasion(pieces: list[dict[str, Any]]) -> tuple[str, bool, list[str]]:
    """What the outfit is for: the headline occasion, whether the pieces agreed,
    and every occasion it genuinely covers.

    The full list matters for browsing. A cotton shirt and jeans both logged for
    casual and a day out suit both, and listing the outfit only under the
    dressier of the two hides it from the section where someone would look for
    it. Without any shared occasion the dressier piece decides alone: a silk top
    with jeans is an evening outfit, not a casual one.
    """
    sets = [occasions_of(piece) for piece in pieces if occasions_of(piece)]
    if not sets:
        return "casual", False, ["casual"]

    shared = set.intersection(*sets) if len(sets) > 1 else sets[0]
    if shared:
        ordered = sorted(shared, key=lambda o: OCCASION_RANK.get(o, 1))
        return ordered[-1], True, ordered

    everything = set.union(*sets)
    headline = max(everything, key=lambda o: OCCASION_RANK.get(o, 1))
    return headline, False, [headline]
