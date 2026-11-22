from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.core.database import connect_db, db_manager
from app.core.models import Base
from app.modules.analytics.service import analytics_service, is_long_unused, start_of_local_day
from app.modules.auth.service import register_user
from app.modules.shopping.repository import shopping_repository
from app.modules.wardrobe.repository import wardrobe_repository

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await connect_db()
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    yield


def test_long_unused_goes_by_when_it_was_last_worn_not_how_often():
    worn_long_ago = {"wear_count": 40, "last_worn_at": (NOW - timedelta(days=120)).isoformat()}
    worn_recently = {"wear_count": 0, "last_worn_at": (NOW - timedelta(days=3)).isoformat()}
    assert is_long_unused(worn_long_ago, NOW)
    assert not is_long_unused(worn_recently, NOW)


def test_a_never_worn_piece_gets_a_grace_period():
    just_added = {"created_at": (NOW - timedelta(days=2)).isoformat()}
    added_ages_ago = {"created_at": (NOW - timedelta(days=60)).isoformat()}
    assert not is_long_unused(just_added, NOW)
    assert is_long_unused(added_ages_ago, NOW)


def test_today_starts_at_the_viewers_midnight():
    # 02:00 UTC is 07:30 in India (offset -330), whose day began at 18:30 UTC.
    early = datetime(2026, 11, 22, 2, 0, tzinfo=timezone.utc)
    assert start_of_local_day(early, -330) == datetime(2026, 11, 21, 18, 30, tzinfo=timezone.utc)
    assert start_of_local_day(early, 0) == datetime(2026, 11, 22, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_duplicate_checks_are_counted_from_the_log_and_colours_ignore_case():
    user = await register_user("Stats", "stats@example.com", "Password123!")
    user_id = str(user["id"])
    for color in ("Maroon", "maroon", "black"):
        await wardrobe_repository.create_item(
            {"user_id": user_id, "name": color, "type": "top", "primary_color": color}
        )
    for _ in range(2):
        await shopping_repository.log_check(user_id, "", [], "no_strong_duplicate", 0.1)

    stats = await analytics_service.get_user_wardrobe_analytics(user_id)
    assert stats["duplicate_checks_today"] == 2
    assert stats["most_common_color"] == "maroon"
