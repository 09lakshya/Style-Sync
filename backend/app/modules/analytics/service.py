from datetime import datetime, timedelta, timezone
from typing import Any

from app.modules.ai.service import wardrobe_summary
from app.modules.shopping.repository import shopping_repository
from app.modules.wardrobe.service import wardrobe_service

# A piece counts as long unused when it has not been worn for this long. One
# that was never worn counts once it has been in the wardrobe this long, so a
# jacket added yesterday is not flagged on day one.
LONG_UNUSED_AFTER = timedelta(days=90)
NEVER_WORN_GRACE = timedelta(days=30)


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


def is_long_unused(item: dict[str, Any], now: datetime) -> bool:
    last_worn = _parse_dt(item.get("last_worn_at"))
    if last_worn:
        return now - last_worn >= LONG_UNUSED_AFTER
    added = _parse_dt(item.get("created_at"))
    return added is not None and now - added >= NEVER_WORN_GRACE


def start_of_local_day(now: datetime, tz_offset_minutes: int) -> datetime:
    """UTC instant of the viewer's local midnight.

    tz_offset_minutes is what JavaScript's Date.getTimezoneOffset() returns:
    minutes to add to local time to reach UTC (-330 in India).
    """
    local_now = now - timedelta(minutes=tz_offset_minutes)
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight + timedelta(minutes=tz_offset_minutes)


class AnalyticsService:
    async def get_user_wardrobe_analytics(
        self, user_id: str, tz_offset_minutes: int = 0
    ) -> dict[str, Any]:
        """Wardrobe statistics, plus today's duplicate checks from the audit log."""
        items = await wardrobe_service.get_user_items(user_id)
        now = datetime.now(timezone.utc)
        summary = wardrobe_summary(items)
        summary["long_unused_items"] = sum(1 for item in items if is_long_unused(item, now))
        summary["duplicate_checks_today"] = await shopping_repository.count_since(
            user_id, start_of_local_day(now, tz_offset_minutes)
        )
        return summary


analytics_service = AnalyticsService()
