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

# Traditional/ethnic layering items (outer garments)
ETHNIC_LAYERS = {"nehru jacket", "bandhgala", "phiran", "waistcoat"}

# Western casual outerwear that clashes when worn over traditional garments
WESTERN_CASUAL_LAYERS = {
    "jacket", "coat", "hoodie", "cardigan", "blazer", "sweater"
}

# Fabrics that clash structurally or sensorially
HEAVY_LEATHER_OR_WINTER = {"leather", "shearling", "fleece", "heavy wool", "down"}
DELICATE_SUMMER_FABRICS = {"linen", "chiffon", "georgette", "silk"}

# Traditional/ethnic layering items (outer garments)
ETHNIC_LAYERS = {"nehru jacket", "bandhgala", "phiran", "waistcoat"}

# Western casual outerwear that clashes when worn over traditional garments
WESTERN_CASUAL_LAYERS = {
    "jacket", "coat", "hoodie", "cardigan", "blazer", "sweater"
}

# Fabrics that clash structurally or sensorially
HEAVY_LEATHER_OR_WINTER = {"leather", "shearling", "fleece", "heavy wool", "down"}
DELICATE_SUMMER_FABRICS = {"linen", "chiffon", "georgette", "silk"}


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
    name = str(item.get("name") or "").lower()
    tags = {str(t).lower() for t in (item.get("tags") or [])}
    if garment in ETHNIC_TYPES or "ethnic" in tags:
        return True
    return any(ethnic_type in name for ethnic_type in ETHNIC_TYPES)


def is_leather_item(item: dict[str, Any]) -> bool:
    fabric = str(item.get("fabric") or "").lower()
    name = str(item.get("name") or "").lower()
    tags = {str(t).lower() for t in (item.get("tags") or [])}
    return fabric == "leather" or "leather" in name or "leather" in tags


def can_layer(layer: dict[str, Any], core_pieces: list[dict[str, Any]]) -> tuple[bool, str]:
    """Determines whether a layer item can tastefully sit on top of core pieces."""
    layer_type = str(layer.get("type") or "").lower()
    layer_is_ethnic = is_ethnic(layer) or layer_type in ETHNIC_LAYERS
    layer_is_leather = is_leather_item(layer)

    # 1. Tradition & Cultural Silhouette Compatibility:
    has_ethnic_top = any(
        is_ethnic(p) and slot_of(p) in {"top", "one_piece"}
        for p in core_pieces
    )

    if has_ethnic_top:
        # A traditional top (kurta, kurti, saree, anarkali) can only be layered with ethnic outerwear.
        # Casual Western outerwear like leather jackets or hoodies strictly clash.
        if not layer_is_ethnic:
            return False, f"A western {layer_type or 'jacket'} clashes culturally and structurally over a traditional top."

    # Conversely, an ethnic outer garment (like a formal bandhgala) shouldn't layer over casual western tees/hoodies
    has_casual_western_top = any(
        not is_ethnic(p) and str(p.get("type") or "").lower() in {"t-shirt", "hoodie", "tank top"}
        for p in core_pieces
    )
    if has_casual_western_top and layer_is_ethnic and layer_type != "waistcoat":
        return False, f"A traditional {layer_type} clashes over casual western separates."

    # 2. Fabric Physics & Material Harmony:
    # Heavy leather jackets over delicate/linen tops create an absurd textural clash
    has_delicate_summer_top = any(
        (
            str(p.get("fabric") or "").lower() in DELICATE_SUMMER_FABRICS
            or "linen" in str(p.get("name") or "").lower()
            or "linen" in str(p.get("fabric") or "").lower()
            or "silk" in str(p.get("fabric") or "").lower()
        )
        and slot_of(p) in {"top", "one_piece"}
        for p in core_pieces
    )
    if layer_is_leather and has_delicate_summer_top:
        return False, "Heavy leather outerwear clashes over delicate or breathable linen/summer tops."

    # 3. Season Harmony:
    layer_seasons = seasons_of(layer)
    if layer_seasons and layer_seasons != {"all_season"}:
        core_seasons = shared_seasons(core_pieces)
        if core_seasons and core_seasons != {"all_season"}:
            if not (layer_seasons & core_seasons):
                return False, "Layer season conflicts with the base outfit."

    # 4. Color Clash:
    outfit_colors: set[str] = set()
    for p in core_pieces:
        outfit_colors |= colors_of(p)
    if clashes(colors_of(layer), outfit_colors):
        return False, "Layer color clashes with the outfit."

    return True, ""


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
