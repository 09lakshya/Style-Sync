import io
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.database import connect_db, db_manager
from app.core.models import Base
from app.main import app
from app.modules.auth.service import create_access_token, register_user
from app.modules.wardrobe import normalise as norm


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await connect_db()
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    yield


def jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (200, 200), color=(120, 30, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


# --- the rules ------------------------------------------------------------

def test_colours_and_patterns_have_one_spelling():
    assert norm.normalise_color(" Maroon ") == "maroon"
    assert norm.normalise_pattern("Block Print") == "block print"
    assert norm.normalise_pattern("polka_dot") == "polka dot"


def test_everyday_garment_words_map_onto_known_types():
    assert norm.normalise_type("Trouser") == "pants"
    assert norm.normalise_type("tee") == "t-shirt"
    assert norm.normalise_type("Kurti") == "kurti"


def test_occasions_use_the_outfit_builders_vocabulary():
    assert norm.normalise_occasions(["Office", "College", "Travel", "Party", "Other"]) == [
        "work", "casual", "day_out", "party",
    ]
    assert norm.normalise_occasions("Traditional") == ["festive"]


def test_seasons_are_canonical():
    assert norm.normalise_seasons(["Autumn", "All Season", "summer", "monsoon"]) == [
        "fall", "all_season", "summer",
    ]


def test_normalise_item_moves_category_and_tags_with_the_type():
    changes = norm.normalise_item(
        {"type": "trouser", "category": "dresses", "tags": ["trouser", "solid"], "primary_color": "Black"}
    )
    assert changes["type"] == "pants"
    assert changes["category"] == "separates"
    assert "pants" in changes["tags"] and "trouser" not in changes["tags"]
    assert changes["primary_color"] == "black"


# --- through the API -----------------------------------------------------

async def _client_and_headers(email: str):
    user = await register_user("Tester", email, "Password123!")
    headers = {"Authorization": f"Bearer {create_access_token(user['id'])}"}
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver/api/v1")
    return client, headers


@pytest.mark.asyncio
async def test_saving_keeps_what_the_form_was_detected_with():
    """Seasons, fabric and the other occasions come from the detection the form
    was filled from, not from a second local read of the photo."""
    client, headers = await _client_and_headers("detect@example.com")
    detected = {
        "name": "Spaghetti Bodycon Maxi Dress",
        "type": "dress",
        "season": ["Winter", "Fall"],
        "fabric": "Velvet",
        "secondary_colors": ["Black"],
        "sleeve_type": "sleeveless",
        "occasion": ["party", "wedding", "office"],
        "tags": ["#bodycon", "#maxi"],
    }
    async with client:
        resp = await client.post(
            "/wardrobe/items",
            data={"color": "Maroon", "pattern": "Solid", "occasion": "party", "item_type": "dress",
                  "detected": json.dumps(detected)},
            files={"image": ("dress.jpg", jpeg(), "image/jpeg")},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    item = resp.json()["item"]
    assert item["name"] == "Spaghetti Bodycon Maxi Dress"
    assert item["season"] == ["winter", "fall"]
    assert item["fabric"] == "velvet"
    assert item["secondary_colors"] == ["black"]
    assert item["sleeve_type"] == "sleeveless"
    assert item["occasion"] == ["party", "wedding", "work"]
    assert item["primary_color"] == "maroon"
    assert item["pattern"] == "solid"


@pytest.mark.asyncio
async def test_a_malformed_detection_does_not_block_saving():
    client, headers = await _client_and_headers("bad@example.com")
    async with client:
        resp = await client.post(
            "/wardrobe/items",
            data={"name": "Shirt", "color": "White", "occasion": "casual", "detected": "{not json"},
            files={"image": ("shirt.jpg", jpeg(), "image/jpeg")},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_type_and_seasons_can_be_corrected_and_survive_a_new_photo():
    client, headers = await _client_and_headers("edit@example.com")
    async with client:
        created = await client.post(
            "/wardrobe/items",
            data={"name": "Mermaid", "color": "Maroon", "occasion": "party", "item_type": "gown"},
            files={"image": ("gown.jpg", jpeg(), "image/jpeg")},
            headers=headers,
        )
        item_id = created.json()["item"]["id"]

        resp = await client.put(
            f"/wardrobe/items/{item_id}",
            json={"item_type": "Dress", "season": ["Winter"], "occasion": ["Party", "Wedding"]},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        item = resp.json()["item"]
        assert item["type"] == "dress"
        assert item["category"] == "one_piece"
        assert item["season"] == ["winter"]
        assert item["occasion"] == ["party", "wedding"]

        replaced = await client.put(
            f"/wardrobe/items/{item_id}/image",
            files={"image": ("new.jpg", jpeg(), "image/jpeg")},
            headers=headers,
        )
        assert replaced.status_code == 200
        kept = replaced.json()["item"]
        assert kept["type"] == "dress"
        assert kept["season"] == ["winter"]
        assert kept["occasion"] == ["party", "wedding"]

        empty = await client.put(
            f"/wardrobe/items/{item_id}", json={"season": []}, headers=headers
        )
        assert empty.status_code == 422
