"""Curated seasonal trend catalogue.

IMPORTANT: like `recommendations.style_rules`, this module is editorial data, not
a model. Nothing here is inferred from the user's photos - it is a hand-kept list
of current-season looks that the service scores against what a user already owns.

Vocabulary is deliberately aligned with `app.modules.ai.service`: colours come
from CANDIDATE_COLORS, patterns from CANDIDATE_PATTERNS, seasons from
CANDIDATE_SEASONS and occasions from CANDIDATE_OCCASIONS, so a trend can be
matched against stored wardrobe metadata without a translation layer.

To add a trend, append a dict with the same keys. `momentum` is 0-1 and drives
both the ordering and the status label; keep CATALOG_UPDATED current when you
edit the list.
"""

from typing import Any

CATALOG_SEASON = "Autumn/Winter 2026"
CATALOG_UPDATED = "2026-09-01"

# momentum -> label. Read as "where the look sits in its cycle".
STATUS_BANDS: list[tuple[float, str]] = [
    (0.85, "peaking"),
    (0.70, "rising"),
    (0.50, "steady"),
    (0.0, "cooling"),
]


def status_for(momentum: float) -> str:
    for threshold, label in STATUS_BANDS:
        if momentum >= threshold:
            return label
    return "cooling"


# Each key piece lists the garment words that satisfy it (matched against an
# item's type, category, tags and name) and, optionally, the colours or patterns
# that make it an on-trend example rather than merely the right garment.
TRENDS: list[dict[str, Any]] = [
    {
        "id": "quiet-luxury-neutrals",
        "genders": ["female", "male"],
        "title": "Quiet Luxury Neutrals",
        "momentum": 0.93,
        "summary": (
            "Undyed, unbranded and expensively plain. Camel, oat and bone layered "
            "tone-on-tone, with the interest coming from fabric weight rather than colour."
        ),
        "palette": ["beige", "brown", "white", "grey"],
        "patterns": ["solid"],
        "seasons": ["fall", "winter", "all_season"],
        "occasions": ["work", "formal", "day_out"],
        "key_pieces": [
            {"label": "Oversized camel coat", "types": ["coat", "overcoat", "trench"], "colors": ["beige", "brown"]},
            {"label": "Fine-gauge knit", "types": ["sweater", "knit", "jumper", "top"], "colors": ["beige", "white", "grey"]},
            {"label": "Straight-leg tailored trouser", "types": ["trouser", "pants", "chinos"], "colors": ["beige", "brown", "grey", "black"]},
            {"label": "Leather tote", "types": ["bag", "tote"], "colors": ["brown", "beige", "black"]},
        ],
        "styling_tips": [
            "Keep every piece within two shades of each other - contrast is what breaks the look.",
            "Swap silver hardware for matte brass, or skip hardware entirely.",
            "One texture change per outfit is enough: wool against silk, or suede against cotton.",
        ],
        "avoid": ["Visible logos", "High-shine synthetics"],
    },
    {
        "id": "burgundy-takeover",
        "genders": ["female", "male"],
        "title": "The Burgundy Takeover",
        "momentum": 0.91,
        "summary": (
            "Deep wine red has replaced black as the season's default dark neutral - worn "
            "head to toe, or as the single saturated note in an otherwise quiet outfit."
        ),
        "palette": ["red", "purple", "brown"],
        "patterns": ["solid"],
        "seasons": ["fall", "winter"],
        "occasions": ["evening", "party", "work", "day_out"],
        "key_pieces": [
            {"label": "Burgundy knit or shirt", "types": ["sweater", "knit", "shirt", "top", "blouse"], "colors": ["red", "purple"]},
            {"label": "Wine-toned trouser or skirt", "types": ["trouser", "pants", "skirt"], "colors": ["red", "purple", "brown"]},
            {"label": "Oxblood boot or loafer", "types": ["boot", "loafer", "shoe"], "colors": ["red", "brown"]},
        ],
        "styling_tips": [
            "Burgundy with chocolate brown is the season's pairing; burgundy with black reads dated.",
            "A single wine-coloured accessory carries the trend if you own nothing else in it.",
            "Gold jewellery warms it; silver flattens it.",
        ],
        "avoid": ["Bright primary red in the same outfit"],
    },
    {
        "id": "sheer-layering",
        "genders": ["female"],
        "title": "Sheer Layering",
        "momentum": 0.82,
        "summary": (
            "Translucent shirting and mesh worn over solid bases - a slip under organza, a "
            "knit vest over a sheer sleeve. Coverage stays high; the fabric does the talking."
        ),
        "palette": ["black", "white", "grey", "pink"],
        "patterns": ["solid", "floral"],
        "seasons": ["fall", "spring", "all_season"],
        "occasions": ["party", "evening", "day_out"],
        "key_pieces": [
            {"label": "Sheer shirt or blouse", "types": ["shirt", "blouse", "top"], "patterns": ["solid", "floral"]},
            {"label": "Slip dress or camisole base", "types": ["dress", "slip", "camisole", "top"]},
            {"label": "Knit vest or short cardigan", "types": ["vest", "cardigan", "sweater", "knit"]},
        ],
        "styling_tips": [
            "Match the base layer to your skin tone for the subtle read, or contrast it hard for the loud one.",
            "Keep the silhouette close on top if the bottom half is voluminous.",
        ],
        "avoid": ["Busy prints under sheer layers"],
    },
    {
        "id": "modern-indian-drape",
        "genders": ["female"],
        "title": "Modern Indian Drape",
        "momentum": 0.88,
        "summary": (
            "Sarees and lehengas restyled with contemporary separates - a draped saree over "
            "a shirt, a lehenga skirt with a plain knit, dupattas worn as one clean fall."
        ),
        "palette": ["red", "pink", "green", "yellow", "beige"],
        "patterns": ["solid", "floral"],
        "seasons": ["all_season", "winter"],
        "occasions": ["party", "evening", "formal"],
        "key_pieces": [
            {"label": "Saree or lehenga", "types": ["saree", "sari", "lehenga", "anarkali", "salwar"]},
            {"label": "Plain shirt or knit as the blouse", "types": ["shirt", "top", "blouse", "sweater", "knit"], "colors": ["white", "black", "beige"]},
            {"label": "Contrast dupatta or stole", "types": ["dupatta", "stole", "scarf"]},
            {"label": "Embellished flat or jutti", "types": ["jutti", "sandal", "flat", "shoe"]},
        ],
        "styling_tips": [
            "One ornamental piece per outfit - if the drape is worked, the blouse stays plain.",
            "A wide belt over the drape is the quickest way to modernise an older saree.",
        ],
        "avoid": ["Matching every piece to the same embroidery"],
    },
    {
        "id": "utility-tailoring",
        "genders": ["female", "male"],
        "title": "Utility Tailoring",
        "momentum": 0.79,
        "summary": (
            "Workwear detailing cut with a tailor's precision: patch pockets on a blazer, a "
            "chore jacket in suiting wool, cargo trousers with a pressed crease."
        ),
        "palette": ["green", "beige", "brown", "navy", "grey"],
        "patterns": ["solid", "checked"],
        "seasons": ["fall", "winter", "spring"],
        "occasions": ["work", "casual", "day_out"],
        "key_pieces": [
            {"label": "Chore jacket or utility blazer", "types": ["jacket", "blazer", "coat"], "colors": ["green", "beige", "brown", "navy"]},
            {"label": "Cargo or wide work trouser", "types": ["trouser", "pants", "cargo", "chinos"]},
            {"label": "Plain crew or oxford shirt", "types": ["shirt", "top", "t-shirt", "tee"], "colors": ["white", "beige", "grey"]},
            {"label": "Leather boot", "types": ["boot", "shoe"], "colors": ["brown", "black"]},
        ],
        "styling_tips": [
            "Pick one utility element per outfit; two makes it a costume.",
            "Press everything - the crease is what separates this from plain workwear.",
        ],
        "avoid": ["Head-to-toe khaki"],
    },
    {
        "id": "leopard-as-neutral",
        "genders": ["female"],
        "title": "Leopard as a Neutral",
        "momentum": 0.84,
        "summary": (
            "Animal print treated as a base colour rather than a statement - a leopard midi "
            "or flat styled with grey, camel and navy as though it were plain brown."
        ),
        "palette": ["brown", "beige", "black"],
        "patterns": ["animal print"],
        "seasons": ["fall", "winter", "all_season"],
        "occasions": ["day_out", "casual", "evening"],
        "key_pieces": [
            {"label": "Leopard skirt, dress or coat", "types": ["skirt", "dress", "coat", "jacket"], "patterns": ["animal print"]},
            {"label": "Solid knit to ground it", "types": ["sweater", "knit", "top"], "colors": ["brown", "beige", "grey", "black"]},
            {"label": "Leopard flat or bag", "types": ["shoe", "flat", "loafer", "bag"], "patterns": ["animal print"]},
        ],
        "styling_tips": [
            "Treat the print as brown: whatever you would wear with camel works here.",
            "One printed piece only - the rest solid.",
        ],
        "avoid": ["Pairing with another loud print"],
    },
    {
        "id": "polished-denim",
        "genders": ["female", "male"],
        "title": "Polished Denim",
        "momentum": 0.76,
        "summary": (
            "Dark, rigid, uniform indigo in tailored shapes - the barrel-leg jean and the "
            "denim maxi worn with the same pieces you would wear with trousers."
        ),
        "palette": ["navy", "blue", "white"],
        "patterns": ["solid"],
        "seasons": ["all_season", "spring", "fall"],
        "occasions": ["casual", "day_out", "work"],
        "key_pieces": [
            {"label": "Dark rigid jean or denim skirt", "types": ["jeans", "denim", "trouser", "pants", "skirt"], "colors": ["blue", "navy"]},
            {"label": "Crisp white shirt", "types": ["shirt", "blouse", "top"], "colors": ["white"]},
            {"label": "Structured blazer or coat", "types": ["blazer", "jacket", "coat"]},
        ],
        "styling_tips": [
            "Keep the wash even - distressing and whiskering read as last season.",
            "Full length or cropped at the ankle; nothing in between.",
        ],
        "avoid": ["Matching denim jacket and jean in the same wash"],
    },
    {
        "id": "chocolate-brown",
        "genders": ["female", "male"],
        "title": "Chocolate Brown Suiting",
        "momentum": 0.80,
        "summary": (
            "Brown has taken over from navy as the considered suit colour - worn as a full "
            "set, or split so the jacket does duty over jeans."
        ),
        "palette": ["brown", "beige", "white"],
        "patterns": ["solid", "checked"],
        "seasons": ["fall", "winter"],
        "occasions": ["work", "formal", "day_out"],
        "key_pieces": [
            {"label": "Brown blazer", "types": ["blazer", "jacket"], "colors": ["brown", "beige"]},
            {"label": "Matching or tonal trouser", "types": ["trouser", "pants"], "colors": ["brown", "beige"]},
            {"label": "Cream knit or shirt", "types": ["shirt", "sweater", "knit", "top", "blouse"], "colors": ["white", "beige"]},
        ],
        "styling_tips": [
            "Brown with cream reads expensive; brown with black reads accidental.",
            "Splitting the suit doubles its use - the jacket over indigo denim is the easiest version.",
        ],
        "avoid": ["Black shoes with a brown suit"],
    },
    {
        "id": "statement-outerwear",
        "genders": ["female", "male"],
        "title": "Statement Outerwear",
        "momentum": 0.74,
        "summary": (
            "The coat is the outfit. Exaggerated shoulders, floor-skimming lengths and one "
            "saturated colour over an otherwise plain base."
        ),
        "palette": ["red", "green", "purple", "navy", "black"],
        "patterns": ["solid", "checked"],
        "seasons": ["winter", "fall"],
        "occasions": ["day_out", "work", "evening"],
        "key_pieces": [
            {"label": "Long or oversized coat", "types": ["coat", "overcoat", "trench", "jacket"]},
            {"label": "Simple base layer", "types": ["top", "knit", "sweater", "shirt", "dress"], "colors": ["black", "white", "grey", "beige"]},
            {"label": "Flat boot", "types": ["boot", "shoe"]},
        ],
        "styling_tips": [
            "Everything under the coat should be quieter than the coat.",
            "Buy the shoulder one size up; the drop is the whole silhouette.",
        ],
        "avoid": ["Competing prints underneath"],
    },
    {
        "id": "soft-power-dressing",
        "genders": ["female", "male"],
        "title": "Soft Power Dressing",
        "momentum": 0.71,
        "summary": (
            "Office tailoring that has lost its stiffness - unlined jackets, fluid trousers "
            "and knitwear where a shirt used to be."
        ),
        "palette": ["navy", "grey", "white", "beige", "black"],
        "patterns": ["solid", "striped"],
        "seasons": ["all_season", "spring", "fall"],
        "occasions": ["work", "formal"],
        "key_pieces": [
            {"label": "Unstructured blazer", "types": ["blazer", "jacket"]},
            {"label": "Fluid wide trouser", "types": ["trouser", "pants"], "colors": ["navy", "grey", "black", "beige"]},
            {"label": "Fine knit in place of a shirt", "types": ["sweater", "knit", "top"], "colors": ["white", "grey", "beige", "navy"]},
            {"label": "Low block heel or loafer", "types": ["loafer", "heel", "shoe", "flat"]},
        ],
        "styling_tips": [
            "Let the trouser break once on the shoe, no more.",
            "A knit under the blazer is warmer and reads softer than a poplin shirt.",
        ],
        "avoid": ["Stiff shoulder pads"],
    },
    {
        "id": "monochrome-column",
        "genders": ["female", "male"],
        "title": "Considered Monochrome",
        "momentum": 0.68,
        "summary": (
            "Single-colour dressing done with intent - one colour, three textures, no "
            "contrast trims or hardware breaking the line."
        ),
        "palette": ["black", "grey", "navy", "white"],
        "patterns": ["solid"],
        "seasons": ["all_season", "winter"],
        "occasions": ["evening", "work", "party"],
        "key_pieces": [
            {"label": "Top in the anchor colour", "types": ["top", "shirt", "blouse", "sweater", "knit"]},
            {"label": "Bottom in the same colour", "types": ["trouser", "pants", "skirt", "jeans"]},
            {"label": "Outer layer to complete the column", "types": ["coat", "jacket", "blazer", "cardigan"]},
        ],
        "styling_tips": [
            "Three textures minimum, or it flattens into a uniform.",
            "Keep shoes and bag inside the same colour family to hold the line.",
        ],
        "avoid": ["A contrasting belt cutting the column"],
    },
    {
        "id": "pistachio-and-sage",
        "genders": ["female", "male"],
        "title": "Pistachio & Sage",
        "momentum": 0.66,
        "summary": (
            "Muted greens carried over from spring into the cold months, warmed up against "
            "cream and tan instead of the white they were worn with in summer."
        ),
        "palette": ["green", "beige", "white"],
        "patterns": ["solid", "floral"],
        "seasons": ["spring", "summer", "fall"],
        "occasions": ["day_out", "casual", "work"],
        "key_pieces": [
            {"label": "Green knit, shirt or dress", "types": ["sweater", "knit", "shirt", "top", "dress"], "colors": ["green"]},
            {"label": "Cream or tan bottom", "types": ["trouser", "pants", "skirt", "jeans"], "colors": ["beige", "white", "brown"]},
        ],
        "styling_tips": [
            "Sage sits closer to a neutral than a colour - style it the way you would grey.",
            "Tan leather accessories keep it from reading clinical.",
        ],
        "avoid": ["Bright kelly green in the same outfit"],
    },
    {
        "id": "boho-revival",
        "genders": ["female"],
        "title": "Boho Revival",
        "momentum": 0.72,
        "summary": (
            "The 70s silhouette is back in a cleaner form - suede, fringing and floral "
            "prints cut into modern, less voluminous shapes."
        ),
        "palette": ["brown", "beige", "red", "orange"],
        "patterns": ["floral", "solid"],
        "seasons": ["fall", "spring"],
        "occasions": ["day_out", "casual", "party"],
        "key_pieces": [
            {"label": "Floral midi or maxi dress", "types": ["dress", "maxi", "midi"], "patterns": ["floral"]},
            {"label": "Suede jacket or waistcoat", "types": ["jacket", "vest", "coat"], "colors": ["brown", "beige"]},
            {"label": "Tall boot", "types": ["boot", "shoe"], "colors": ["brown", "beige", "black"]},
        ],
        "styling_tips": [
            "Pick one 70s signal - the print or the suede, not both at full volume.",
            "A modern belt at the waist stops a floral maxi reading costume.",
        ],
        "avoid": ["Layered fringing on more than one piece"],
    },
    {
        "id": "sporty-off-duty",
        "genders": ["female", "male"],
        "title": "Sporty Off-Duty",
        "momentum": 0.63,
        "summary": (
            "Track and gym pieces taken out of context - a zip-up under tailoring, a running "
            "shoe with a midi skirt, everything in clean solid colours."
        ),
        "palette": ["grey", "navy", "white", "black"],
        "patterns": ["solid", "striped"],
        "seasons": ["all_season", "spring"],
        "occasions": ["casual", "sports", "day_out"],
        "key_pieces": [
            {"label": "Zip-up or sweatshirt", "types": ["sweatshirt", "hoodie", "jacket", "top"], "colors": ["grey", "navy", "black", "white"]},
            {"label": "Midi skirt or relaxed trouser", "types": ["skirt", "trouser", "pants"]},
            {"label": "Clean sneaker", "types": ["sneaker", "shoe", "trainer"], "colors": ["white", "grey"]},
        ],
        "styling_tips": [
            "One sport piece against two tailored ones keeps the balance right.",
            "Solid colours only - team logos pull it back into actual sportswear.",
        ],
        "avoid": ["A full matching tracksuit"],
    },
    {
        "id": "pinstripe-return",
        "genders": ["female", "male"],
        "title": "The Pinstripe Return",
        "momentum": 0.58,
        "summary": (
            "Wide-set stripes on grey and navy suiting, cut loose enough to wear as "
            "separates rather than as a suit."
        ),
        "palette": ["grey", "navy", "black", "white"],
        "patterns": ["striped"],
        "seasons": ["fall", "winter", "spring"],
        "occasions": ["work", "formal", "evening"],
        "key_pieces": [
            {"label": "Striped blazer or waistcoat", "types": ["blazer", "jacket", "vest"], "patterns": ["striped"]},
            {"label": "Striped trouser or skirt", "types": ["trouser", "pants", "skirt"], "patterns": ["striped"]},
            {"label": "Plain shirt or knit", "types": ["shirt", "top", "sweater", "knit"], "colors": ["white", "grey", "black"]},
        ],
        "styling_tips": [
            "Only one striped piece unless the stripes match exactly.",
            "Wider spacing reads current; fine chalk stripes read costume.",
        ],
        "avoid": ["Mixing two stripe widths"],
    },
    {
        "id": "linen-carryover",
        "genders": ["female", "male"],
        "title": "Linen Carry-Over",
        "momentum": 0.52,
        "summary": (
            "Summer linen kept in rotation by layering it - a linen shirt as a light jacket, "
            "linen trousers over boots rather than sandals."
        ),
        "palette": ["white", "beige", "blue", "green"],
        "patterns": ["solid", "striped"],
        "seasons": ["summer", "spring", "all_season"],
        "occasions": ["casual", "day_out", "work"],
        "key_pieces": [
            {"label": "Linen shirt", "types": ["shirt", "blouse", "top"], "colors": ["white", "beige", "blue"]},
            {"label": "Relaxed linen trouser", "types": ["trouser", "pants"], "colors": ["white", "beige"]},
            {"label": "Knit to layer over", "types": ["sweater", "knit", "cardigan", "vest"]},
        ],
        "styling_tips": [
            "Linen over a knit, not under it - the crease is the point.",
            "Closed shoes are what move linen out of summer.",
        ],
        "avoid": ["Pressing the linen flat"],
    },
    {
        "id": "modern-bandhgala",
        "genders": ["male"],
        "title": "The Modern Bandhgala",
        "momentum": 0.86,
        "summary": (
            "The closed-collar jacket has moved off the wedding circuit - worn over "
            "trousers and a plain shirt, it does the job a blazer used to."
        ),
        "palette": ["black", "navy", "maroon", "olive"],
        "patterns": ["solid", "embroidered"],
        "seasons": ["fall", "winter", "all_season"],
        "occasions": ["wedding", "formal", "evening"],
        "key_pieces": [
            {"label": "Bandhgala or nehru jacket", "types": ["bandhgala", "nehru jacket", "jacket", "blazer"]},
            {"label": "Straight trouser", "types": ["trouser", "pants", "churidar"], "colors": ["black", "beige", "navy", "grey"]},
            {"label": "Plain shirt or kurta underneath", "types": ["shirt", "kurta", "top"], "colors": ["white", "cream", "beige"]},
        ],
        "styling_tips": [
            "Keep the jacket the only worked piece; the shirt underneath stays plain.",
            "It reads as tailoring, so the trouser should break cleanly on the shoe.",
        ],
        "avoid": ["Matching embroidered trousers"],
    },
    {
        "id": "everyday-kurta",
        "genders": ["male", "female"],
        "title": "The Kurta as Everyday Wear",
        "momentum": 0.77,
        "summary": (
            "Plain cotton and linen kurtas worn as ordinary daywear rather than festive "
            "dress - with jeans, with chinos, with anything."
        ),
        "palette": ["white", "cream", "olive", "navy", "beige"],
        "patterns": ["solid", "striped", "block print"],
        "seasons": ["summer", "spring", "all_season"],
        "occasions": ["casual", "day_out", "work"],
        "key_pieces": [
            {"label": "Plain cotton kurta", "types": ["kurta", "kurti"], "colors": ["white", "cream", "olive", "navy", "beige"]},
            {"label": "Jeans or straight trouser", "types": ["jeans", "trouser", "pants", "churidar", "palazzo"]},
            {"label": "Leather sandal or clean sneaker", "types": ["sandal", "jutti", "sneaker", "shoe", "flat"]},
        ],
        "styling_tips": [
            "Short kurta with jeans, long kurta with something straight and narrow.",
            "Unstarched cotton is what keeps this from reading as festive dress.",
        ],
        "avoid": ["Heavy embroidery in daylight"],
    },
    {
        "id": "festive-tonal-dressing",
        "genders": ["female", "male"],
        "title": "Tonal Festive Dressing",
        "momentum": 0.83,
        "summary": (
            "Occasion wear in one colour family, with zari and embroidery doing the work "
            "that contrast trims used to - quieter than it sounds, and far easier to wear."
        ),
        "palette": ["maroon", "gold", "cream", "olive", "magenta"],
        "patterns": ["embroidered", "zari", "solid"],
        "seasons": ["winter", "fall", "all_season"],
        "occasions": ["wedding", "festive", "party"],
        "key_pieces": [
            {"label": "Occasion piece in the anchor colour", "types": ["saree", "lehenga", "anarkali", "sherwani", "kurta", "salwar kameez", "gown"]},
            {"label": "Drape or layer in the same family", "types": ["dupatta", "stole", "scarf", "jacket", "choli"]},
            {"label": "Metallic accessory", "types": ["jutti", "clutch", "bag", "sandal", "shoe"], "colors": ["gold", "silver", "beige"]},
        ],
        "styling_tips": [
            "One colour family, three depths of it - the embroidery supplies the contrast.",
            "Gold work with warm colours, silver with cool ones; mixing the two flattens both.",
        ],
        "avoid": ["A contrast dupatta fighting the base"],
    },
]


def by_id(trend_id: str) -> dict[str, Any] | None:
    return next((trend for trend in TRENDS if trend["id"] == trend_id), None)
