import logging
import time
from collections import Counter
from typing import Any
from PIL import Image

from app.core.config import settings
from app.modules.ai.clip_manager import clip_manager
from app.modules.ai.preprocessor import preprocessor

logger = logging.getLogger("stylesync.ai.service")

# Candidate label sets for Zero-Shot attribute extraction.
#
# Every attribute is described by a prompt phrase rather than the bare label.
# CLIP scores a sentence, not a word, so "a kurta, a long straight Indian tunic"
# separates cleanly from "a shirt", where the bare word "kurta" does not. The
# dict key is what gets stored; the value is only ever sent to the model.
TYPE_PROMPTS: dict[str, str] = {
    # Western
    "dress": "a dress",
    "gown": "a long formal evening gown",
    "shirt": "a button-up shirt",
    "blouse": "a women's blouse",
    "top": "a casual top",
    "t-shirt": "a t-shirt",
    "skirt": "a skirt",
    "pants": "a pair of trousers",
    "jeans": "a pair of denim jeans",
    "shorts": "a pair of shorts",
    "jumpsuit": "a jumpsuit",
    "romper": "a playsuit romper",
    "jacket": "a jacket",
    "coat": "a long coat",
    "blazer": "a tailored blazer",
    "sweater": "a knitted sweater",
    "hoodie": "a hooded sweatshirt",
    "cardigan": "a knitted cardigan",
    "waistcoat": "a sleeveless waistcoat",
    # Ethnic / South Asian. Zero-shot classification can only return a label it
    # was given, so without these an anarkali or saree is forced onto the
    # nearest Western word -- typically "skirt" or "dress". The wardrobe has an
    # Ethnic category, so the vocabulary has to cover it properly.
    "saree": "a saree, the traditional Indian draped garment",
    "lehenga": "a lehenga, an embroidered Indian flared skirt worn with a choli",
    "choli": "a choli, the fitted Indian blouse worn with a lehenga or saree",
    "anarkali": "an anarkali, a long flared Indian frock-style kurta",
    "salwar kameez": "a salwar kameez, an Indian tunic worn with loose trousers",
    "patiala salwar": "a patiala salwar, heavily pleated loose Indian trousers",
    "churidar": "a churidar, tight-fitting gathered Indian trousers",
    "palazzo": "palazzo pants, wide-legged flowing Indian trousers",
    "sharara": "a sharara, wide flared Indian trousers worn with a short kurta",
    "gharara": "a gharara, Indian trousers flared from the knee",
    "kurta": "a kurta, a long straight Indian tunic",
    "kurti": "a kurti, a short Indian tunic top",
    "angrakha": "an angrakha, an Indian overlapping wrap-style tunic",
    "sherwani": "a sherwani, a long embroidered Indian coat for men",
    "bandhgala": "a bandhgala jodhpuri suit, an Indian closed-collar formal jacket",
    "nehru jacket": "a nehru jacket, a short Indian mandarin-collar waistcoat",
    "pathani suit": "a pathani suit, a straight Indian kurta with matching trousers",
    "dhoti": "a dhoti, a draped Indian lower garment for men",
    "lungi": "a lungi, a wrapped Indian sarong",
    "mekhela chador": "a mekhela chador, the traditional Assamese two-piece drape",
    "pattu pavadai": "a pattu pavadai half saree, the South Indian skirt and drape",
    "phiran": "a phiran, a loose Kashmiri woollen overgarment",
    "indo-western gown": "an indo-western gown blending Indian embroidery with a western cut",
    "dupatta": "a dupatta, a long Indian scarf or stole",
}

CANDIDATE_TYPES = list(TYPE_PROMPTS)

CANDIDATE_CATEGORIES = ["one_piece", "separates", "outerwear", "accessories"]

# Garments worn as a single complete outfit rather than separates.
ONE_PIECE_TYPES = {
    "dress", "gown", "jumpsuit", "romper",
    "saree", "lehenga", "anarkali", "salwar kameez", "sherwani",
    "pathani suit", "mekhela chador", "pattu pavadai", "indo-western gown",
    "angrakha",
}
OUTERWEAR_TYPES = {
    "jacket", "coat", "blazer", "cardigan", "waistcoat",
    "bandhgala", "nehru jacket", "phiran",
}
ACCESSORY_TYPES = {"dupatta"}

# Garments that place an item in the Ethnic side of the wardrobe. Used to tag
# items and to keep festive occasions in play for them.
ETHNIC_TYPES = {
    "saree", "lehenga", "choli", "anarkali", "salwar kameez", "patiala salwar",
    "churidar", "palazzo", "sharara", "gharara", "kurta", "kurti", "angrakha",
    "sherwani", "bandhgala", "nehru jacket", "pathani suit", "dhoti", "lungi",
    "mekhela chador", "pattu pavadai", "phiran", "indo-western gown", "dupatta",
}

# Colours. The second block matters for ethnic wear, where maroon, mustard and
# metallics are ordinary rather than exotic and "red" or "yellow" loses the item.
COLOR_PROMPTS: dict[str, str] = {
    "blue": "blue",
    "navy": "dark navy blue",
    "teal": "teal",
    "white": "white",
    "cream": "cream off-white",
    "black": "black",
    "grey": "grey",
    "green": "green",
    "olive": "olive green",
    "red": "bright red",
    "maroon": "deep maroon",
    "pink": "pink",
    "magenta": "magenta",
    "peach": "peach",
    "yellow": "yellow",
    "mustard": "mustard yellow",
    "beige": "beige",
    "brown": "brown",
    "purple": "purple",
    "orange": "orange",
    "gold": "metallic gold",
    "silver": "metallic silver",
}

CANDIDATE_COLORS = list(COLOR_PROMPTS)

# Patterns, including the surface work that defines most Indian occasion wear.
PATTERN_PROMPTS: dict[str, str] = {
    "solid": "a plain solid colour with no pattern",
    "floral": "a floral pattern",
    "striped": "a striped pattern",
    "checked": "a checked pattern",
    "plaid": "a plaid tartan pattern",
    "polka dot": "a polka dot pattern",
    "graphic": "a printed graphic",
    "animal print": "an animal print",
    "geometric": "a geometric pattern",
    "paisley": "a paisley buta pattern",
    "embroidered": "dense thread embroidery",
    "zari": "metallic zari brocade work",
    "sequined": "sequins and mirror work",
    "bandhani": "bandhani tie-dye dots",
    "block print": "a hand block print",
    "ikat": "an ikat woven pattern",
}

CANDIDATE_PATTERNS = list(PATTERN_PROMPTS)

# Patterns that are surface work rather than a woven print. Reported separately
# so the UI can say "embroidered" without losing the base pattern.
EMBELLISHMENT_PATTERNS = {"embroidered", "zari", "sequined"}

# Fabrics. Detection is coarse -- CLIP reads drape and sheen, not fibre -- so
# the confidence is returned alongside and the UI should treat it as a hint.
FABRIC_PROMPTS: dict[str, str] = {
    "cotton": "matte cotton fabric",
    "linen": "textured linen fabric",
    "denim": "denim fabric",
    "silk": "glossy silk fabric",
    "satin": "smooth satin fabric",
    "chiffon": "sheer chiffon fabric",
    "georgette": "crinkled georgette fabric",
    "velvet": "plush velvet fabric",
    "brocade": "stiff woven brocade fabric",
    "wool": "woollen fabric",
    "knit": "knitted jersey fabric",
    "leather": "leather",
}

CANDIDATE_FABRICS = list(FABRIC_PROMPTS)

CANDIDATE_SEASONS = ["summer", "winter", "spring", "fall", "all_season"]

OCCASION_PROMPTS: dict[str, str] = {
    "casual": "a casual everyday occasion",
    "formal": "a formal occasion",
    "work": "the office",
    "party": "a party",
    "evening": "an evening out",
    "day_out": "a day out",
    "sports": "sport or exercise",
    "wedding": "an Indian wedding",
    "festive": "a festival or religious celebration",
}

CANDIDATE_OCCASIONS = list(OCCASION_PROMPTS)

# Occasions an ethnic garment should still be offered for, even when the top
# zero-shot answer is the generic "casual".
ETHNIC_OCCASIONS = {"wedding", "festive", "party", "formal"}

CANDIDATE_SLEEVES = ["sleeveless", "short_sleeve", "long_sleeve", "three_quarter"]

# Prompt -> styling gender. Phrased around the clothing rather than the wearer
# so flat-lay and hanger photos are classifiable too.
GENDER_PROMPTS = {
    "women's clothing": "female",
    "men's clothing": "male",
}


class AIService:
    """
    Dedicated AI Service for computer vision preprocessing, CLIP feature extraction,
    zero-shot clothing attribute classification, and embedding generation.
    """

    def __init__(self) -> None:
        self.clip = clip_manager
        self.preprocessor = preprocessor

    def preprocess_image(self, file_bytes: bytes) -> Image.Image:
        """Decode and enhance image with OpenCV."""
        return self.preprocessor.preprocess_for_clip(file_bytes)

    def _crop_to_subject(self, file_bytes: bytes) -> bytes:
        """Return the image bytes to analyse: cropped to the subject when needed."""
        # In a full-scene photo the background dominates what CLIP sees -- a room
        # portrait measured here put the person at 5.8% of the frame and the
        # colour came back as the carpet rather than the outfit. Crop to the
        # subject in that case only; normally framed photos are left untouched
        # (see subject_detector, which is deliberately conservative).
        #
        # The crop must happen at full resolution, BEFORE downscaling to 224px --
        # cropping the downscaled image leaves a handful of pixels to upscale.
        #
        # Deliberately not applied to embeddings: the duplicate-detection
        # thresholds are calibrated on uncropped images.
        analysis_bytes = file_bytes
        try:
            import io as _io

            from app.modules.ai.subject_detector import subject_detector

            original = Image.open(_io.BytesIO(file_bytes)).convert("RGB")
            cropped, crop_info = subject_detector.crop_to_subject(original)
            if crop_info.get("cropped"):
                buffer = _io.BytesIO()
                cropped.save(buffer, format="PNG")
                analysis_bytes = buffer.getvalue()
                logger.info(
                    "Cropped to subject (coverage %.3f, score %.3f) before attribute extraction",
                    crop_info["coverage"], crop_info["score"],
                )
        except Exception as exc:
            logger.warning("Subject cropping skipped: %s", exc)
        return analysis_bytes

    def detect_styling_gender(self, file_bytes: bytes) -> tuple[str, float | None]:
        """Guess whether the outfit is menswear or womenswear via CLIP zero-shot.

        Returns ("female" | "male" | "unisex", confidence). Only a confident
        call picks a side; anything close, or any failure, is "unisex" so the
        styling never commits to options the image does not support. This reads
        the clothing's styling, so it works on flat-lays as well as worn photos.
        """
        if not self.clip.is_loaded:
            # The fallback classifier is uniform, so there is nothing to read.
            return "unisex", None

        try:
            pil_image = self.preprocess_image(self._crop_to_subject(file_bytes))
        except Exception as exc:
            logger.warning("Gender detection skipped, preprocessing failed: %s", exc)
            return "unisex", None

        results = self.clip.zero_shot_classify(
            pil_image,
            list(GENDER_PROMPTS),
            prompt_template="a photo of {}",
        )
        if not results:
            return "unisex", None

        top_label, top_conf = results[0]
        gender = GENDER_PROMPTS[top_label] if top_conf >= settings.gender_confidence_threshold else "unisex"
        logger.info("Styling gender: %s (%s at %.2f)", gender, top_label, top_conf)
        return gender, round(float(top_conf), 2)

    def _classify_prompted(
        self,
        pil_image: Image.Image,
        prompts: dict[str, str],
        template: str,
    ) -> list[tuple[str, float]]:
        """Zero-shot classify by prompt phrase, returning results keyed by label.

        CLIP compares whole sentences, so each label is scored through its
        descriptive phrase and mapped back afterwards.
        """
        phrases = list(prompts.values())
        label_of = {phrase: label for label, phrase in prompts.items()}
        results = self.clip.zero_shot_classify(pil_image, phrases, prompt_template=template)
        return [(label_of[phrase], score) for phrase, score in results if phrase in label_of]

    def _classify_type(self, pil_image: Image.Image) -> tuple[str, float]:
        """Identify the garment across the whole vocabulary at once.

        A two-stage variant (decide the silhouette, then name the garment within
        it) was measured against the curated test set and was not better: it
        scored the same on the ethnic/western axis but pulled full-body model
        photos towards one-piece labels, reading a suit as a pathani suit and a
        sweater as a jumpsuit, because the *photo* shows a whole body even when
        the garment does not cover one. The descriptive prompts are what carry
        the traditional wear here -- with them, every Ethnic test image resolves
        to an ethnic garment.
        """
        results = self._classify_prompted(pil_image, TYPE_PROMPTS, "a photo of {}")
        if not results:
            return "dress", 0.5
        top_type, confidence = results[0]
        return top_type, float(confidence)

    def extract_clothing_metadata(self, file_bytes: bytes, filename: str = "") -> dict[str, Any]:
        """
        Analyze image with OpenCV and CLIP to extract comprehensive clothing attributes and confidence scores.
        """
        start_time = time.perf_counter()
        logger.info("Starting AI metadata extraction (filename=%s)", filename)

        analysis_bytes = self._crop_to_subject(file_bytes)

        try:
            # CLAHE sharpens structure but shifts hue, so colour is read from the
            # un-enhanced image and everything else from the enhanced one.
            pil_image = self.preprocess_image(analysis_bytes)
            colour_image = self.preprocessor.preprocess_for_clip(analysis_bytes, enhance=False)
        except Exception as exc:
            logger.warning("Preprocessing failed, falling back to rule-based inference: %s", exc)
            return infer_metadata(filename)

        threshold = settings.clip_confidence_threshold

        # 1. Classify Clothing Type (silhouette first, then the garment within it)
        top_type, type_conf = self._classify_type(pil_image)
        if type_conf < threshold:
            # Fallback check against filename if confidence is low
            rule_meta = infer_metadata(filename)
            top_type = rule_meta["type"]

        # Determine Category based on type
        if top_type in ONE_PIECE_TYPES:
            category = "one_piece"
        elif top_type in OUTERWEAR_TYPES:
            category = "outerwear"
        elif top_type in ACCESSORY_TYPES:
            category = "accessories"
        else:
            category = "separates"
        cat_conf = max(type_conf, 0.75)
        is_ethnic = top_type in ETHNIC_TYPES

        # 2. Classify Primary Color
        color_results = self._classify_prompted(colour_image, COLOR_PROMPTS, "a photo of {} coloured clothing")
        top_color, color_conf = color_results[0] if color_results else ("blue", 0.5)
        secondary_colors = [c for c, p in color_results[1:3] if p > 0.18]

        # 3. Classify Pattern. Surface work (embroidery, zari, sequins) is
        # reported separately because an embroidered saree is still, underneath,
        # solid or floral, and the wardrobe filters read the base pattern.
        pattern_results = self._classify_prompted(pil_image, PATTERN_PROMPTS, "clothing with {}")
        top_pattern, pattern_conf = pattern_results[0] if pattern_results else ("solid", 0.5)
        embellishment = next(
            (p for p, score in pattern_results if p in EMBELLISHMENT_PATTERNS and score > 0.15),
            None,
        )
        base_pattern = top_pattern
        if top_pattern in EMBELLISHMENT_PATTERNS:
            base_pattern = next(
                (p for p, _ in pattern_results if p not in EMBELLISHMENT_PATTERNS),
                "solid",
            )

        # 4. Classify Season
        season_results = self.clip.zero_shot_classify(pil_image, CANDIDATE_SEASONS, prompt_template="clothing suitable for {} season")
        top_season, season_conf = season_results[0] if season_results else ("summer", 0.5)
        seasons = [top_season]
        if top_season != "all_season":
            seasons.extend([s for s, p in season_results[1:2] if p > 0.20])

        # 5. Classify Occasion
        occasion_results = self._classify_prompted(pil_image, OCCASION_PROMPTS, "clothing for {}")
        top_occasion, occ_conf = occasion_results[0] if occasion_results else ("casual", 0.5)
        occasions = [top_occasion]
        # Ethnic wear is rarely "casual" in the sense the filters mean; surface
        # the best festive reading alongside so it stays findable for those.
        if is_ethnic:
            festive = next(
                (o for o, _ in occasion_results if o in ETHNIC_OCCASIONS),
                "festive",
            )
            if festive not in occasions:
                occasions.append(festive)

        # 6. Sleeve Type (best effort)
        sleeve_results = self.clip.zero_shot_classify(pil_image, CANDIDATE_SLEEVES, prompt_template="clothing with {} sleeves")
        top_sleeve, _ = sleeve_results[0] if sleeve_results else ("short_sleeve", 0.4)

        # 7. Fabric (best effort; CLIP reads drape and sheen, not fibre)
        fabric_results = self._classify_prompted(pil_image, FABRIC_PROMPTS, "clothing made of {}")
        top_fabric, fabric_conf = fabric_results[0] if fabric_results else ("user_review_needed", 0.0)
        if fabric_conf < threshold:
            top_fabric = "user_review_needed"

        tags = [base_pattern, top_color, top_type]
        if embellishment and embellishment != base_pattern:
            tags.append(embellishment)
        if is_ethnic:
            tags.append("ethnic")

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "AI metadata extraction completed in %sms. Type=%s (%.2f), Color=%s (%.2f), Pattern=%s (%.2f), Fabric=%s",
            duration_ms, top_type, type_conf, top_color, color_conf, top_pattern, pattern_conf, top_fabric,
        )

        metadata = {
            "type": top_type,
            "category": category,
            "is_ethnic": is_ethnic,
            "primary_color": top_color,
            "secondary_colors": secondary_colors,
            "pattern": base_pattern,
            "embellishment": embellishment,
            "sleeve_type": top_sleeve,
            "fabric": top_fabric,
            "season": seasons,
            "occasion": occasions,
            "tags": tags,
            "confidence": {
                "category": round(float(cat_conf), 2),
                "type": round(float(type_conf), 2),
                "color": round(float(color_conf), 2),
                "pattern": round(float(pattern_conf), 2),
                "season": round(float(season_conf), 2),
                "occasion": round(float(occ_conf), 2),
                "fabric": round(float(fabric_conf), 2),
            },
        }
        metadata["suggested_name"] = suggest_item_name(metadata)
        return metadata

    def generate_image_embedding(self, file_bytes: bytes) -> list[float]:
        """Generate float32, L2-normalized 512-dimensional embedding for an image."""
        try:
            pil_image = self.preprocess_image(file_bytes)
            return self.clip.generate_image_embedding(pil_image)
        except Exception as exc:
            logger.warning("Image embedding extraction error: %s", exc)
            return generate_embedding("fallback_seed", dimensions=512)

    def generate_text_embedding(self, text: str) -> list[float]:
        """Generate float32, L2-normalized 512-dimensional embedding for text."""
        return self.clip.generate_text_embedding(text)


ai_service = AIService()


# Backward-compatible utilities

# Words that already read as a garment name; anything else gets no suffix.
_NAME_SKIP_PATTERNS = {"solid", "user_review_needed"}


def suggest_item_name(metadata: dict[str, Any]) -> str:
    """Build a human name from the detected attributes.

    "Maroon Embroidered Lehenga" rather than the uploaded file's name, which is
    usually IMG_2831. Falls back to the garment alone if colour is unknown.
    """
    color = str(metadata.get("primary_color") or "").strip()
    garment = str(metadata.get("type") or "item").strip()
    embellishment = str(metadata.get("embellishment") or "").strip()
    pattern = str(metadata.get("pattern") or "").strip()

    # Surface work is the more descriptive of the two when both are present.
    descriptor = embellishment or pattern
    if descriptor in _NAME_SKIP_PATTERNS:
        descriptor = ""

    parts = [part for part in (color, descriptor, garment) if part]
    return " ".join(part.title() for part in parts) or "Wardrobe Item"

def infer_metadata(filename: str) -> dict[str, object]:
    """Lightweight rule-based fallback metadata inference for filenames and legacy callers."""
    lower = filename.lower()
    color = next((candidate for candidate in CANDIDATE_COLORS if candidate in lower), "blue")

    if any(token in lower for token in ("shirt", "top", "tee", "blouse")):
        item_type = "top"
    elif any(token in lower for token in ("skirt", "jean", "pant", "trouser")):
        item_type = "bottom"
    elif any(token in lower for token in ("jacket", "coat", "blazer")):
        item_type = "outerwear"
    else:
        item_type = "dress"

    if "floral" in lower:
        pattern = "floral"
    elif "stripe" in lower:
        pattern = "striped"
    elif "check" in lower:
        pattern = "checked"
    else:
        pattern = "solid"

    metadata = {
        "type": item_type,
        "category": "one_piece" if item_type == "dress" else "separates",
        "is_ethnic": item_type in ETHNIC_TYPES,
        "primary_color": color,
        "secondary_colors": [],
        "pattern": pattern,
        "embellishment": None,
        "sleeve_type": "short_sleeve",
        "fabric": "user_review_needed",
        "season": ["all_season"] if color == "black" else ["summer", "spring"],
        "occasion": ["casual"],
        "tags": [pattern, color, item_type],
        "confidence": {"category": 0.85, "type": 0.74, "color": 0.82, "pattern": 0.66, "season": 0.70, "occasion": 0.70},
    }
    metadata["suggested_name"] = suggest_item_name(metadata)
    return metadata


def generate_embedding(seed: str, dimensions: int = 512) -> list[float]:
    """Generate normalized embedding vector from text or seed."""
    return ai_service.generate_text_embedding(seed)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity between two normalized float32 vectors."""
    if not left or not right:
        return 0.0
    return float(sum(a * b for a, b in zip(left, right)))


def wardrobe_summary(items: list[dict[str, object]]) -> dict[str, object]:
    """Aggregate wardrobe summary stats."""
    colors = Counter(str(item.get("primary_color", "unknown")) for item in items)
    types = Counter(str(item.get("type", "unknown")) for item in items)
    return {
        "total_items": len(items),
        "most_common_color": colors.most_common(1)[0][0] if colors else None,
        "category_distribution": dict(types),
        "least_used_items": sum(1 for item in items if int(item.get("wear_count", 0)) <= 2),
    }
