import io
import pytest
import pytest_asyncio
from PIL import Image
from httpx import ASGITransport, AsyncClient

from app.core.database import connect_db, db_manager
from app.core.models import Base
from app.main import app
from app.modules.auth.service import create_access_token, register_user


def create_dummy_jpeg() -> bytes:
    img = Image.new("RGB", (200, 200), color=(100, 150, 200))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await connect_db()
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_dress_wardrobe_crud_and_user_isolation():
    # 1. Register User A and User B
    user_a = await register_user("User A", "usera@example.com", "Password123!")
    user_b = await register_user("User B", "userb@example.com", "Password123!")

    token_a = create_access_token(user_a["id"])
    token_b = create_access_token(user_b["id"])

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as client:
        # 2. User A uploads a dress with complete metadata
        jpeg_bytes = create_dummy_jpeg()
        files = {"image": ("blue_dress.jpg", jpeg_bytes, "image/jpeg")}
        data = {
            "name": "Blue Floral Summer Dress",
            "color": "Blue",
            "pattern": "Floral",
            "brand": "Zara",
            "purchase_date": "2026-05-10",
            "occasion": "Casual",
            "last_worn_date": "2026-08-01",
        }

        resp_upload = await client.post("/wardrobe/items", data=data, files=files, headers=headers_a)
        assert resp_upload.status_code == 201, resp_upload.text
        item_a = resp_upload.json()["item"]

        assert item_a["name"] == "Blue Floral Summer Dress"
        assert item_a["primary_color"] == "Blue"
        assert item_a["pattern"] == "Floral"
        assert item_a["brand"] == "Zara"
        assert item_a["user_id"] == user_a["id"]
        assert "image_url" in item_a
        assert "thumbnail_url" in item_a
        item_id = item_a["id"]

        # 3. User A can view the dress item detail
        resp_get_a = await client.get(f"/wardrobe/items/{item_id}", headers=headers_a)
        assert resp_get_a.status_code == 200
        assert resp_get_a.json()["item"]["id"] == item_id

        # 4. User B CANNOT view User A's dress (User isolation test -> 404)
        resp_get_b = await client.get(f"/wardrobe/items/{item_id}", headers=headers_b)
        assert resp_get_b.status_code == 404

        # 5. User B CANNOT list User A's dress
        resp_list_b = await client.get("/wardrobe/items", headers=headers_b)
        assert resp_list_b.status_code == 200
        items_b = resp_list_b.json()["items"]
        assert not any(i["id"] == item_id for i in items_b)

        # 6. User B CANNOT edit User A's dress metadata (-> 404)
        resp_update_b = await client.put(
            f"/wardrobe/items/{item_id}",
            json={"name": "Hacked Dress Name"},
            headers=headers_b,
        )
        assert resp_update_b.status_code == 404

        # 7. User A updates dress metadata via PUT
        resp_update_a = await client.put(
            f"/wardrobe/items/{item_id}",
            json={
                "name": "Updated Blue Dress",
                "color": "Navy Blue",
                "brand": "Mango",
                "occasion": "Formal",
            },
            headers=headers_a,
        )
        assert resp_update_a.status_code == 200
        updated_item = resp_update_a.json()["item"]
        assert updated_item["name"] == "Updated Blue Dress"
        assert updated_item["primary_color"] == "Navy Blue"
        assert updated_item["brand"] == "Mango"
        assert updated_item["occasion"] == ["Formal"]

        # 8. User A replaces image
        files_new = {"image": ("replaced_dress.jpg", jpeg_bytes, "image/jpeg")}
        resp_img_a = await client.put(f"/wardrobe/items/{item_id}/image", files=files_new, headers=headers_a)
        assert resp_img_a.status_code == 200
        assert resp_img_a.json()["item"]["id"] == item_id

        # 9. User B CANNOT delete User A's dress (-> 404)
        resp_del_b = await client.delete(f"/wardrobe/items/{item_id}", headers=headers_b)
        assert resp_del_b.status_code == 404

        # 10. User A deletes dress successfully
        resp_del_a = await client.delete(f"/wardrobe/items/{item_id}", headers=headers_a)
        assert resp_del_a.status_code == 200
        assert resp_del_a.json()["success"] is True

        # Verify it's gone
        resp_get_after = await client.get(f"/wardrobe/items/{item_id}", headers=headers_a)
        assert resp_get_after.status_code == 404
