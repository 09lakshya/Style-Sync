from typing import Any

from app.modules.ai.repository import embedding_repository
from app.modules.ai.service import ai_service, cosine_similarity, generate_embedding, infer_metadata
from app.modules.shopping.repository import shopping_repository
from app.modules.wardrobe.service import wardrobe_service

# --- Scoring constants -------------------------------------------------------
# PROVISIONAL. These weights are structural, not calibrated: they encode the rule
# that duplicate detection must be driven by visual similarity, with metadata as a
# secondary signal only. The numeric thresholds below still need calibration against
# real garment photographs. Attempting to calibrate them on the current curated
# dataset is not meaningful -- its images are procedurally generated colour blocks,
# and measured CLIP cosine over them does not separate same-category from
# different-category pairs (medians 0.891 vs 0.883, fully overlapping ranges).

# Maximum attainable metadata agreement (colour + type + pattern), used to normalise.
COLOR_MATCH_SCORE = 0.28
TYPE_MATCH_SCORE = 0.28
PATTERN_MATCH_SCORE = 0.16
MAX_METADATA_SCORE = COLOR_MATCH_SCORE + TYPE_MATCH_SCORE + PATTERN_MATCH_SCORE

VISUAL_WEIGHT = 0.75
METADATA_WEIGHT = 0.25

# Never report absolute certainty, even for a byte-identical image.
MAX_REPORTED_SIMILARITY = 0.98

DUPLICATE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.70
# A match may only be called a duplicate if the images themselves agree. Without this
# gate, identical metadata alone reaches the duplicate threshold.
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

            metadata_score = 0.0
            if item.get("primary_color") == query_metadata["primary_color"]:
                metadata_score += COLOR_MATCH_SCORE
            if item.get("type") == query_metadata["type"]:
                metadata_score += TYPE_MATCH_SCORE
            if item.get("pattern") == query_metadata["pattern"]:
                metadata_score += PATTERN_MATCH_SCORE

            similarity = score_match(visual_score, metadata_score)
            matches.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "image_url": item.get("image_url", ""),
                    "similarity": round(similarity, 3),
                    "visual_similarity": round(max(0.0, min(1.0, visual_score)), 3),
                    "reason": self._build_reason(item, query_metadata),
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

    def _build_reason(self, item: dict[str, Any], query_metadata: dict[str, Any]) -> str:
        reasons = []
        if item.get("primary_color") == query_metadata["primary_color"]:
            reasons.append("color")
        if item.get("type") == query_metadata["type"]:
            reasons.append("type")
        if item.get("pattern") == query_metadata["pattern"]:
            reasons.append("pattern")
        return f"Matched on {', '.join(reasons)}." if reasons else "Closest vector match in the wardrobe."


shopping_service = ShoppingService()
