from typing import Any

from app.modules.ai.repository import embedding_repository
from app.modules.ai.service import ai_service, cosine_similarity, generate_embedding, infer_metadata
from app.modules.shopping.repository import shopping_repository
from app.modules.wardrobe.service import wardrobe_service


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
                metadata_score += 0.28
            if item.get("type") == query_metadata["type"]:
                metadata_score += 0.28
            if item.get("pattern") == query_metadata["pattern"]:
                metadata_score += 0.16

            similarity = max(0.0, min(0.98, (visual_score + 1.0) / 2.0 * 0.28 + metadata_score))
            matches.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "image_url": item.get("image_url", ""),
                    "similarity": round(similarity, 3),
                    "reason": self._build_reason(item, query_metadata),
                }
            )

        matches.sort(key=lambda match: match["similarity"], reverse=True)
        highest = matches[0]["similarity"] if matches else 0.0

        if highest >= 0.85:
            decision = "similar_found"
        elif highest >= 0.70:
            decision = "review_matches"
        else:
            decision = "no_strong_duplicate"

        top_matches = matches[:5]

        # Log audit trail to MongoDB
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
