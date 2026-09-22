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

# Ceiling on pairings scored per request. A 60-piece wardrobe is 900 top/bottom
# combinations, which is fine; this only stops a pathological wardrobe from
# turning one request into a long job.
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
            # Least-worn first: the point is to wear what is hanging unused.
            outfits.sort(key=lambda o: (o["total_wears"], -o["score"]))
        else:
            outfits.sort(key=lambda o: (-o["score"], o["total_wears"]))

        return {
            "wardrobe_size": len(items),
            "count": len(outfits),
            "gaps": self._gaps(by_slot),
            "outfits": outfits[: max(limit, 1)],
        }

    def _build(self, by_slot: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        outfits: list[dict[str, Any]] = []

        tops = by_slot.get("top", [])
        bottoms = by_slot.get("bottom", [])
        layers = by_slot.get("layer", [])
        accessories = by_slot.get("accessory", [])

        pairs = itertools.islice(itertools.product(tops, bottoms), MAX_COMBINATIONS)
        for top, bottom in pairs:
            outfit = self._score([("top", top), ("bottom", bottom)], layers, accessories)
            if outfit:
                outfits.append(outfit)

        # A saree or a jumpsuit is already an outfit; it only needs what goes over it.
        for piece in by_slot.get("one_piece", []):
            outfit = self._score([("one_piece", piece)], layers, accessories)
            if outfit:
                outfits.append(outfit)

        return outfits

    def _score(
        self,
        core: list[tuple[str, dict[str, Any]]],
        layers: list[dict[str, Any]],
        accessories: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        pieces = [item for _, item in core]
        reasons: list[str] = []
        warnings: list[str] = []
        score = 50

        names = {role: item.get("name") for role, item in core}

        # --- colour ----------------------------------------------------------
        if len(pieces) == 2:
            top_colors = rules.colors_of(pieces[0])
            bottom_colors = rules.colors_of(pieces[1])

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
            elif rules.is_neutral(pieces[0]) or rules.is_neutral(pieces[1]):
                score += 14
                neutral = names["top"] if rules.is_neutral(pieces[0]) else names["bottom"]
                reasons.append(f"{neutral} is a neutral, so it carries the other piece.")
            else:
                score += 4

        # --- pattern ---------------------------------------------------------
        patterns = [rules.pattern_of(piece) for piece in pieces]
        loud = [p for p in patterns if p not in rules.QUIET_PATTERNS]
        if len(loud) >= 2:
            score -= 18
            warnings.append(
                f"Two patterns competing ({' and '.join(loud)}) - keep one of them plain."
            )
        elif len(loud) == 1 and len(pieces) == 2:
            score += 12
            plain = names["bottom"] if patterns[0] == loud[0] else names["top"]
            reasons.append(f"One patterned piece against plain {plain} keeps the balance right.")
        elif len(pieces) == 2:
            score += 6
            reasons.append("Both pieces are plain, so the cut does the talking.")

        # --- tradition -------------------------------------------------------
        if len(pieces) == 2:
            top_type = str(pieces[0].get("type") or "").lower()
            bottom_type = str(pieces[1].get("type") or "").lower()
            top_ethnic = rules.is_ethnic(pieces[0])
            bottom_ethnic = rules.is_ethnic(pieces[1])

            if top_ethnic and bottom_ethnic:
                score += 10
            elif top_ethnic != bottom_ethnic:
                crossover = (
                    top_type in rules.CROSSOVER_TOPS and bottom_type in rules.CROSSOVER_BOTTOMS
                )
                if crossover:
                    score += 8
                    # The caveat differs: denim is the relaxed version of this
                    # pairing, tailoring is the one that can tip into costume.
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

        # --- occasion and season ---------------------------------------------
        style, styles, style_note = rules.resolve_styles(pieces)
        if style_note:
            reasons.append(style_note)

        occasion, agreed, occasions = rules.resolve_occasion(pieces)
        if agreed:
            score += 12
            reasons.append(
                f"Both pieces are logged for {occasion.replace('_', ' ')}."
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
            warnings.append("These are logged for different seasons.")
            seasons = {"all_season"}

        # --- rotation ---------------------------------------------------------
        wears = [int(piece.get("wear_count") or 0) for piece in pieces]
        total_wears = sum(wears)
        if total_wears == 0:
            score += 8
            reasons.append("Neither piece has been worn yet.")
        elif min(wears) == 0:
            score += 5
            unworn = names["top"] if wears[0] == 0 else names.get("bottom")
            reasons.append(f"{unworn} is still unworn - this is a way to start.")

        if score < 25:
            return None

        pieces_out = [self._piece(role, item) for role, item in core]

        # A layer and a dupatta are optional extras, added only when they agree
        # with the outfit rather than to pad the card out.
        extra = self._best_extra(layers, pieces, "layer")
        if extra:
            pieces_out.append(self._piece("layer", extra))
            reasons.append(f"{extra.get('name')} layers over it without fighting the colours.")
        if occasion in {"festive", "wedding", "party"}:
            dupatta = self._best_extra(accessories, pieces, "accessory")
            if dupatta:
                pieces_out.append(self._piece("accessory", dupatta))
                reasons.append(f"{dupatta.get('name')} finishes it for the occasion.")

        return {
            "id": "-".join(str(item.get("id")) for _, item in core),
            "pieces": pieces_out,
            "occasion": occasion,
            "occasions": occasions,
            "style": style,
            "styles": styles,
            "style_labels": {s: rules.STYLE_LABELS[s] for s in styles},
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
        """The neutral-friendliest extra that does not clash with anything chosen."""
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
        # Prefer a neutral, then the least-worn, so extras also get used.
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
        """Why a wardrobe produced few outfits, in the user's terms."""
        gaps: list[str] = []
        if not by_slot.get("top") and not by_slot.get("one_piece"):
            gaps.append("No tops catalogued yet - add a shirt, kurta or knit.")
        if not by_slot.get("bottom") and not by_slot.get("one_piece"):
            gaps.append("No bottoms catalogued yet - add trousers, jeans or a skirt.")
        if by_slot.get("top") and not by_slot.get("bottom") and not by_slot.get("one_piece"):
            gaps.append("Tops with nothing to wear them with - one pair of trousers unlocks them all.")
        return gaps


outfit_service = OutfitService()
