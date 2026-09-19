import logging
import time
from collections import Counter
from typing import Any
from PIL import Image

from app.core.config import settings
from app.modules.ai.clip_manager import clip_manager
from app.modules.ai.preprocessor import preprocessor

logger = logging.getLogger("stylesync.ai.service")

# Candidate label sets for Zero-Shot attribute extraction
CANDIDATE_TYPES = [
    # Western
    "dress", "shirt", "blouse", "top", "t-shirt",
    "skirt", "pants", "jeans", "shorts",
    "jacket", "coat", "blazer", "sweater", "hoodie",
    # Ethnic / South Asian. Zero-shot classification can only return a label it
    # was given, so without these an anarkali or saree is forced onto the nearest
    # Western word -- typically "skirt" or "dress". The wardrobe has an Ethnic
    # category, so the vocabulary has to cover it.
    "saree", "lehenga", "anarkali", "salwar kameez", "kurta", "kurti",
    "churidar", "sherwani", "dupatta",
]

CANDIDATE_CATEGORIES = ["one_piece", "separates", "outerwear", "accessories"]

# Garments worn as a single complete outfit rather than separates.
ONE_PIECE_TYPES = {
    "dress", "jumpsuit", "romper",
    "saree", "lehenga", "anarkali", "salwar kameez", "sherwani",
}
OUTERWEAR_TYPES = {"jacket", "coat", "blazer"}
ACCESSORY_TYPES = {"dupatta"}

CANDIDATE_COLORS = [
    "blue", "white", "black", "green", "red", "pink",
    "yellow", "beige", "navy", "grey", "brown", "purple", "orange",
]

CANDIDATE_PATTERNS = [
    "solid", "floral", "striped", "checked", "plaid",
    "polka dot", "graphic", "animal print",
]

CANDIDATE_SEASONS = ["summer", "winter", "spring", "fall", "all_season"]

CANDIDATE_OCCASIONS = ["casual", "formal", "party", "work", "day_out", "evening", "sports"]

CANDIDATE_SLEEVES = ["sleeveless", "short_sleeve", "long_sleeve", "three_quarter"]


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

    def extract_clothing_metadata(self, file_bytes: bytes, filename: str = "") -> dict[str, Any]:
        """
        Analyze image with OpenCV and CLIP to extract comprehensive clothing attributes and confidence scores.
        """
        start_time = time.perf_counter()
        logger.info("Starting AI metadata extraction (filename=%s)", filename)

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

        try:
            # CLAHE sharpens structure but shifts hue, so colour is read from the
            # un-enhanced image and everything else from the enhanced one.
            pil_image = self.preprocess_image(analysis_bytes)
            colour_image = self.preprocessor.preprocess_for_clip(analysis_bytes, enhance=False)
        except Exception as exc:
            logger.warning("Preprocessing failed, falling back to rule-based inference: %s", exc)
            return infer_metadata(filename)

        threshold = settings.clip_confidence_threshold

        # 1. Classify Clothing Type
        type_results = self.clip.zero_shot_classify(pil_image, CANDIDATE_TYPES, prompt_template="a photo of a {}")
        top_type, type_conf = type_results[0] if type_results else ("dress", 0.5)
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

        # 2. Classify Primary Color
        color_results = self.clip.zero_shot_classify(colour_image, CANDIDATE_COLORS, prompt_template="a photo of {} colored clothing")
        top_color, color_conf = color_results[0] if color_results else ("blue", 0.5)
        secondary_colors = [c for c, p in color_results[1:3] if p > 0.18]

        # 3. Classify Pattern
        pattern_results = self.clip.zero_shot_classify(pil_image, CANDIDATE_PATTERNS, prompt_template="clothing with a {} pattern")
        top_pattern, pattern_conf = pattern_results[0] if pattern_results else ("solid", 0.5)

        # 4. Classify Season
        season_results = self.clip.zero_shot_classify(pil_image, CANDIDATE_SEASONS, prompt_template="clothing suitable for {} season")
        top_season, season_conf = season_results[0] if season_results else ("summer", 0.5)
        seasons = [top_season]
        if top_season != "all_season":
            seasons.extend([s for s, p in season_results[1:2] if p > 0.20])

        # 5. Classify Occasion
        occasion_results = self.clip.zero_shot_classify(pil_image, CANDIDATE_OCCASIONS, prompt_template="clothing for a {} occasion")
        top_occasion, occ_conf = occasion_results[0] if occasion_results else ("casual", 0.5)
        occasions = [top_occasion]

        # 6. Sleeve Type (best effort)
        sleeve_results = self.clip.zero_shot_classify(pil_image, CANDIDATE_SLEEVES, prompt_template="clothing with {} sleeves")
        top_sleeve, _ = sleeve_results[0] if sleeve_results else ("short_sleeve", 0.4)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "AI metadata extraction completed in %sms. Type=%s (%.2f), Color=%s (%.2f), Pattern=%s (%.2f)",
            duration_ms, top_type, type_conf, top_color, color_conf, top_pattern, pattern_conf,
        )

        return {
            "type": top_type,
            "category": category,
            "primary_color": top_color,
            "secondary_colors": secondary_colors,
            "pattern": top_pattern,
            "sleeve_type": top_sleeve,
            "fabric": "user_review_needed",
            "season": seasons,
            "occasion": occasions,
            "tags": [top_pattern, top_color, top_type],
            "confidence": {
                "category": round(float(cat_conf), 2),
                "type": round(float(type_conf), 2),
                "color": round(float(color_conf), 2),
                "pattern": round(float(pattern_conf), 2),
                "season": round(float(season_conf), 2),
                "occasion": round(float(occ_conf), 2),
            },
        }

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

    return {
        "type": item_type,
        "category": "one_piece" if item_type == "dress" else "separates",
        "primary_color": color,
        "secondary_colors": [],
        "pattern": pattern,
        "fabric": "user_review_needed",
        "season": ["all_season"] if color == "black" else ["summer", "spring"],
        "occasion": ["casual"],
        "tags": [pattern, color, item_type],
        "confidence": {"category": 0.85, "type": 0.74, "color": 0.82, "pattern": 0.66, "season": 0.70, "occasion": 0.70},
    }


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
