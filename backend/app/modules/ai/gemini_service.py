import base64
import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("stylesync.ai.gemini")

OUTFIT_ANALYSIS_PROMPT = """You are an elite, world-class personal fashion stylist and computer vision fashion analyst.
Analyze this outfit image thoroughly and return a comprehensive, highly accurate JSON evaluation.

Rules for your analysis:
1. Identify all visible clothing pieces worn in the image (upper wear, lower wear, footwear, outerwear, and accessories).
2. Determine the precise aesthetic / style subgenre (e.g., "Smart Casual", "Urban Streetwear", "Modern Minimalist", "Indo-Western Fusion", "Old Money / Quiet Luxury", "Bohemian Chic", "Athleisure", "Classic Tailored").
3. Extract the exact color palette with realistic hex codes and analyze color harmony (e.g., Complementary, Monochromatic, Analogous, High Contrast, Neutral Anchor).
4. Evaluate silhouette, fit, and proportions.
5. Provide a realistic Outfit Score (0-100) based on aesthetic harmony, color balance, and fit.
6. Provide specific, personalized stylist critique:
   - strengths: 2-3 genuine compliments on why this look works.
   - elevation_tips: 2-3 concrete, actionable styling tips to elevate or refine this exact outfit (e.g., cuffing trousers, tucking shirts, layering specific jackets, proportion fixes).
7. Recommend complementary accessories, footwear, bags, and layers that specifically harmonize with this outfit's aesthetic and palette (do NOT give generic advice).

Return ONLY valid JSON matching this exact structure:
{
  "aesthetic": "Aesthetic style name",
  "category": "Casual" | "Formal" | "Party" | "Ethnic" | "Western" | "Summer" | "Winter",
  "outfit_score": 85,
  "summary": "1-2 sentence overview of the outfit's vibe and cohesion.",
  "detected_pieces": [
    {
      "slot": "top" | "bottom" | "outerwear" | "one_piece" | "footwear" | "accessory",
      "name": "Detailed descriptive name of the piece",
      "color": "Color name",
      "pattern": "solid" | "striped" | "printed" | "embroidered" | "checked" | "floral" | "other",
      "details": "Fit, cut, fabric or styling notes"
    }
  ],
  "color_palette": {
    "primary_color": "Dominant color name",
    "secondary_colors": ["Secondary color 1", "Secondary color 2"],
    "color_chips": [
      {"name": "Color name", "hex": "#HEXCODE"}
    ],
    "harmony_type": "Monochromatic" | "Complementary" | "Analogous" | "Neutral Anchor" | "High Contrast" | "Warm Tonal" | "Cool Tonal",
    "harmony_evaluation": "1-2 sentence explanation of color interaction."
  },
  "silhouette_and_proportions": {
    "fit": "Balanced" | "Relaxed" | "Structured" | "Oversized" | "Fitted",
    "evaluation": "Critique of how top and bottom proportions and draping balance."
  },
  "occasions": ["Occasion 1", "Occasion 2"],
  "seasons": ["Season 1", "Season 2"],
  "gender": "female" | "male" | "unisex",
  "stylist_critique": {
    "strengths": [
      "Specific praise 1",
      "Specific praise 2"
    ],
    "elevation_tips": [
      "Actionable styling tip 1",
      "Actionable styling tip 2"
    ]
  },
  "styling_recommendations": {
    "footwear": ["Footwear recommendation 1", "Footwear recommendation 2"],
    "bag": ["Bag recommendation 1", "Bag recommendation 2"],
    "jewellery_and_watches": ["Jewellery recommendation 1", "Jewellery recommendation 2"],
    "layers_and_outerwear": ["Layering piece 1", "Layering piece 2"],
    "other_accessories": ["Accessory 1", "Accessory 2"]
  },
  "tags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
}
"""

CLOTHING_ITEM_DETECTION_PROMPT = """You are an expert fashion stylist and computer vision garment analyst.
Analyze this single clothing item image and extract precise attributes.

Rules:
1. name: Descriptive, elegant fashion title (e.g. "Vintage Washed Oversized Graphic Tee", "Slim Fit Dark Indigo Chinos", "Hand-Embroidered Raw Silk Kurti", "Pleated Linen Wide-Leg Trousers").
2. type: The single best garment type from:
   ["shirt", "blouse", "top", "t-shirt", "skirt", "pants", "jeans", "shorts", "jumpsuit", "romper", "jacket", "coat", "blazer", "sweater", "hoodie", "cardigan", "waistcoat", "saree", "lehenga", "choli", "anarkali", "salwar kameez", "patiala salwar", "churidar", "palazzo", "sharara", "gharara", "kurta", "kurti", "angrakha", "sherwani", "bandhgala", "nehru jacket", "pathani suit", "dhoti", "lungi", "dupatta", "dress", "gown"]
3. type_alternatives: 2-3 other plausible alternative garment type labels with confidence scores (e.g. [["t-shirt", 0.95], ["top", 0.85]]).
4. category: "separates" | "one_piece" | "outerwear" | "accessories"
5. is_ethnic: true if traditional or ethnic Indian/South Asian wear, false if western.
6. color: The single dominant primary color from:
   ["Black", "White", "Cream", "Grey", "Silver", "Blue", "Navy", "Teal", "Green", "Olive", "Red", "Maroon", "Pink", "Magenta", "Peach", "Purple", "Yellow", "Mustard", "Orange", "Gold", "Beige", "Brown"]
7. secondary_colors: List of other visible colors.
8. pattern: Dominant pattern from:
   ["Solid", "Floral", "Striped", "Checked", "Plaid", "Polka Dot", "Geometric", "Graphic", "Animal Print", "Paisley", "Embroidered", "Zari", "Sequined", "Bandhani", "Block Print", "Ikat"]
9. embellishment: If surface work exists (e.g. "Embroidered", "Zari", "Sequined"), name it, otherwise null.
10. sleeve_type: "sleeveless" | "short_sleeve" | "long_sleeve" | "three_quarter" (or null if garment has no sleeves, e.g. trousers or skirt).
11. fabric: Detected fabric (e.g. "Cotton", "Denim", "Linen", "Silk", "Wool", "Velvet", "Leather", "Chiffon", "Knit", "Georgette").
12. season: Suitable seasons from ["summer", "winter", "spring", "fall", "all_season"].
13. occasion: Suitable occasions from ["casual", "formal", "party", "college", "office", "wedding", "sports", "travel", "festive"].
14. predicted_category: One broad occasion/tradition tag: "Casual" | "Formal" | "Party" | "Ethnic" | "Western" | "Summer" | "Winter".
15. tags: 4-6 lowercase hashtags (e.g. ["#graphic-tee", "#vintage", "#black", "#casual"]).

Return ONLY valid JSON matching this exact structure:
{
  "name": "Garment Name",
  "type": "type",
  "type_alternatives": [["type1", 0.95], ["type2", 0.8]],
  "category": "category",
  "is_ethnic": false,
  "color": "Color",
  "secondary_colors": ["Color2"],
  "pattern": "Pattern",
  "embellishment": null,
  "sleeve_type": "sleeve_type",
  "fabric": "Fabric",
  "season": ["season1"],
  "occasion": ["occasion1", "occasion2"],
  "tags": ["#tag1", "#tag2"],
  "predicted_category": "Casual",
  "prediction_confidence": 0.95,
  "confidence": {
    "type": 0.95,
    "color": 0.98,
    "pattern": 0.92,
    "fabric": 0.88,
    "category": 0.95
  }
}
"""

CANDIDATE_MODELS = [
    "gemini-3-flash-preview",
    settings.gemini_model,
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]


class GeminiVisionService:
    @property
    def is_configured(self) -> bool:
        return settings.is_gemini_configured

    async def _call_gemini_json(
        self,
        prompt: str,
        file_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
    ) -> Optional[dict[str, Any]]:
        api_key = settings.effective_gemini_api_key
        if not api_key:
            logger.info("Gemini API key is not configured.")
            return None

        parts: list[dict[str, Any]] = [{"text": prompt}]
        if file_bytes is not None:
            encoded_image = base64.b64encode(file_bytes).decode("utf-8")
            if not mime_type or mime_type not in settings.allowed_image_mime_types:
                mime_type = "image/jpeg"
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": encoded_image,
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.3,
            },
        }

        models_to_try: list[str] = []
        for m in CANDIDATE_MODELS:
            if m and m not in models_to_try:
                models_to_try.append(m)

        timeout = httpx.Timeout(45.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            last_error: Optional[Exception] = None
            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                try:
                    logger.info("Calling Gemini with model %s...", model_name)
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            continue
                        part = candidates[0].get("content", {}).get("parts", [{}])[0]
                        text = part.get("text", "")
                        if text:
                            parsed = json.loads(text)
                            parsed["model_used"] = model_name
                            parsed["engine"] = "gemini_multimodal_vision"
                            return parsed
                    elif response.status_code in (400, 404, 429, 500, 503):
                        logger.warning(
                            "Model %s returned HTTP %s. Trying next candidate model...",
                            model_name,
                            response.status_code,
                        )
                        continue
                    else:
                        logger.error("Gemini API error %s: %s", response.status_code, response.text[:200])
                except Exception as exc:
                    last_error = exc
                    logger.warning("Gemini request error (%s): %s", model_name, exc)

            if last_error:
                logger.error("All Gemini attempts failed: %s", last_error)
            return None

    async def analyze_outfit(
        self,
        file_bytes: bytes,
        mime_type: str = "image/jpeg",
        gender_override: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Call Google Gemini Vision API to perform multi-modal outfit analysis."""
        prompt = OUTFIT_ANALYSIS_PROMPT
        if gender_override:
            prompt += f"\nNote: The user specified the styling gender preference as '{gender_override}'."

        return await self._call_gemini_json(prompt, file_bytes, mime_type)

    async def detect_clothing_item(
        self,
        file_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> Optional[dict[str, Any]]:
        """Call Google Gemini Vision API to detect single clothing item attributes with high precision."""
        result = await self._call_gemini_json(CLOTHING_ITEM_DETECTION_PROMPT, file_bytes, mime_type)
        if not result:
            return None

        # Ensure type alternatives format matches [["label", score], ...]
        raw_alts = result.get("type_alternatives", [])
        formatted_alts = []
        for item in raw_alts:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                formatted_alts.append([str(item[0]), float(item[1])])
            elif isinstance(item, str):
                formatted_alts.append([item, 0.85])

        result["type_alternatives"] = formatted_alts
        result["model_version"] = result.get("model_used", "gemini-3.5-flash")
        result["predicted_axes"] = {
            "occasion": result.get("occasion", []),
            "season": result.get("season", []),
            "tradition": "ethnic" if result.get("is_ethnic") else "western",
        }
        return result

    async def advise_shopping_purchase(
        self,
        file_bytes: bytes,
        matched_items: list[dict[str, Any]],
        mime_type: str = "image/jpeg",
    ) -> Optional[dict[str, Any]]:
        """Compare a shopping item candidate against the user's closest wardrobe items."""
        items_summary = "\n".join(
            f"- {item.get('name')} (Type: {item.get('type', 'item')}, Color: {item.get('color', 'unknown')}, Similarity: {item.get('similarity', 0)})"
            for item in matched_items[:4]
        ) or "None (this category is empty in wardrobe)"

        prompt = f"""You are an expert personal wardrobe stylist and mindful fashion shopping advisor.
The user is considering purchasing the garment shown in the image.
Here are the closest items they ALREADY own in their digital wardrobe:
{items_summary}

Evaluate whether this purchase is justified, redundant, or fills a gap in their wardrobe.
Provide actionable, stylish advice.

Return ONLY valid JSON matching this exact structure:
{{
  "recommendation": "buy" | "skip" | "consider_alternative",
  "headline": "Short punchy summary (e.g. 'High redundancy with existing wardrobe', 'Fills an essential layer gap')",
  "stylist_reasoning": "2-3 sentences explaining why they should buy or skip based on visual similarity, versatility, and wear count.",
  "wardrobe_gap_insight": "What is missing or already oversaturated in their current wardrobe related to this piece.",
  "styling_potential": "How this piece would realistically pair with existing clothes if purchased."
}}"""
        return await self._call_gemini_json(prompt, file_bytes, mime_type)

    async def evaluate_outfit_pairing(
        self,
        pieces: list[dict[str, Any]],
        occasion: Optional[str] = None,
        season: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Generate high-fashion AI stylist rationales and elevation tips for a wardrobe outfit pairing."""
        pieces_desc = "\n".join(
            f"- {p.get('role', 'piece').upper()}: {p.get('name')} (Type: {p.get('type', '')}, Color: {p.get('color', '')}, Pattern: {p.get('pattern', '')})"
            for p in pieces
        )
        prompt = f"""You are an elite, critical personal fashion stylist and image consultant.
Evaluate this outfit combination assembled from a user's real wardrobe:
{pieces_desc}
Target Occasion: {occasion or 'Any occasion'}
Target Season: {season or 'All season'}

Provide an honest, high-fashion styling evaluation:
1. is_cohesive: boolean. True if this is an aesthetically pleasing, culturally coherent, and wearable outfit. False if there is any jarring clash in tradition (e.g. leather jacket over traditional kurta/saree), fabric weights (heavy winter leather over breezy summer linen), or formality.
2. aesthetic: Specific aesthetic subgenre (e.g. 'Effortless Linen Minimalist', 'Elevated Streetwear', 'Contemporary Indo-Western', 'Classic Smart Casual').
3. stylist_rationale: 1-2 sentences on why these exact pieces, cuts, and colors harmonize (or why they clash if is_cohesive is false).
4. elevation_tip: One concrete, actionable tip on how to style/wear this combination (e.g., footwear pairing, sleeve roll, jewelry/watch, or belt).
5. score_adjustment: integer between -40 and +10 reflecting fashion synergy. If is_cohesive is false or there is an absurd clash, use a negative adjustment between -25 and -40. If highly cohesive, use +5 to +10.

Return ONLY valid JSON matching this structure:
{{
  "is_cohesive": true,
  "aesthetic": "Aesthetic style name",
  "stylist_rationale": "Why this pairing works or clashes",
  "elevation_tip": "How to elevate the look",
  "score_adjustment": 5
}}"""
        return await self._call_gemini_json(prompt, file_bytes=None)


gemini_service = GeminiVisionService()
