"""Scores the curated trend catalogue against a user's stored wardrobe.

Two distinct outputs, kept separate the same way the recommendations module
keeps model output apart from rule output:

  - `feed`: editorial trends from `catalog.py`, each annotated with what the
    user already owns for it. The trend copy is editorial; the match is computed.
  - `signals`: trends *inside* the wardrobe - colour drift, rising categories,
    pieces falling out of rotation. Nothing editorial, purely the user's data.
"""

import logging
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.modules.trends import catalog
from app.modules.wardrobe.service import wardrobe_service

logger = logging.getLogger("stylesync.trends")

# A piece is "owned" once the garment type matches; colour and pattern only
# raise the strength from there.
TYPE_WEIGHT = 0.60
COLOR_WEIGHT = 0.25
PATTERN_WEIGHT = 0.15
OWNED_THRESHOLD = TYPE_WEIGHT

# How the two halves of a trend's fit score are balanced.
PIECE_WEIGHT = 0.75
PALETTE_WEIGHT = 0.25

# Colours that read as interchangeable when matching a trend palette.
COLOR_FAMILIES: dict[str, set[str]] = {
    "blue": {"blue", "navy"},
    "navy": {"navy", "blue"},
    "beige": {"beige", "brown", "white"},
    "brown": {"brown", "beige"},
    "grey": {"grey", "black", "white"},
    "black": {"black", "grey"},
    "white": {"white", "beige", "grey"},
    "red": {"red", "pink", "purple"},
    "purple": {"purple", "red", "pink"},
    "pink": {"pink", "red", "purple"},
    "green": {"green"},
    "yellow": {"yellow", "orange"},
    "orange": {"orange", "yellow", "brown"},
}

_WORD_RE = re.compile(r"[a-z]+")


def _words(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {word for entry in value for word in _words(entry)}
    return set(_WORD_RE.findall(str(value).lower()))


def _item_tokens(item: dict[str, Any]) -> set[str]:
    """Every word that could name the garment, for key-piece matching."""
    tokens = _words(item.get("type"))
    tokens |= _words(item.get("category"))
    tokens |= _words(item.get("name"))
    tokens |= _words(item.get("tags"))
    tokens |= _words(item.get("predicted_category"))
    # "t-shirt" and "tshirt" both tokenise oddly; normalise the common ones.
    if "shirt" in tokens and "t" in tokens:
        tokens.add("tee")
    return tokens


def _item_colors(item: dict[str, Any]) -> set[str]:
    colors = _words(item.get("primary_color")) | _words(item.get("color"))
    secondary = item.get("secondary_colors") or []
    colors |= _words(secondary)
    return colors


def _colors_overlap(item_colors: set[str], wanted: set[str]) -> bool:
    if not wanted:
        return False
    for color in item_colors:
        if color in wanted:
            return True
        if COLOR_FAMILIES.get(color, set()) & wanted:
            return True
    return False


def _score_piece(piece: dict[str, Any], item: dict[str, Any]) -> float:
    """0 when the garment is wrong, up to 1.0 for the right garment in the right colour."""
    wanted_types = {t.lower() for t in piece.get("types", [])}
    tokens = _item_tokens(item)
    if not wanted_types & tokens:
        return 0.0

    score = TYPE_WEIGHT

    wanted_colors = {c.lower() for c in piece.get("colors", [])}
    if not wanted_colors or _colors_overlap(_item_colors(item), wanted_colors):
        score += COLOR_WEIGHT

    wanted_patterns = {p.lower() for p in piece.get("patterns", [])}
    item_pattern = str(item.get("pattern") or "").lower()
    if not wanted_patterns or item_pattern in wanted_patterns:
        score += PATTERN_WEIGHT

    return round(score, 3)


def _item_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "image_url": item.get("thumbnail_url") or item.get("image_url") or "",
        "primary_color": item.get("primary_color") or item.get("color") or "",
        "pattern": item.get("pattern") or "",
        "wear_count": int(item.get("wear_count") or 0),
    }


def _palette_affinity(items: list[dict[str, Any]], palette: list[str]) -> float:
    """Share of the wardrobe that already sits inside the trend's palette."""
    if not items:
        return 0.0
    wanted = {c.lower() for c in palette}
    hits = sum(1 for item in items if _colors_overlap(_item_colors(item), wanted))
    return round(hits / len(items), 3)


def _verdict(owned: int, total: int, score: int) -> str:
    if total and owned == total:
        return "ready to wear"
    if total - owned == 1:
        return "one piece away"
    if score >= 45:
        return "almost there"
    return "not your wardrobe yet"


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


class TrendsService:
    async def get_feed(
        self,
        user_id: str,
        season: str | None = None,
        occasion: str | None = None,
        sort: str = "momentum",
        limit: int | None = None,
    ) -> dict[str, Any]:
        items = await wardrobe_service.get_user_items(user_id)
        trends = [self._annotate(trend, items) for trend in catalog.TRENDS]

        if season and season.lower() not in {"all", ""}:
            wanted = season.lower()
            trends = [
                t for t in trends
                if wanted in t["seasons"] or "all_season" in t["seasons"]
            ]
        if occasion and occasion.lower() not in {"all", ""}:
            wanted = occasion.lower()
            trends = [t for t in trends if wanted in t["occasions"]]

        if sort == "match":
            trends.sort(key=lambda t: (t["match"]["score"], t["momentum"]), reverse=True)
        elif sort == "title":
            trends.sort(key=lambda t: t["title"].lower())
        else:
            trends.sort(key=lambda t: (t["momentum"], t["match"]["score"]), reverse=True)

        if limit and limit > 0:
            trends = trends[:limit]

        scores = [t["match"]["score"] for t in trends]
        return {
            "season": catalog.CATALOG_SEASON,
            "updated": catalog.CATALOG_UPDATED,
            "wardrobe_size": len(items),
            "count": len(trends),
            "average_match": round(sum(scores) / len(scores)) if scores else 0,
            "top_match_id": max(trends, key=lambda t: t["match"]["score"])["id"] if trends else None,
            "trends": trends,
        }

    async def get_trend(self, user_id: str, trend_id: str) -> dict[str, Any] | None:
        trend = catalog.by_id(trend_id)
        if not trend:
            return None
        items = await wardrobe_service.get_user_items(user_id)
        return self._annotate(trend, items)

    def _annotate(self, trend: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
        pieces: list[dict[str, Any]] = []
        for piece in trend["key_pieces"]:
            best_item: dict[str, Any] | None = None
            best_score = 0.0
            for item in items:
                score = _score_piece(piece, item)
                # Ties go to the better-worn item: it is the one they reach for.
                if score > best_score or (
                    score == best_score
                    and score > 0
                    and best_item is not None
                    and int(item.get("wear_count") or 0) > int(best_item.get("wear_count") or 0)
                ):
                    best_score, best_item = score, item

            owned = best_score >= OWNED_THRESHOLD
            pieces.append(
                {
                    "label": piece["label"],
                    "owned": owned,
                    "strength": round(best_score, 3),
                    "match": _item_summary(best_item) if owned and best_item else None,
                    "note": self._piece_note(piece, best_item, best_score),
                }
            )

        total = len(pieces)
        owned_count = sum(1 for p in pieces if p["owned"])
        piece_mean = sum(p["strength"] for p in pieces) / total if total else 0.0
        affinity = _palette_affinity(items, trend["palette"])
        score = round(100 * (PIECE_WEIGHT * piece_mean + PALETTE_WEIGHT * affinity))

        return {
            "id": trend["id"],
            "title": trend["title"],
            "summary": trend["summary"],
            "momentum": trend["momentum"],
            "status": catalog.status_for(trend["momentum"]),
            "season_label": catalog.CATALOG_SEASON,
            "palette": trend["palette"],
            "patterns": trend["patterns"],
            "seasons": trend["seasons"],
            "occasions": trend["occasions"],
            "styling_tips": trend["styling_tips"],
            "avoid": trend.get("avoid", []),
            "match": {
                "score": score,
                "owned_count": owned_count,
                "total_pieces": total,
                "palette_affinity": affinity,
                "verdict": _verdict(owned_count, total, score),
                "pieces": pieces,
                "missing": [p["label"] for p in pieces if not p["owned"]],
            },
        }

    def _piece_note(
        self, piece: dict[str, Any], item: dict[str, Any] | None, score: float
    ) -> str:
        if not item or score < OWNED_THRESHOLD:
            return "Nothing in your wardrobe covers this yet."
        if score >= TYPE_WEIGHT + COLOR_WEIGHT + PATTERN_WEIGHT - 0.001:
            return f"{item.get('name')} is an exact fit for this piece."
        gaps: list[str] = []
        wanted_colors = {c.lower() for c in piece.get("colors", [])}
        if wanted_colors and not _colors_overlap(_item_colors(item), wanted_colors):
            gaps.append(f"the trend leans {', '.join(sorted(wanted_colors))}")
        wanted_patterns = {p.lower() for p in piece.get("patterns", [])}
        if wanted_patterns and str(item.get("pattern") or "").lower() not in wanted_patterns:
            gaps.append(f"look for {', '.join(sorted(wanted_patterns))}")
        if not gaps:
            return f"{item.get('name')} works here."
        return f"{item.get('name')} works, but {'; '.join(gaps)}."

    async def get_signals(self, user_id: str) -> dict[str, Any]:
        """Trends inside the wardrobe itself - no editorial input."""
        items = await wardrobe_service.get_user_items(user_id)
        if not items:
            return {"wardrobe_size": 0, "signals": []}

        now = datetime.now(timezone.utc)
        signals: list[dict[str, Any]] = []

        # 1. Which colours actually get worn, versus which just get owned.
        owned_colors: Counter[str] = Counter()
        worn_colors: Counter[str] = Counter()
        for item in items:
            color = str(item.get("primary_color") or item.get("color") or "unknown").lower()
            owned_colors[color] += 1
            worn_colors[color] += int(item.get("wear_count") or 0)

        total_wears = sum(worn_colors.values())
        if total_wears:
            ranked = sorted(
                owned_colors,
                key=lambda c: (worn_colors[c] / total_wears) - (owned_colors[c] / len(items)),
                reverse=True,
            )
            over = ranked[0]
            under = ranked[-1]
            signals.append(
                {
                    "id": "colour-rotation",
                    "label": "Colour you reach for",
                    "value": over,
                    "detail": (
                        f"{worn_colors[over]} of your {total_wears} recorded wears are {over} "
                        f"pieces, from only {owned_colors[over]} item(s)."
                    ),
                    "direction": "up",
                }
            )
            if under != over:
                signals.append(
                    {
                        "id": "colour-neglected",
                        "label": "Colour going unworn",
                        "value": under,
                        "detail": (
                            f"You own {owned_colors[under]} {under} piece(s) but they account "
                            f"for {worn_colors[under]} wear(s)."
                        ),
                        "direction": "down",
                    }
                )

        # 2. Category momentum by average wears per item.
        by_category: dict[str, list[int]] = {}
        for item in items:
            key = str(item.get("type") or item.get("category") or "unknown").lower()
            by_category.setdefault(key, []).append(int(item.get("wear_count") or 0))
        if by_category:
            averages = {k: sum(v) / len(v) for k, v in by_category.items()}
            top = max(averages, key=lambda k: averages[k])
            signals.append(
                {
                    "id": "category-momentum",
                    "label": "Hardest-working category",
                    "value": top,
                    "detail": (
                        f"{top.replace('_', ' ')} averages {averages[top]:.1f} wears per item "
                        f"across {len(by_category[top])} piece(s)."
                    ),
                    "direction": "up",
                }
            )

        # 3. What is falling out of rotation.
        stale = [
            item
            for item in items
            if int(item.get("wear_count") or 0) <= 1
            and (
                _parse_dt(item.get("last_worn_at")) is None
                or (now - _parse_dt(item.get("last_worn_at"))).days >= 60
            )
        ]
        if stale:
            signals.append(
                {
                    "id": "falling-out",
                    "label": "Falling out of rotation",
                    "value": str(len(stale)),
                    "detail": (
                        f"{len(stale)} piece(s) have one wear or fewer and nothing logged in "
                        "the last two months - e.g. "
                        + ", ".join(str(i.get("name")) for i in stale[:3])
                        + "."
                    ),
                    "direction": "down",
                }
            )

        # 4. Palette drift: what recent additions look like versus the back catalogue.
        dated = [(i, _parse_dt(i.get("created_at"))) for i in items]
        recent = [i for i, dt in dated if dt and (now - dt).days <= 90]
        older = [i for i, dt in dated if dt and (now - dt).days > 90]
        if recent and older:
            recent_top = Counter(
                str(i.get("primary_color") or "unknown").lower() for i in recent
            ).most_common(1)[0][0]
            older_top = Counter(
                str(i.get("primary_color") or "unknown").lower() for i in older
            ).most_common(1)[0][0]
            if recent_top != older_top:
                signals.append(
                    {
                        "id": "palette-drift",
                        "label": "Your palette is shifting",
                        "value": f"{older_top} to {recent_top}",
                        "detail": (
                            f"Recent additions skew {recent_top}, while older pieces skew "
                            f"{older_top}."
                        ),
                        "direction": "up",
                    }
                )

        return {"wardrobe_size": len(items), "signals": signals}


trends_service = TrendsService()
