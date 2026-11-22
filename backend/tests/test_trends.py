from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import connect_db, db_manager
from app.core.models import Base
from app.main import app
from app.modules.auth.service import create_access_token, register_user
from app.modules.trends import catalog
from app.modules.trends.service import TrendsService, _owns, _score_piece
from app.modules.wardrobe.repository import wardrobe_repository


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await connect_db()
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    yield


def item(**overrides):
    base = {
        "name": "Test piece",
        "type": "coat",
        "category": "outerwear",
        "primary_color": "beige",
        "secondary_colors": [],
        "pattern": "solid",
        "wear_count": 0,
    }
    base.update(overrides)
    return base


# --- scoring -------------------------------------------------------------

def test_wrong_garment_scores_zero():
    piece = {"label": "Camel coat", "types": ["coat"], "colors": ["beige"]}
    assert _score_piece(piece, item(type="skirt", category="separates", name="Skirt")) == 0.0


def test_right_garment_and_colour_is_a_full_match():
    piece = {"label": "Camel coat", "types": ["coat"], "colors": ["beige"]}
    assert _score_piece(piece, item()) == pytest.approx(1.0)


def test_right_garment_wrong_colour_still_counts_as_owned():
    piece = {"label": "Camel coat", "types": ["coat"], "colors": ["beige"]}
    score = _score_piece(piece, item(primary_color="green"))
    assert 0.0 < score < 1.0
    assert score >= 0.6  # owned, just off-palette


def test_colour_families_are_interchangeable():
    piece = {"label": "Dark jean", "types": ["jeans"], "colors": ["blue"]}
    # navy reads as blue for trend-matching purposes
    assert _score_piece(piece, item(type="jeans", primary_color="navy")) == pytest.approx(1.0)


def test_secondary_colour_can_satisfy_the_palette():
    piece = {"label": "Camel coat", "types": ["coat"], "colors": ["beige"]}
    matched = item(primary_color="black", secondary_colors=["beige"])
    assert _score_piece(piece, matched) == pytest.approx(1.0)


def test_pattern_constraint_is_enforced():
    piece = {"label": "Leopard skirt", "types": ["skirt"], "patterns": ["animal print"]}
    solid = _score_piece(piece, item(type="skirt", pattern="solid"))
    printed = _score_piece(piece, item(type="skirt", pattern="animal print"))
    assert printed > solid


def test_catalogue_entries_are_well_formed():
    ids = [t["id"] for t in catalog.TRENDS]
    assert len(ids) == len(set(ids)), "trend ids must be unique"
    for trend in catalog.TRENDS:
        assert trend["key_pieces"], f"{trend['id']} has no key pieces"
        assert 0.0 <= trend["momentum"] <= 1.0
        assert trend["styling_tips"]
        for piece in trend["key_pieces"]:
            assert piece["types"], f"{trend['id']}/{piece['label']} matches no garment"


# --- service -------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_wardrobe_scores_zero_without_failing():
    user = await register_user("Empty", "empty-trends@example.com", "Password123!")
    feed = await TrendsService().get_feed(str(user["id"]))
    assert feed["count"] == len(catalog.TRENDS)
    assert all(t["match"]["score"] == 0 for t in feed["trends"])
    assert all(t["match"]["verdict"] == "not your wardrobe yet" for t in feed["trends"])


@pytest.mark.asyncio
async def test_owned_pieces_raise_the_match_score():
    user = await register_user("Stylish", "stylish-trends@example.com", "Password123!")
    user_id = str(user["id"])
    for piece in [
        item(name="Camel overcoat", type="coat", primary_color="beige"),
        item(name="Oat knit", type="sweater", category="separates", primary_color="beige"),
        item(name="Stone trouser", type="trouser", category="separates", primary_color="beige"),
        item(name="Tan tote", type="bag", category="accessories", primary_color="brown"),
    ]:
        await wardrobe_repository.create_item({**piece, "user_id": user_id})

    trend = await TrendsService().get_trend(user_id, "quiet-luxury-neutrals")
    assert trend is not None
    assert trend["match"]["owned_count"] == trend["match"]["total_pieces"]
    assert trend["match"]["verdict"] == "ready to wear"
    assert trend["match"]["score"] >= 90
    assert trend["match"]["missing"] == []


@pytest.mark.asyncio
async def test_missing_one_piece_is_reported():
    user = await register_user("Nearly", "nearly-trends@example.com", "Password123!")
    user_id = str(user["id"])
    for piece in [
        item(name="Burgundy knit", type="sweater", category="separates", primary_color="red"),
        item(name="Wine trouser", type="trouser", category="separates", primary_color="red"),
    ]:
        await wardrobe_repository.create_item({**piece, "user_id": user_id})

    trend = await TrendsService().get_trend(user_id, "burgundy-takeover")
    assert trend["match"]["verdict"] == "one piece away"
    assert trend["match"]["missing"] == ["Oxblood boot or loafer"]


@pytest.mark.asyncio
async def test_signals_report_colour_rotation():
    user = await register_user("Signals", "signals-trends@example.com", "Password123!")
    user_id = str(user["id"])
    await wardrobe_repository.create_item(
        {**item(name="Worn navy coat", primary_color="navy", wear_count=12), "user_id": user_id}
    )
    await wardrobe_repository.create_item(
        {
            **item(name="Unworn pink dress", type="dress", primary_color="pink"),
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc) - timedelta(days=120),
        }
    )

    result = await TrendsService().get_signals(user_id)
    rotation = next(s for s in result["signals"] if s["id"] == "colour-rotation")
    assert rotation["value"] == "navy"
    assert any(s["id"] == "falling-out" for s in result["signals"])


@pytest.mark.asyncio
async def test_pieces_added_this_week_are_not_out_of_rotation():
    user = await register_user("Fresh", "fresh-trends@example.com", "Password123!")
    user_id = str(user["id"])
    for name in ("New tee", "New jeans"):
        await wardrobe_repository.create_item({**item(name=name, type="t-shirt"), "user_id": user_id})

    result = await TrendsService().get_signals(user_id)
    ids = {s["id"] for s in result["signals"]}
    assert "falling-out" not in ids
    # Nothing has been worn, so no category can be "hardest-working".
    assert "category-momentum" not in ids


# --- what counts as owning a piece --------------------------------------

def test_a_jacket_without_stripes_is_not_a_striped_blazer():
    piece = {"label": "Striped blazer", "types": ["blazer", "jacket"], "patterns": ["striped"]}
    assert not _owns(piece, item(type="jacket", name="Gold Geometric Jacket", pattern="geometric"))
    assert _owns(piece, item(type="blazer", name="Navy blazer", pattern="striped"))
    # Pattern spellings that mean the same thing still count.
    assert _owns(piece, item(type="blazer", name="Grey blazer", pattern="pinstripe"))


def test_colour_is_a_preference_not_a_requirement():
    piece = {"label": "Camel coat", "types": ["coat"], "colors": ["beige"]}
    assert _owns(piece, item(primary_color="green"))


@pytest.mark.asyncio
async def test_near_miss_is_not_ready_to_wear():
    user = await register_user("Near", "near-trends@example.com", "Password123!")
    user_id = str(user["id"])
    for piece in [
        item(name="Gold Geometric Jacket", type="jacket", pattern="geometric", primary_color="gold"),
        item(name="Grey trousers", type="pants", category="separates", primary_color="grey"),
        item(name="White shirt", type="shirt", category="separates", primary_color="white"),
    ]:
        await wardrobe_repository.create_item({**piece, "user_id": user_id})

    trend = await TrendsService().get_trend(user_id, "pinstripe-return")
    blazer = trend["match"]["pieces"][0]
    assert blazer["owned"] is False
    assert blazer["match"] is None
    assert "Gold Geometric Jacket" in blazer["note"]
    assert trend["match"]["verdict"] != "ready to wear"


# --- routes --------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_feed_route_filters_and_sorts(client):
    user = await register_user("Router", "router-trends@example.com", "Password123!")
    headers = {"Authorization": f"Bearer {create_access_token(str(user['id']))}"}

    response = await client.get("/api/v1/trends", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["season"] == catalog.CATALOG_SEASON
    momentums = [t["momentum"] for t in payload["trends"]]
    assert momentums == sorted(momentums, reverse=True)

    filtered = await client.get("/api/v1/trends?occasion=work", headers=headers)
    assert filtered.status_code == 200
    assert filtered.json()["count"] > 0
    assert all("work" in t["occasions"] for t in filtered.json()["trends"])


@pytest.mark.asyncio
async def test_unknown_trend_returns_404(client):
    user = await register_user("Missing", "missing-trends@example.com", "Password123!")
    headers = {"Authorization": f"Bearer {create_access_token(str(user['id']))}"}
    response = await client.get("/api/v1/trends/not-a-real-trend", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_feed_requires_authentication(client):
    response = await client.get("/api/v1/trends")
    assert response.status_code in (401, 403)


# --- gender personalisation ---------------------------------------------

@pytest.mark.asyncio
async def test_feed_is_filtered_to_the_profile_gender():
    male = await register_user("Man", "man-trends@example.com", "Password123!", "male")
    female = await register_user("Woman", "woman-trends@example.com", "Password123!", "female")

    male_feed = await TrendsService().get_feed(str(male["id"]))
    female_feed = await TrendsService().get_feed(str(female["id"]))

    male_ids = {t["id"] for t in male_feed["trends"]}
    female_ids = {t["id"] for t in female_feed["trends"]}

    assert male_feed["gender"] == "male"
    assert "modern-indian-drape" not in male_ids
    assert "modern-bandhgala" in male_ids
    assert "modern-indian-drape" in female_ids
    assert "modern-bandhgala" not in female_ids
    # The shared looks are shared, not duplicated per gender.
    assert "quiet-luxury-neutrals" in male_ids & female_ids


@pytest.mark.asyncio
async def test_unspecified_and_non_binary_see_every_trend():
    for email, gender in (("nb-trends@example.com", "non-binary"), ("un-trends@example.com", "unspecified")):
        user = await register_user("Anyone", email, "Password123!", gender)
        feed = await TrendsService().get_feed(str(user["id"]))
        assert feed["count"] == len(catalog.TRENDS), gender


@pytest.mark.asyncio
async def test_all_genders_override_restores_the_full_feed():
    user = await register_user("Man", "override-trends@example.com", "Password123!", "male")
    filtered = await TrendsService().get_feed(str(user["id"]))
    everything = await TrendsService().get_feed(str(user["id"]), include_all_genders=True)
    assert everything["count"] > filtered["count"]
    assert everything["count"] == len(catalog.TRENDS)


def test_every_trend_declares_who_it_is_cut_for():
    for trend in catalog.TRENDS:
        assert trend["genders"], f"{trend['id']} declares no genders"
        assert set(trend["genders"]) <= {"female", "male"}


def test_the_catalogue_is_not_lopsided():
    """Filtering by gender must not leave one of them with a thin feed."""
    for gender in ("female", "male"):
        count = sum(1 for t in catalog.TRENDS if gender in t["genders"])
        assert count >= 10, f"only {count} trends for {gender}"
