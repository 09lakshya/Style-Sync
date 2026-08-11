from typing import Any

from app.modules.wardrobe.service import wardrobe_service


class RecommendationService:
    async def get_outfit_recommendations(
        self,
        user_id: str,
        occasion: str | None = None,
        season: str | None = None,
    ) -> dict[str, Any]:
        """Generate explainable outfit recommendations tailored to the user's wardrobe."""
        items = await wardrobe_service.get_user_items(user_id)
        if not items:
            return {"recommendations": []}

        # Rank items with lowest wear count first to promote unused clothing
        ranked = sorted(items, key=lambda item: int(item.get("wear_count", 0)))
        recommendations: list[dict[str, Any]] = []

        for item in ranked[:4]:
            reasons = ["Promotes a less-used wardrobe item"]
            if occasion and occasion.lower() in [occ.lower() for occ in item.get("occasion", [])]:
                reasons.append(f"Matches {occasion} occasion")
            if season and season.lower() in [s.lower() for s in item.get("season", [])]:
                reasons.append(f"Suitable for {season}")
            if item.get("primary_color") in {"black", "white", "blue", "beige", "grey"}:
                reasons.append("Versatile neutral color")

            score = round(0.68 + min(len(reasons) * 0.06, 0.24), 2)
            recommendations.append(
                {
                    "items": [{"id": item["id"], "name": item["name"]}],
                    "score": score,
                    "reasons": reasons,
                }
            )

        return {"recommendations": recommendations}


recommendation_service = RecommendationService()
