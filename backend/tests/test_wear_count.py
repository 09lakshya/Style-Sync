import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.core.database import connect_db, db_manager
from app.core.models import Base
from app.modules.wardrobe.service import wardrobe_service
from tests.test_cloudinary import create_test_image_bytes


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await connect_db()
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    yield


async def _create_item(user_id: str) -> str:
    item = await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        file_bytes=create_test_image_bytes(format="JPEG", size=(120, 160), color="navy"),
        filename="navy_shirt.jpg",
        name="Navy Shirt",
        content_type="image/jpeg",
    )
    return str(item["id"])


@pytest.mark.asyncio
async def test_marking_worn_adds_one_and_stamps_last_worn():
    user_id = "usr-wear-1"
    item_id = await _create_item(user_id)

    first = await wardrobe_service.record_item_worn(item_id, user_id)
    assert first["wear_count"] == 1
    assert first["last_worn_at"] is not None

    second = await wardrobe_service.record_item_worn(item_id, user_id)
    assert second["wear_count"] == 2


@pytest.mark.asyncio
async def test_wear_count_can_be_corrected_up_or_down():
    user_id = "usr-wear-2"
    item_id = await _create_item(user_id)
    await wardrobe_service.record_item_worn(item_id, user_id)

    raised = await wardrobe_service.update_wardrobe_item_metadata(
        user_id=user_id, item_id=item_id, wear_count=12
    )
    assert raised["wear_count"] == 12

    lowered = await wardrobe_service.update_wardrobe_item_metadata(
        user_id=user_id, item_id=item_id, wear_count=0
    )
    assert lowered["wear_count"] == 0


@pytest.mark.asyncio
async def test_other_edits_leave_the_wear_count_alone():
    user_id = "usr-wear-3"
    item_id = await _create_item(user_id)
    await wardrobe_service.record_item_worn(item_id, user_id)

    updated = await wardrobe_service.update_wardrobe_item_metadata(
        user_id=user_id, item_id=item_id, name="Renamed"
    )
    assert updated["name"] == "Renamed"
    assert updated["wear_count"] == 1


@pytest.mark.asyncio
async def test_negative_wear_count_is_rejected():
    user_id = "usr-wear-4"
    item_id = await _create_item(user_id)

    with pytest.raises(HTTPException) as exc:
        await wardrobe_service.update_wardrobe_item_metadata(
            user_id=user_id, item_id=item_id, wear_count=-1
        )
    assert exc.value.status_code == 422
