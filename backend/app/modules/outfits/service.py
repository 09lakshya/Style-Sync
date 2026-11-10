"""Builds wearable outfits from the items a user already owns.

Every suggestion is a real combination of their own pieces, scored on colour,
pattern, occasion, season and tradition, and returned with the reasons that
produced the score. Nothing editorial: if the wardrobe cannot make an outfit,
the honest answer is an empty list and a note saying what is missing.
"""

import itertools
import logging
from typing import Any

from app.modules.outfits import rules
from app.modules.wardrobe.service import wardrobe_service

logger = logging.getLogger("stylesync.outfits")

# Ceiling on pairings scored per request.
MAX_COMBINATIONS = 4000


class OutfitService:
    async def suggest(
        self,
        user_id: str,
        occasion: str | None = None,
        season: str | None = None,
        style: str | None = None,
        sort: str = "score",
        limit: int = 12,
    ) -> dict[str, Any]:
        items = await wardrobe_service.get_user_items(user_id)
        by_slot: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            slot = rules.slot_of(item)
            if slot:
                by_slot.setdefault(slot, []).append(item)

        outfits = self._build(by_slot)

        if occasion and occasion.lower() not in {"", "all"}:
            wanted = occasion.lower().replace(" ", "_")
            outfits = [o for o in outfits if wanted in o["occasions"]]
        if style and style.lower() not in {"", "all"}:
            wanted = style.lower()
            outfits = [o for o in outfits if wanted in o["styles"]]
        if season and season.lower() not in {"", "all"}:
            wanted = season.lower()
            outfits = [
                o for o in outfits if wanted in o["seasons"] or "all_season" in o["seasons"]
            ]

        if sort == "fresh":
            # Least-worn first: wear what is hanging unused
            outfits.sort(key=lambda o: (o["total_wears"], -o["score"]))
        else:
            outfits.sort(key=lambda o: (-o["score"], o["total_wears"]))

        outfits_to_return = outfits[: max(limit, 1)]
        from app.modules.ai.gemini_service import gemini_service
        if gemini_service.is_configured and outfits_to_return:
            for top_outfit in outfits_to_return[:2]:
                try:
                    insight = await gemini_service.evaluate_outfit_pairing(
                        pieces=top_outfit.get("pieces", []),
                        occasion=occasion,
                        season=season,
                    )
                    if insight:
                        if not insight.get("is_cohesive", True):
                            top_outfit["warnings"].append(
                                f"AI Stylist Caution: {insight.get('stylist_rationale', 'Aesthetic mismatch detected.')}"
                            )
                            top_outfit["score"] = max(
                                20,
                                min(100, top_outfit["score"] + min(-20, insight.get("score_adjustment", -25))),
                            )
                        else:
                            if insight.get("aesthetic"):
                                top_outfit["style"] = insight["aesthetic"]
                                top_outfit.setdefault("style_labels", {})[insight["aesthetic"]] = insight["aesthetic"]
                            if insight.get("stylist_rationale"):
                                top_outfit["reasons"].insert(0, f"AI Stylist: {insight['stylist_rationale']}")
                            if insight.get("elevation_tip"):
                                top_outfit["reasons"].append(f"Stylist Tip: {insight['elevation_tip']}")
                            if isinstance(insight.get("score_adjustment"), int):
                                top_outfit["score"] = max(
                                    40, min(100, top_outfit["score"] + insight["score_adjustment"])
                                )
                except Exception as exc:
                    logger.warning("Gemini outfit pairing evaluation skipped: %s", exc)

        return {
            "wardrobe_size": len(items),
            "count": len(outfits),
            "gaps": self._gaps(by_slot),
            "outfits": outfits_to_return,
        }

    def _build(self, by_slot: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        outfits: list[dict[str, Any]] = []

        tops = by_slot.get("top", [])
        bottoms = by_slot.get("bottom", [])
        layers = by_slot.get("layer", [])
        accessories = by_slot.get("accessory", [])

        pairs = itertools.islice(itertools.product(tops, bottoms), MAX_COMBINATIONS)
        for top, bottom in pairs:
            # 1. Base clean 2-piece outfit
            base_outfit = self._score([("top", top), ("bottom", bottom)], layer=None, accessories=accessories)
            if base_outfit:
                outfits.append(base_outfit)

            # 2. Layered outfit variant (Top + Bottom + Layer) - ONLY if layer is strictly compatible
            if layers:
                compatible_layer = self._best_compatible_layer(layers, [top, bottom])
                if compatible_layer:
                    layered_outfit = self._score(
                        [("top", top), ("bottom", bottom)],
                        layer=compatible_layer,
                        accessories=accessories,
                    )
                    if layered_outfit:
                        outfits.append(layered_outfit)

        # One-piece garments (saree, jumpsuit, dress)
        for piece in by_slot.get("one_piece", []):
            base_outfit = self._score([("one_piece", piece)], layer=None, accessories=accessories)
            if base_outfit:
                outfits.append(base_outfit)
            if layers:
                compatible_layer = self._best_compatible_layer(layers, [piece])
                if compatible_layer:
                    layered_outfit = self._score(
                        [("one_piece", piece)],
                        layer=compatible_layer,
                        accessories=accessories,
                    )
                    if layered_outfit:
                        outfits.append(layered_outfit)

        return outfits

    def _best_compatible_layer(
        self, candidates: list[dict[str, Any]], core_pieces: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Find the most harmonious layer that satisfies all tradition, fabric, season, and color rules."""
        usable: list[dict[str, Any]] = []
        for candidate in candidates:
            allowed, _ = rules.can_layer(candidate, core_pieces)
            if allowed:
                usable.append(candidate)

        if not usable:
            return None

        # Prefer a neutral, then the least-worn, so extras also get used
        usable.sort(
            key=lambda c: (not rules.is_neutral(c), int(c.get("wear_count") or 0))
        )
        return usable[0]

    def _score(
        self,
        core: list[tuple[str, dict[str, Any]]],
        layer: dict[str, Any] | None = None,
        accessories: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        pieces = [item for _, item in core]
        if layer:
            pieces.append(layer)

        reasons: list[str] = []
        warnings: list[str] = []
        score = 50

        names = {role: item.get("name") for role, item in core}

        # --- colour ----------------------------------------------------------
        if len(core) == 2:
            top_colors = rules.colors_of(core[0][1])
            bottom_colors = rules.colors_of(core[1][1])

            if rules.clashes(top_colors, bottom_colors):
                score -= 22
                warnings.append(
                    "Both halves are saturated colours pulling in opposite directions - "
                    "a neutral in between would settle it."
                )
            elif rules.same_family(top_colors, bottom_colors):
                score += 16
                reasons.append(
                    f"{', '.join(sorted(top_colors))} and {', '.join(sorted(bottom_colors))} "
                    "sit in the same family, so it reads as one tonal outfit."
                )
            elif rules.is_neutral(core[0][1]) or rules.is_neutral(core[1][1]):
                score += 14
                neutral = names["top"] if rules.is_neutral(core[0][1]) else names["bottom"]
                reasons.append(f"{neutral} is a neutral, so it carries the other piece.")
            else:
                score += 4

        # Layer colour check
        if layer:
            layer_colors = rules.colors_of(layer)
            core_colors: set[str] = set()
            for _, item in core:
                core_colors |= rules.colors_of(item)

            if rules.clashes(layer_colors, core_colors):
                score -= 18
                warnings.append("The outer layer color clashes with the core pieces.")
            elif rules.same_family(layer_colors, core_colors):
                score += 6
                reasons.append(f"{layer.get('name')} tonally harmonizes with the outfit.")
            elif rules.is_neutral(layer):
                score += 4
                reasons.append(f"{layer.get('name')} adds a balanced neutral outer layer.")

        # --- pattern ---------------------------------------------------------
        patterns = [rules.pattern_of(piece) for piece in pieces]
        loud = [p for p in patterns if p not in rules.QUIET_PATTERNS]
        if len(loud) >= 2:
            score -= 18
            warnings.append(
                f"Two patterns competing ({' and '.join(loud)}) - keep one of them plain."
            )
        elif len(loud) == 1 and len(core) == 2 and not layer:
            score += 12
            plain = names["bottom"] if patterns[0] == loud[0] else names["top"]
            reasons.append(f"One patterned piece against plain {plain} keeps the balance right.")
        elif len(core) == 2 and not layer:
            score += 6
            reasons.append("Both pieces are plain, so the cut does the talking.")

        # --- tradition -------------------------------------------------------
        if len(core) == 2:
            top_type = str(core[0][1].get("type") or "").lower()
            bottom_type = str(core[1][1].get("type") or "").lower()
            top_ethnic = rules.is_ethnic(core[0][1])
            bottom_ethnic = rules.is_ethnic(core[1][1])

            if top_ethnic and bottom_ethnic:
                score += 10
            elif top_ethnic != bottom_ethnic:
                crossover = (
                    top_type in rules.CROSSOVER_TOPS and bottom_type in rules.CROSSOVER_BOTTOMS
                )
                if crossover:
                    score += 8
                    reasons.append(
                        "Keep the kurta unstarched and it reads as everyday wear."
                        if bottom_type == "jeans"
                        else "Keep the kurta short so it does not fight the tailoring."
                    )
                else:
                    score -= 14
                    warnings.append(
                        "Mixing a traditional piece with a western one here needs care."
                    )

        # Layer tradition check
        if layer:
            top_item = core[0][1]
            top_ethnic = rules.is_ethnic(top_item)
            layer_ethnic = rules.is_ethnic(layer) or str(layer.get("type") or "").lower() in rules.ETHNIC_LAYERS

            if top_ethnic:
                if layer_ethnic:
                    score += 8
                    reasons.append(f"{layer.get('name')} elegantly elevates the traditional silhouette.")
                else:
                    score -= 35
                    warnings.append(f"{layer.get('name')} clashes culturally and structurally with traditional wear.")
            else:
                if not layer_ethnic:
                    score += 6
                    reasons.append(f"{layer.get('name')} layers cleanly over western separates.")

        # --- occasion and season ---------------------------------------------
        style, styles, style_note = rules.resolve_styles(pieces)
        if style_note:
            reasons.append(style_note)

        occasion, agreed, occasions = rules.resolve_occasion(pieces)
        if agreed:
            score += 12
            reasons.append(
                f"Pieces agree on {occasion.replace('_', ' ')}."
            )
        else:
            score -= 6
            warnings.append(
                f"The pieces are logged for different occasions; the dressier one puts this at "
                f"{occasion.replace('_', ' ')}."
            )

        seasons = rules.shared_seasons(pieces)
        if not seasons:
            score -= 10
            warnings.append("These pieces are logged for different seasons.")
            seasons = {"all_season"}

        # --- rotation ---------------------------------------------------------
        wears = [int(piece.get("wear_count") or 0) for piece in pieces]
        total_wears = sum(wears)
        if total_wears == 0:
            score += 8
            reasons.append("Pieces are unworn - a fresh combination to try.")
        elif min(wears) == 0:
            score += 5
            unworn = names["top"] if wears[0] == 0 else names.get("bottom")
            if unworn:
                reasons.append(f"{unworn} is still unworn - this is a way to start.")

        if score < 25:
            return None

        pieces_out = [self._piece(role, item) for role, item in core]
        if layer:
            pieces_out.append(self._piece("layer", layer))

        # Dupatta is added only for traditional/festive outfits
        if accessories and occasion in {"festive", "wedding", "party"}:
            if any(rules.is_ethnic(p) for p in pieces):
                dupatta = self._best_extra(accessories, pieces, "accessory")
                if dupatta:
                    pieces_out.append(self._piece("accessory", dupatta))
                    reasons.append(f"{dupatta.get('name')} finishes it for the occasion.")

        core_id = "-".join(str(item.get("id")) for _, item in core)
        outfit_id = f"{core_id}-{layer.get('id')}" if layer else core_id

        return {
            "id": outfit_id,
            "pieces": pieces_out,
            "occasion": occasion,
            "occasions": occasions,
            "style": style,
            "styles": styles,
            "style_labels": {s: rules.STYLE_LABELS.get(s, s.title()) for s in styles},
            "occasion_labels": {
                o: rules.OCCASION_LABELS.get(o, o.replace("_", " ").title()) for o in occasions
            },
            "occasion_label": rules.OCCASION_LABELS.get(
                occasion, occasion.replace("_", " ").title()
            ),
            "seasons": sorted(seasons),
            "score": max(0, min(100, score)),
            "reasons": reasons,
            "warnings": warnings,
            "total_wears": total_wears,
        }

    def _best_extra(
        self, candidates: list[dict[str, Any]], pieces: list[dict[str, Any]], slot: str
    ) -> dict[str, Any] | None:
        outfit_colors: set[str] = set()
        for piece in pieces:
            outfit_colors |= rules.colors_of(piece)

        usable = [
            candidate
            for candidate in candidates
            if not rules.clashes(rules.colors_of(candidate), outfit_colors)
        ]
        if not usable:
            return None
        usable.sort(
            key=lambda c: (not rules.is_neutral(c), int(c.get("wear_count") or 0))
        )
        return usable[0]

    def _piece(self, role: str, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "role": role,
            "id": item.get("id"),
            "name": item.get("name"),
            "image_url": item.get("thumbnail_url") or item.get("image_url") or "",
            "type": item.get("type") or "",
            "color": item.get("primary_color") or item.get("color") or "",
            "pattern": item.get("pattern") or "",
            "wear_count": int(item.get("wear_count") or 0),
        }

    def _gaps(self, by_slot: dict[str, list[dict[str, Any]]]) -> list[str]:
        gaps: list[str] = []
        if not by_slot.get("top") and not by_slot.get("one_piece"):
            gaps.append("No tops catalogued yet - add a shirt, kurta or knit.")
        if not by_slot.get("bottom") and not by_slot.get("one_piece"):
            gaps.append("No bottoms catalogued yet - add trousers, jeans or a skirt.")
        if by_slot.get("top") and not by_slot.get("bottom") and not by_slot.get("one_piece"):
            gaps.append("Tops with nothing to wear them with - one pair of trousers unlocks them all.")
        return gaps


outfit_service = OutfitService()
