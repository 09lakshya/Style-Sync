import pytest
import pytest_asyncio

from app.core.database import connect_db, db_manager
from app.core.models import Base
from app.modules.auth.service import register_user
from app.modules.outfits import rules
from app.modules.outfits.service import OutfitService
from app.modules.wardrobe.repository import wardrobe_repository


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await connect_db()
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    yield


def piece(**overrides):
    base = {
        "name": "Piece",
        "type": "shirt",
        "primary_color": "white",
        "secondary_colors": [],
        "pattern": "solid",
        "occasion": ["casual"],
        "season": ["all_season"],
        "tags": [],
        "wear_count": 0,
    }
    base.update(overrides)
    return base


# --- rules ---------------------------------------------------------------

def test_garments_land_in_the_right_slot():
    assert rules.slot_of(piece(type="kurti")) == "top"
    assert rules.slot_of(piece(type="palazzo")) == "bottom"
    assert rules.slot_of(piece(type="saree")) == "one_piece"
    assert rules.slot_of(piece(type="blazer")) == "layer"
    assert rules.slot_of(piece(type="dupatta")) == "accessory"


def test_a_neutral_never_clashes():
    assert not rules.clashes({"white"}, {"red"})
    assert not rules.clashes({"black"}, {"green"})


def test_opposing_saturated_colours_clash():
    assert rules.clashes({"red"}, {"teal"})


def test_same_family_is_not_a_clash():
    assert rules.same_family({"navy"}, {"blue"})
    assert not rules.clashes({"navy"}, {"blue"})


def test_shared_occasion_wins_and_all_season_never_excludes():
    occasion, agreed, covered = rules.resolve_occasion(
        [piece(occasion=["work", "casual"]), piece(occasion=["casual"])]
    )
    assert (occasion, agreed) == ("casual", True)
    assert covered == ["casual"]
    assert rules.shared_seasons([piece(season=["winter"]), piece(season=["all_season"])]) == {"winter"}


def test_without_a_shared_occasion_the_dressier_piece_decides():
    occasion, agreed, covered = rules.resolve_occasion(
        [piece(occasion=["party"]), piece(occasion=["casual"])]
    )
    assert occasion == "party"
    assert agreed is False
    assert covered == ["party"]


def test_an_outfit_is_listed_under_every_occasion_it_covers():
    """A shirt and jeans both logged casual and day-out belong in both sections."""
    occasion, agreed, covered = rules.resolve_occasion(
        [piece(occasion=["casual", "day_out"]), piece(occasion=["casual", "day_out"])]
    )
    assert agreed is True
    assert covered == ["casual", "day_out"]
    assert occasion == "day_out"


# --- service -------------------------------------------------------------

async def build(user_id, items):
    for item in items:
        await wardrobe_repository.create_item({**item, "user_id": user_id})
    return await OutfitService().suggest(user_id, limit=20)


@pytest.mark.asyncio
async def test_a_top_and_a_bottom_make_an_outfit():
    user = await register_user("Pairer", "pairs@example.com", "Password123!")
    result = await build(
        str(user["id"]),
        [
            piece(name="White shirt", type="shirt"),
            piece(name="Navy trousers", type="pants", primary_color="navy"),
        ],
    )
    assert result["count"] == 1
    outfit = result["outfits"][0]
    assert {p["role"] for p in outfit["pieces"]} == {"top", "bottom"}
    assert outfit["occasion"] == "casual"
    assert outfit["reasons"], "an outfit must explain itself"


@pytest.mark.asyncio
async def test_a_saree_is_an_outfit_on_its_own():
    user = await register_user("Drape", "drape@example.com", "Password123!")
    result = await build(str(user["id"]), [piece(name="Red saree", type="saree", primary_color="red")])
    assert result["count"] == 1
    assert result["outfits"][0]["pieces"][0]["role"] == "one_piece"


@pytest.mark.asyncio
async def test_clashing_pairs_rank_below_tonal_ones():
    user = await register_user("Ranker", "rank@example.com", "Password123!")
    result = await build(
        str(user["id"]),
        [
            piece(name="Red top", type="top", primary_color="red"),
            piece(name="Teal trouser", type="pants", primary_color="teal"),
            piece(name="Navy knit", type="sweater", primary_color="navy"),
            piece(name="Blue jeans", type="jeans", primary_color="blue"),
        ],
    )
    ranked = [o["pieces"][0]["name"] for o in result["outfits"]]
    assert ranked[0] == "Navy knit", result["outfits"][0]
    clashing = next(o for o in result["outfits"] if o["pieces"][0]["name"] == "Red top"
                    and o["pieces"][1]["name"] == "Teal trouser")
    assert clashing["warnings"]


@pytest.mark.asyncio
async def test_kurta_with_jeans_is_allowed_but_kurta_with_shorts_is_flagged():
    user = await register_user("Cross", "cross@example.com", "Password123!")
    result = await build(
        str(user["id"]),
        [
            piece(name="Cream kurta", type="kurta", primary_color="cream", tags=["ethnic"]),
            piece(name="Indigo jeans", type="jeans", primary_color="blue"),
            piece(name="Khaki shorts", type="shorts", primary_color="beige"),
        ],
    )
    jeans = next(o for o in result["outfits"] if o["pieces"][1]["name"] == "Indigo jeans")
    shorts = next(o for o in result["outfits"] if o["pieces"][1]["name"] == "Khaki shorts")
    assert jeans["score"] > shorts["score"]
    assert jeans["style"] == "fusion"
    assert jeans["styles"] == ["fusion", "traditional"]


@pytest.mark.asyncio
async def test_two_loud_patterns_are_warned_about():
    user = await register_user("Loud", "loud@example.com", "Password123!")
    result = await build(
        str(user["id"]),
        [
            piece(name="Floral top", type="top", pattern="floral"),
            piece(name="Paisley skirt", type="skirt", pattern="paisley", primary_color="beige"),
        ],
    )
    assert result["outfits"], "a questionable outfit should still be offered, with the caveat"
    assert any("competing" in w for w in result["outfits"][0]["warnings"])


@pytest.mark.asyncio
async def test_fresh_sort_surfaces_the_unworn():
    user = await register_user("Fresh", "fresh@example.com", "Password123!")
    user_id = str(user["id"])
    for item in [
        piece(name="Worn shirt", type="shirt", wear_count=20),
        piece(name="Unworn shirt", type="shirt", wear_count=0),
        piece(name="Trousers", type="pants", primary_color="navy", wear_count=5),
    ]:
        await wardrobe_repository.create_item({**item, "user_id": user_id})

    fresh = await OutfitService().suggest(user_id, sort="fresh", limit=10)
    assert fresh["outfits"][0]["pieces"][0]["name"] == "Unworn shirt"


@pytest.mark.asyncio
async def test_a_wardrobe_of_only_tops_says_what_is_missing():
    user = await register_user("Gaps", "gaps@example.com", "Password123!")
    result = await build(str(user["id"]), [piece(name="Shirt", type="shirt")])
    assert result["count"] == 0
    assert any("bottom" in gap.lower() for gap in result["gaps"])


@pytest.mark.asyncio
async def test_occasion_filter_only_returns_that_occasion():
    user = await register_user("Filter", "filter@example.com", "Password123!")
    user_id = str(user["id"])
    for item in [
        piece(name="Work shirt", type="shirt", occasion=["work"]),
        piece(name="Work trouser", type="pants", primary_color="grey", occasion=["work"]),
        piece(name="Party top", type="top", primary_color="black", occasion=["party"]),
        piece(name="Party skirt", type="skirt", primary_color="black", occasion=["party"]),
    ]:
        await wardrobe_repository.create_item({**item, "user_id": user_id})

    work = await OutfitService().suggest(user_id, occasion="work", limit=10)
    assert work["count"] >= 1
    assert all(o["occasion"] == "work" for o in work["outfits"])


# --- the tradition axis --------------------------------------------------

def test_a_kurta_with_a_churidar_is_traditional_outright():
    style, styles, note = rules.resolve_styles(
        [piece(type="kurta", tags=["ethnic"]), piece(type="churidar", tags=["ethnic"])]
    )
    assert style == "traditional"
    assert styles == ["traditional"]
    assert note


def test_a_kurta_with_jeans_is_listed_as_fusion_and_traditional():
    """The user's case: it is casual, and a little traditional - so it appears
    in both places rather than being forced onto one."""
    style, styles, note = rules.resolve_styles(
        [piece(type="kurta", tags=["ethnic"]), piece(type="jeans")]
    )
    assert style == "fusion"
    assert styles == ["fusion", "traditional"]
    assert "leans traditional" in note


def test_a_short_kurti_with_jeans_reads_as_everyday_with_a_traditional_note():
    _, styles, note = rules.resolve_styles(
        [piece(type="kurti", tags=["ethnic"]), piece(type="jeans")]
    )
    assert styles == ["fusion", "traditional"]
    assert "everyday wear with a traditional note" in note


def test_two_western_pieces_are_only_western():
    style, styles, _ = rules.resolve_styles([piece(type="shirt"), piece(type="jeans")])
    assert (style, styles) == ("western", ["western"])


def test_a_dhoti_under_a_kurta_is_traditional():
    style, styles, _ = rules.resolve_styles(
        [piece(type="kurta", tags=["ethnic"]), piece(type="dhoti", tags=["ethnic"])]
    )
    assert (style, styles) == ("traditional", ["traditional"])


@pytest.mark.asyncio
async def test_style_filter_returns_fusion_outfits():
    user = await register_user("Styles", "styles@example.com", "Password123!")
    user_id = str(user["id"])
    for item in [
        piece(name="Cream kurta", type="kurta", primary_color="cream", tags=["ethnic"]),
        piece(name="Indigo jeans", type="jeans", primary_color="blue"),
        piece(name="White shirt", type="shirt"),
    ]:
        await wardrobe_repository.create_item({**item, "user_id": user_id})

    fusion = await OutfitService().suggest(user_id, style="fusion", limit=10)
    assert fusion["count"] == 1
    assert fusion["outfits"][0]["style"] == "fusion"

    traditional = await OutfitService().suggest(user_id, style="traditional", limit=10)
    assert traditional["count"] == 1, "the fusion outfit is also findable under traditional"
