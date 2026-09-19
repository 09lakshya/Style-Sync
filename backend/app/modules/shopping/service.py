from typing import Any

from app.modules.ai.repository import embedding_repository
from app.modules.ai.service import ai_service, cosine_similarity, generate_embedding, infer_metadata
from app.modules.shopping.repository import shopping_repository
from app.modules.wardrobe.service import wardrobe_service

# --- Scoring constants -------------------------------------------------------
# The weights are structural: duplicate detection is driven by visual similarity,
# with metadata as a secondary signal only.
#
# The thresholds are CALIBRATED against real garment photographs by
# backend/scripts/calibrate_similarity.py (see model/artifacts/
# similarity_calibration.json). Measured over 1,596 pairs from the curated test
# split:
#
#     identical    median 1.0000
#     same_class   median 0.7789   max 0.9271
#     diff_class   median 0.7181   max 0.9185
#
# Same-category and different-category pairs separate cleanly, and every one of
# the 1,540 non-duplicate pairs falls below 0.9271 while true duplicates sit at
# 1.0. VISUAL_DUPLICATE_GATE is placed at 0.95 -- above every observed
# non-duplicate, with 0.05 of margin before a true duplicate. Re-run the
# calibration script whenever the dataset changes.

# Maximum attainable metadata agreement (colour + type + pattern), used to normalise.
COLOR_MATCH_SCORE = 0.28
TYPE_MATCH_SCORE = 0.28
PATTERN_MATCH_SCORE = 0.16
MAX_METADATA_SCORE = COLOR_MATCH_SCORE + TYPE_MATCH_SCORE + PATTERN_MATCH_SCORE
ATTRIBUTE_MATCH_SCORES = {"color": COLOR_MATCH_SCORE, "type": TYPE_MATCH_SCORE, "pattern": PATTERN_MATCH_SCORE}

VISUAL_WEIGHT = 0.75
METADATA_WEIGHT = 0.25

# Never report absolute certainty, even for a byte-identical image.
MAX_REPORTED_SIMILARITY = 0.98

DUPLICATE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.70
# A match may only be called a duplicate if the images themselves agree. Without this
# gate, identical metadata alone reaches the duplicate threshold. Calibrated: sits
# above the highest observed non-duplicate pair (0.9271).
VISUAL_DUPLICATE_GATE = 0.95


def score_match(visual_cosine: float, metadata_score: float) -> float:
    """Combine CLIP visual agreement with metadata agreement into a 0..1 similarity.

    visual_cosine is a raw cosine in [-1, 1]; negative values carry no meaning for
    image-image comparison and are floored to 0.
    """
    visual = max(0.0, min(1.0, visual_cosine))
    metadata_norm = max(0.0, min(1.0, metadata_score / MAX_METADATA_SCORE)) if MAX_METADATA_SCORE else 0.0
    combined = VISUAL_WEIGHT * visual + METADATA_WEIGHT * metadata_norm
    return max(0.0, min(MAX_REPORTED_SIMILARITY, combined))


def _normalise_label(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def matching_attributes(item: dict[str, Any], query_metadata: dict[str, Any]) -> list[str]:
    """Metadata fields on which the wardrobe item agrees with the query.

    Compared case-insensitively: wardrobe metadata can be edited by hand
    ("White", "Solid") while the model emits lowercase labels.
    """
    return [
        name
        for name, field in (("color", "primary_color"), ("type", "type"), ("pattern", "pattern"))
        if _normalise_label(item.get(field)) and _normalise_label(item.get(field)) == _normalise_label(query_metadata.get(field))
    ]


def decide_outcome(highest_similarity: float, highest_visual: float) -> str:
    """Map the best match onto a verdict. Duplicates require visual agreement."""
    if highest_similarity >= DUPLICATE_THRESHOLD and highest_visual >= VISUAL_DUPLICATE_GATE:
        return "similar_found"
    if highest_similarity >= REVIEW_THRESHOLD:
        return "review_matches"
    return "no_strong_duplicate"


class ShoppingService:
    async def check_duplicate_purchase(
        self,
        user_id: str,
        filename: str,
        file_bytes: bytes | None = None,
        image_url: str = "",
    ) -> dict[str, Any]:
        """Compare a shopping image against user's wardrobe items and embeddings."""
        if file_bytes is not None:
            query_metadata = ai_service.extract_clothing_metadata(file_bytes=file_bytes, filename=filename)
            query_embedding = ai_service.generate_image_embedding(file_bytes)
        else:
            query_metadata = infer_metadata(filename)
            query_embedding = generate_embedding(filename)

        items = await wardrobe_service.get_user_items(user_id)
        user_embeddings = await embedding_repository.get_by_user_id(user_id)
        embedding_map = {str(emb["item_id"]): emb.get("embedding", []) for emb in user_embeddings}

        matches: list[dict[str, Any]] = []
        for item in items:
            item_id = str(item["id"])
            embedding = embedding_map.get(item_id, item.get("embedding", []))
            visual_score = cosine_similarity(query_embedding, embedding if isinstance(embedding, list) else [])

            matched = matching_attributes(item, query_metadata)
            metadata_score = sum(ATTRIBUTE_MATCH_SCORES[name] for name in matched)

            similarity = score_match(visual_score, metadata_score)
            matches.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "image_url": item.get("image_url", ""),
                    "similarity": round(similarity, 3),
                    "visual_similarity": round(max(0.0, min(1.0, visual_score)), 3),
                    "reason": self._build_reason(matched),
                }
            )

        matches.sort(key=lambda match: match["similarity"], reverse=True)
        highest = matches[0]["similarity"] if matches else 0.0
        highest_visual = matches[0]["visual_similarity"] if matches else 0.0

        decision = decide_outcome(highest, highest_visual)

        top_matches = matches[:5]

        # Log audit trail to database
        await shopping_repository.log_check(
            user_id=user_id,
            query_image_url=image_url,
            similar_items=top_matches,
            decision=decision,
            highest_similarity=highest,
        )

        return {
            "decision": decision,
            "highest_similarity": highest,
            "similar_items": top_matches,
        }

    def _build_reason(self, reasons: list[str]) -> str:
        return f"Matched on {', '.join(reasons)}." if reasons else "Closest vector match in the wardrobe."


shopping_service = ShoppingService()
