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

    async def analyze(
        self,
        file_bytes: bytes,
        filename: str,
        gender: str | None = None,
        profile_gender: str | None = None,
    ) -> dict[str, Any]:
        from app.modules.ai.service import ai_service

        # 1. Real CLIP attribute extraction (also performs the preprocessing).
        # Without CLIP the extractor still answers, but from a uniform fallback
        # that lands on the first label of every list -- "dress, blue, solid" for
        # any photo. That is not a reading of this image, so it is not reported
        # as one.
        attributes_available = ai_service.clip.is_loaded
        attributes: dict[str, Any] = (
            ai_service.extract_clothing_metadata(file_bytes=file_bytes, filename=filename)
            if attributes_available
            else {}
        )

        # 2. Real classifier prediction, if the model is loaded.
        predicted_category: str | None = None
        confidence: float | None = None
        model_version: str | None = None
        labels: list[str] = []
        try:
            from PIL import Image

            from app.modules.ai.classifier_manager import classifier_manager

            if classifier_manager.is_loaded:
                pil = Image.open(io.BytesIO(file_bytes))
                axes = classifier_manager.predict_axes(pil)
                if axes is not None:
                    probabilities = axes["probabilities"]
                    predicted_category, confidence = classifier_manager.single_label(probabilities)
                    model_version = classifier_manager.model_version
                    if predicted_category:
                        labels = [predicted_category]
                    # The single label ranks occasion over tradition, so a
                    # sherwani reads "Formal" and gets styled with oxfords and a
                    # tie. Tradition decides the styling more than occasion does,
                    # but the classifier's ethnic head also fires on some western
                    # pieces (a plain black jacket at 0.92), so it only leads when
                    # CLIP independently named an ethnic garment.
                    if (
                        axes.get("tradition") == "ethnic"
                        and attributes.get("is_ethnic")
                        and predicted_category != "Ethnic"
                    ):
                        predicted_category = "Ethnic"
                        confidence = probabilities.get("ethnic")
                        labels = ["Ethnic", *labels]
        except Exception as exc:
            logger.warning("Outfit classification failed: %s", exc)

        primary_color = attributes.get("primary_color", "")
        secondary_colors = attributes.get("secondary_colors", []) or []
        pattern = attributes.get("pattern", "")
        seasons = attributes.get("season", []) or []

        # 3. Styling gender. An explicit override wins; otherwise CLIP reads the
        # garment. The profile answer is the tie-break rather than the first
        # choice: it says who the wardrobe belongs to, not what is in this photo,
        # and people own clothes cut for more than one convention.
        if gender in style_rules.VALID_GENDERS:
            gender_info = {"value": gender, "source": "provided", "confidence": None}
        else:
            detected, gender_conf = ai_service.detect_styling_gender(file_bytes)
            # A None confidence means nothing was read (CLIP down or the image
            # unusable), as opposed to a reading too close to call.
            if detected == "unisex" and profile_gender in style_rules.VALID_GENDERS:
                gender_info = {
                    "value": profile_gender,
                    "source": "profile",
                    "confidence": gender_conf,
                }
            elif gender_conf is None:
                gender_info = {"value": "unisex", "source": "unavailable", "confidence": None}
            else:
                gender_info = {"value": detected, "source": "detected", "confidence": gender_conf}

        # 4. Rule-based styling. Only possible once a category is known.
        if predicted_category:
            styling = style_rules.recommend_accessories(
                category=predicted_category,
                gender=gender_info["value"],
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
                # Every label worth showing, styling label first.
                "labels": labels,
                "prediction_confidence": confidence,
                "model_version": model_version,
            },
            "attributes": {
                "available": attributes_available,
                "reason": (
                    None
                    if attributes_available
                    else "The attribute model is not loaded, so type, colour and pattern could not be read."
                ),
                "type": attributes.get("type"),
                "primary_color": primary_color,
                "secondary_colors": secondary_colors,
                "pattern": pattern,
                "sleeve_type": attributes.get("sleeve_type"),
                "season": seasons,
                "occasion": attributes.get("occasion", []),
                "confidence": attributes.get("confidence", {}),
            },
            "gender": gender_info,
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
