import io
import pytest
import pytest_asyncio
from PIL import Image
from httpx import ASGITransport, AsyncClient
from app.core.config import settings
from app.core.database import connect_db, db_manager
from app.core.models import Base
from app.main import app
from app.modules.auth.service import create_access_token, register_user
from app.modules.media.cloudinary_service import cloudinary_service
from app.modules.media.validator import validate_image_bytes
from app.modules.wardrobe.repository import wardrobe_repository
from app.modules.wardrobe.service import wardrobe_service


def create_test_image_bytes(format: str = "JPEG", size: tuple[int, int] = (200, 200), color: str = "blue") -> bytes:
    """Helper to generate valid in-memory image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Initialize SQLAlchemy engine and recreate fresh tables for test isolation."""
    await connect_db()
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_successful_image_upload_and_metadata():
    """Verify image upload creates document with Cloudinary URLs, public_id, and dimensions."""
    user_id = "usr-cloudinary-1"
    image_bytes = create_test_image_bytes(format="JPEG", size=(300, 400), color="navy")

    item = await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        file_bytes=image_bytes,
        filename="navy_linen_shirt.jpg",
        name="Navy Linen Shirt",
        content_type="image/jpeg",
    )

    assert item is not None
    assert item["name"] == "Navy Linen Shirt"
    assert "public_id" in item and item["public_id"].startswith("stylesync/users/usr-cloudinary-1/wardrobe/")
    assert "image_url" in item and item["image_url"] != ""
    assert "thumbnail_url" in item and item["thumbnail_url"] != ""
    assert item["width"] == 300
    assert item["height"] == 400
    assert item["bytes"] == len(image_bytes)
    assert item["format"] == "jpg"

    # Verify saved in database
    saved = await wardrobe_repository.get_item_by_id(item["id"], user_id)
    assert saved is not None
    assert saved["public_id"] == item["public_id"]


@pytest.mark.asyncio
async def test_invalid_image_payload_rejection():
    """Verify non-image and corrupted data are rejected with 415/400."""
    fake_payload = b"NOT_A_VALID_IMAGE_BINARY_DATA_CORRUPTED_STREAM"

    with pytest.raises(Exception) as exc_info:
        validate_image_bytes(fake_payload, "image/jpeg")

    assert "415" in str(exc_info.value) or "not a valid or supported image" in str(exc_info.value)


@pytest.mark.asyncio
async def test_oversized_image_rejection():
    """Verify oversized payload exceeding max limit is rejected with 413."""
    # Temporarily set max size to 100 bytes to test limit rejection
    original_limit = settings.max_upload_size_bytes
    try:
        settings.max_upload_size_bytes = 100
        image_bytes = create_test_image_bytes(format="JPEG", size=(200, 200))

        with pytest.raises(Exception) as exc_info:
            validate_image_bytes(image_bytes, "image/jpeg")

        assert "413" in str(exc_info.value) or "exceeds the maximum allowed limit" in str(exc_info.value)
    finally:
        settings.max_upload_size_bytes = original_limit


@pytest.mark.asyncio
async def test_delete_wardrobe_item_workflow():
    """Verify deleting wardrobe item cleans up database and triggers asset removal."""
    user_id = "usr-cloudinary-delete"
    image_bytes = create_test_image_bytes(format="PNG", size=(150, 150), color="green")

    item = await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        file_bytes=image_bytes,
        filename="green_dress.png",
        content_type="image/png",
    )

    item_id = str(item["id"])
    assert await wardrobe_repository.get_item_by_id(item_id, user_id) is not None

    # Delete item
    deleted = await wardrobe_service.delete_wardrobe_item(user_id, item_id)
    assert deleted is True

    # Subsequent fetch should raise 404
    with pytest.raises(Exception) as exc_info:
        await wardrobe_service.get_item_by_id(item_id, user_id)
    assert "404" in str(exc_info.value)


@pytest.mark.asyncio
async def test_replace_image_workflow():
    """Verify replacing an item's image updates references and dimensions."""
    user_id = "usr-cloudinary-replace"
    img1 = create_test_image_bytes(format="JPEG", size=(100, 100), color="red")
    img2 = create_test_image_bytes(format="JPEG", size=(400, 500), color="yellow")

    item = await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        file_bytes=img1,
        filename="red_top.jpg",
        content_type="image/jpeg",
    )

    item_id = str(item["id"])
    updated = await wardrobe_service.replace_item_image(
        user_id=user_id,
        item_id=item_id,
        file_bytes=img2,
        filename="yellow_top.jpg",
        content_type="image/jpeg",
    )

    assert updated["width"] == 400
    assert updated["height"] == 500
    assert updated["bytes"] == len(img2)


@pytest.mark.asyncio
async def test_unauthorized_user_isolation():
    """Verify User B cannot access or delete User A's wardrobe items."""
    user_a = "usr-owner-a"
    user_b = "usr-intruder-b"

    image_bytes = create_test_image_bytes(format="JPEG", size=(120, 120))
    item = await wardrobe_service.create_item_from_upload(
        user_id=user_a,
        file_bytes=image_bytes,
        filename="owner_jacket.jpg",
        content_type="image/jpeg",
    )

    item_id = str(item["id"])

    # User B cannot get User A's item
    with pytest.raises(Exception) as exc_info:
        await wardrobe_service.get_item_by_id(item_id, user_b)
    assert "404" in str(exc_info.value)

    # User B cannot delete User A's item
    with pytest.raises(Exception) as exc_info:
        await wardrobe_service.delete_wardrobe_item(user_b, item_id)
    assert "404" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fastapi_wardrobe_api_end_to_end():
    """Verify HTTP API endpoints for wardrobe upload, get, replace, and delete."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"name": "Cloudinary Tester", "email": "cloud@stylesync.dev", "password": "SecurePassword123!"},
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Upload item via multipart
        image_bytes = create_test_image_bytes(format="JPEG", size=(250, 350), color="purple")
        files = {"image": ("purple_blazer.jpg", image_bytes, "image/jpeg")}
        data = {"name": "Purple Blazer"}

        upload_res = await client.post("/api/v1/wardrobe/items", headers=headers, files=files, data=data)
        assert upload_res.status_code == 201
        item_payload = upload_res.json()["item"]
        assert item_payload["name"] == "Purple Blazer"
        assert item_payload["width"] == 250
        assert item_payload["height"] == 350
        item_id = item_payload["id"]

        # 3. Get single item
        get_res = await client.get(f"/api/v1/wardrobe/items/{item_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["item"]["id"] == item_id

        # 4. Replace image via PUT
        new_img_bytes = create_test_image_bytes(format="JPEG", size=(300, 300), color="magenta")
        put_res = await client.put(
            f"/api/v1/wardrobe/items/{item_id}/image",
            headers=headers,
            files={"image": ("magenta_blazer.jpg", new_img_bytes, "image/jpeg")},
        )
        assert put_res.status_code == 200
        assert put_res.json()["item"]["width"] == 300

        # 5. Delete item via DELETE
        del_res = await client.delete(f"/api/v1/wardrobe/items/{item_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # 6. Verify item is deleted
        get_deleted = await client.get(f"/api/v1/wardrobe/items/{item_id}", headers=headers)
        assert get_deleted.status_code == 404
