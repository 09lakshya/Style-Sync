from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.modules.auth.dependencies import require_user
from app.modules.wardrobe.service import wardrobe_service

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


@router.get("/items")
async def get_wardrobe_items(
    type: str | None = None,
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """List all wardrobe items for the authenticated user."""
    items = await wardrobe_service.get_user_items(user_id, type)
    return {"items": [_public_item(item) for item in items]}


@router.get("/items/{item_id}")
async def get_wardrobe_item(
    item_id: str,
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Retrieve a single wardrobe item by ID."""
    item = await wardrobe_service.get_item_by_id(item_id, user_id)
    return {"item": _public_item(item)}


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def upload_wardrobe_item(
    image: UploadFile = File(...),
    name: str | None = Form(default=None),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Upload a new wardrobe item image, validate, store in Cloudinary, and save to MongoDB."""
    file_bytes = await image.read()
    item = await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        file_bytes=file_bytes,
        filename=image.filename or "wardrobe-item.jpg",
        name=name,
        content_type=image.content_type,
    )
    return {"item": _public_item(item)}


@router.put("/items/{item_id}/image")
async def replace_wardrobe_item_image(
    item_id: str,
    image: UploadFile = File(...),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Replace an existing wardrobe item's image in Cloudinary and MongoDB."""
    file_bytes = await image.read()
    item = await wardrobe_service.replace_item_image(
        user_id=user_id,
        item_id=item_id,
        file_bytes=file_bytes,
        filename=image.filename or "wardrobe-item.jpg",
        content_type=image.content_type,
    )
    return {"item": _public_item(item)}


@router.delete("/items/{item_id}")
async def delete_wardrobe_item(
    item_id: str,
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Delete a wardrobe item and its corresponding Cloudinary asset and vector embeddings."""
    success = await wardrobe_service.delete_wardrobe_item(user_id, item_id)
    return {"success": success, "deleted_item_id": item_id}


@router.post("/items/{item_id}/wear")
async def record_item_worn(
    item_id: str,
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Increment the wear count for a wardrobe item."""
    item = await wardrobe_service.record_item_worn(item_id, user_id)
    return {"item": _public_item(item)}


def _public_item(item: dict[str, object]) -> dict[str, object]:
    """Filter out private/embedding fields before returning to frontend."""
    return {key: value for key, value in item.items() if key != "embedding"}
