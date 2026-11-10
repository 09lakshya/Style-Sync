import io
import logging
from typing import Any

from app.modules.recommendations import style_rules
from app.modules.wardrobe.service import wardrobe_service

logger = logging.getLogger("stylesync.recommendations")


class OutfitAnalysisService:
    """Analyse a single uploaded outfit image.

    Supports two tiers:
      - Tier 1 (State of the art): Google Gemini Multimodal Vision AI for deep
        ensemble recognition, aesthetic classification, color harmony, and personalized
        stylist critiques.
      - Tier 2 (Local / Fallback): MobileNetV2 + CLIP zero-shot neural models with
        attribute extraction and explainable styling rules.
    """

    async def analyze(
        self,
        file_bytes: bytes,
        filename: str,
        gender: str | None = None,
        profile_gender: str | None = None,
    ) -> dict[str, Any]:
        # --- Tier 1: Try Gemini Vision if configured -------------------------
        from app.modules.ai.gemini_service import gemini_service

        if gemini_service.is_configured:
            lower = filename.lower()
            mime_type = (
                "image/png"
                if lower.endswith(".png")
                else "image/webp"
                if lower.endswith(".webp")
                else "image/jpeg"
            )
            gender_hint = gender or profile_gender
            gemini_result = await gemini_service.analyze_outfit(
                file_bytes=file_bytes,
                mime_type=mime_type,
                gender_override=gender_hint,
            )
            if gemini_result:
                return self._format_gemini_response(gemini_result, gender, profile_gender)

        # --- Tier 2: Local AI Model Pipeline ---------------------------------
        return await self._analyze_local(file_bytes, filename, gender, profile_gender)

    def _format_gemini_response(
        self,
        gemini_res: dict[str, Any],
        gender_override: str | None,
        profile_gender: str | None,
    ) -> dict[str, Any]:
        detected_gender = gemini_res.get("gender", "unisex")
        if gender_override in style_rules.VALID_GENDERS:
            gender_info = {"value": gender_override, "source": "provided", "confidence": None}
        elif profile_gender in style_rules.VALID_GENDERS and detected_gender == "unisex":
            gender_info = {"value": profile_gender, "source": "profile", "confidence": 0.9}
        else:
            gender_info = {
                "value": detected_gender if detected_gender in style_rules.VALID_GENDERS else "unisex",
                "source": "detected",
                "confidence": 0.95,
            }

        aesthetic = gemini_res.get("aesthetic") or "Smart Casual"
        category = gemini_res.get("category") or "Casual"
        palette = gemini_res.get("color_palette") or {}
        primary_color = palette.get("primary_color", "")
        secondary_colors = palette.get("secondary_colors", []) or []

        detected_pieces = gemini_res.get("detected_pieces", [])
        first_type = detected_pieces[0].get("name") if detected_pieces else "outfit"
        first_pattern = detected_pieces[0].get("pattern", "solid") if detected_pieces else "solid"

        recs = gemini_res.get("styling_recommendations") or {}
        slots: dict[str, list[str]] = {
            "footwear": recs.get("footwear", []),
            "bag": recs.get("bag", []),
            "earrings": recs.get("jewellery_and_watches", [])[:2],
            "necklace": recs.get("jewellery_and_watches", [])[1:3],
            "bracelet": recs.get("jewellery_and_watches", [])[2:4],
            "watch": [item for item in recs.get("jewellery_and_watches", []) if "watch" in item.lower()] or ["Minimal dress watch"],
            "other": recs.get("other_accessories", []) + recs.get("layers_and_outerwear", []),
        }

        critique = gemini_res.get("stylist_critique") or {}
        strengths = critique.get("strengths", [])
        tips = critique.get("elevation_tips", [])
        reasoning = strengths + [f"Stylist Tip: {tip}" for tip in tips]

        return {
            "engine": "gemini_multimodal_vision",
            "outfit_score": gemini_res.get("outfit_score", 85),
            "aesthetic": aesthetic,
            "summary": gemini_res.get("summary", ""),
            "detected_pieces": detected_pieces,
            "color_palette": palette,
            "silhouette_and_proportions": gemini_res.get("silhouette_and_proportions", {}),
            "stylist_critique": critique,
            "styling_recommendations": recs,
            "classification": {
                "available": True,
                "predicted_category": category,
                "labels": [aesthetic, category] if aesthetic != category else [category],
                "prediction_confidence": 0.96,
                "model_version": gemini_res.get("model_used", "gemini-2.5-flash"),
            },
            "attributes": {
                "available": True,
                "reason": None,
                "type": first_type,
                "primary_color": primary_color,
                "secondary_colors": secondary_colors,
                "pattern": first_pattern,
                "sleeve_type": None,
                "season": gemini_res.get("seasons", ["all_season"]),
                "occasion": gemini_res.get("occasions", [category.lower()]),
                "confidence": {"gemini": 0.95},
            },
            "gender": gender_info,
            "tags": gemini_res.get("tags") or [f"#{aesthetic.lower().replace(' ', '-')}"],
            "styling": {
                "available": True,
                "style": aesthetic,
                "metal_tone": "gold" if any("gold" in s.lower() for s in str(palette)) else "silver",
                "reasoning": reasoning,
                "slots": slots,
            },
            "source_note": (
                "Powered by Google Gemini Multimodal Vision AI. Analysis includes full ensemble piece breakdown, "
                "aesthetic classification, color harmony assessment, and personalized stylist critique."
            ),
        }

    async def _analyze_local(
        self,
        file_bytes: bytes,
        filename: str,
        gender: str | None = None,
        profile_gender: str | None = None,
    ) -> dict[str, Any]:
        from app.modules.ai.service import ai_service

        attributes_available = ai_service.clip.is_loaded
        attributes: dict[str, Any] = (
            ai_service.extract_clothing_metadata(file_bytes=file_bytes, filename=filename)
            if attributes_available
            else {}
        )

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

        if gender in style_rules.VALID_GENDERS:
            gender_info = {"value": gender, "source": "provided", "confidence": None}
        else:
            detected, gender_conf = ai_service.detect_styling_gender(file_bytes)
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

        aesthetic = styling.get("style") or predicted_category or "Casual Style"
        outfit_score = 75 if predicted_category else 50
        detected_pieces = []
        if attributes.get("type"):
            detected_pieces.append({
                "slot": attributes.get("category", "garment"),
                "name": attributes.get("suggested_name") or attributes.get("type"),
                "color": primary_color,
                "pattern": pattern,
                "details": f"Sleeve: {attributes.get('sleeve_type') or 'standard'}",
            })

        color_palette = {
            "primary_color": primary_color,
            "secondary_colors": secondary_colors,
            "color_chips": [{"name": primary_color.title(), "hex": "#7d847d"}],
            "harmony_type": "Neutral Anchor" if primary_color in {"black", "white", "grey", "navy"} else "Tonal",
            "harmony_evaluation": f"Dominated by {primary_color} tones.",
        }

        critique = {
            "strengths": styling.get("reasoning", []),
            "elevation_tips": [
                "Pair with contrasting footwear to define the silhouette.",
                "Add subtle jewelry matching the recommended metal tone.",
            ],
        }

        from app.core.config import settings

        gemini_hint = (
            ""
            if settings.is_gemini_configured
            else " (Tip: add a free GEMINI_API_KEY to backend/.env for deep Gemini Vision stylist analysis)."
        )

        return {
            "engine": "local_vision_models",
            "outfit_score": outfit_score,
            "aesthetic": aesthetic,
            "summary": f"Analyzed as a {aesthetic} ensemble.",
            "detected_pieces": detected_pieces,
            "color_palette": color_palette,
            "silhouette_and_proportions": {
                "fit": "Standard",
                "evaluation": "Balanced silhouette.",
            },
            "stylist_critique": critique,
            "styling_recommendations": {
                "footwear": styling.get("slots", {}).get("footwear", []),
                "bag": styling.get("slots", {}).get("bag", []),
                "jewellery_and_watches": (
                    styling.get("slots", {}).get("earrings", [])
                    + styling.get("slots", {}).get("watch", [])
                ),
                "layers_and_outerwear": styling.get("slots", {}).get("other", []),
                "other_accessories": styling.get("slots", {}).get("other", []),
            },
            "classification": {
                "available": predicted_category is not None,
                "predicted_category": predicted_category,
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
                f"Category and attributes are local model output. Styling suggestions are rule-based, derived from those attributes.{gemini_hint}"
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
