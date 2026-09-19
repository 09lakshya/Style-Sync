import io
import logging
from typing import Any

from app.modules.recommendations import style_rules
from app.modules.wardrobe.service import wardrobe_service

logger = logging.getLogger("stylesync.recommendations")


class OutfitAnalysisService:
    """Analyse a single uploaded outfit image.

    Combines two clearly separated sources:
      - model output: the trained classifier's category/confidence, and CLIP
        zero-shot attributes (type, colour, pattern, season, occasion)
      - rule output: accessory suggestions looked up from those attributes

    The response keeps them in distinct fields so the client can label them
    honestly. Nothing in the rule half is presented as a prediction.
    """

    async def analyze(self, file_bytes: bytes, filename: str, gender: str = "unisex") -> dict[str, Any]:
        from app.modules.ai.service import ai_service

        # 1. Real CLIP attribute extraction (also performs the preprocessing).
        attributes = ai_service.extract_clothing_metadata(file_bytes=file_bytes, filename=filename)

        # 2. Real classifier prediction, if the model is loaded.
        predicted_category: str | None = None
        confidence: float | None = None
        model_version: str | None = None
        try:
            from PIL import Image

            from app.modules.ai.classifier_manager import classifier_manager

            if classifier_manager.is_loaded:
                pil = Image.open(io.BytesIO(file_bytes))
                predicted_category, confidence = classifier_manager.predict(pil)
                model_version = classifier_manager.model_version
        except Exception as exc:
            logger.warning("Outfit classification failed: %s", exc)

        primary_color = attributes.get("primary_color", "")
        secondary_colors = attributes.get("secondary_colors", []) or []
        pattern = attributes.get("pattern", "")
        seasons = attributes.get("season", []) or []

        # 3. Rule-based styling. Only possible once a category is known.
        if predicted_category:
            styling = style_rules.recommend_accessories(
                category=predicted_category,
                gender=gender,
                primary_color=primary_color,
                secondary_colors=secondary_colors,
            )
            tags = style_rules.build_tags(predicted_category, primary_color, pattern, seasons)
        else:
            styling = {
                "available": False,
                "reason": "Classification unavailable, so no styling rules could be applied.",
                "slots": {},
            }
            tags = []

        return {
            "classification": {
                "available": predicted_category is not None,
                "predicted_category": predicted_category,
                "prediction_confidence": confidence,
                "model_version": model_version,
            },
            "attributes": {
                "type": attributes.get("type"),
                "primary_color": primary_color,
                "secondary_colors": secondary_colors,
                "pattern": pattern,
                "sleeve_type": attributes.get("sleeve_type"),
                "season": seasons,
                "occasion": attributes.get("occasion", []),
                "confidence": attributes.get("confidence", {}),
            },
            "tags": tags,
            "styling": styling,
            "source_note": (
                "Category and attributes are model output. Styling suggestions are "
                "rule-based, derived from those attributes."
            ),
        }


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
outfit_analysis_service = OutfitAnalysisService()
