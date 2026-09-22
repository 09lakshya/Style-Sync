from pydantic import BaseModel
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.modules.auth.dependencies import require_user
from app.modules.media.validator import validate_image_bytes
from app.modules.wardrobe.service import wardrobe_service

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


class UpdateWardrobeItemSchema(BaseModel):
    name: str | None = None
    color: str | None = None
    pattern: str | None = None
    brand: str | None = None
    purchase_date: str | None = None
    occasion: str | list[str] | None = None
    last_worn_date: str | None = None
    wear_count: int | None = None


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


@router.post("/detect")
async def detect_wardrobe_item(
    image: UploadFile = File(...),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Detect a garment's attributes without saving it.

    The add-item form calls this as soon as a photo is chosen so the fields
    arrive filled in; nothing is stored and the user can still edit every value
    before submitting.
    """
    file_bytes = await image.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image upload.")

    validate_image_bytes(file_bytes, image.content_type or "image/jpeg")

    return await wardrobe_service.detect_item_metadata(
        file_bytes=file_bytes,
        filename=image.filename or "wardrobe-item.jpg",
    )


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def upload_wardrobe_item(
    image: UploadFile | None = File(default=None),
    name: str | None = Form(default=None),
    color: str | None = Form(default=None),
    pattern: str | None = Form(default=None),
    brand: str | None = Form(default=None),
    purchase_date: str | None = Form(default=None),
    occasion: str | None = Form(default=None),
    last_worn_date: str | None = Form(default=None),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Upload a new wardrobe item image, validate, store in Cloudinary, and save metadata to database."""
    file_bytes = await image.read() if image else None
    if file_bytes is not None and len(file_bytes) == 0:
        file_bytes = None
    filename = (image.filename if image and image.filename else "wardrobe-item.jpg")
    content_type = image.content_type if image else None
    item = await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        file_bytes=file_bytes,
        filename=filename,
        name=name,
        color=color,
        pattern=pattern,
        brand=brand,
        purchase_date=purchase_date,
        occasion=occasion,
        last_worn_date=last_worn_date,
        content_type=content_type,
    )
    return {"item": _public_item(item)}



@router.put("/items/{item_id}")
async def update_wardrobe_item(
    item_id: str,
    payload: UpdateWardrobeItemSchema,
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Update metadata of a dress item (without re-uploading image)."""
    item = await wardrobe_service.update_wardrobe_item_metadata(
        user_id=user_id,
        item_id=item_id,
        name=payload.name,
        color=payload.color,
        pattern=payload.pattern,
        brand=payload.brand,
        purchase_date=payload.purchase_date,
        occasion=payload.occasion,
        last_worn_date=payload.last_worn_date,
        wear_count=payload.wear_count,
    )
    return {"item": _public_item(item)}


@router.put("/items/{item_id}/image")
async def replace_wardrobe_item_image(
    item_id: str,
    image: UploadFile = File(...),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Replace an existing wardrobe item's image in Cloudinary and database."""
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
    """Filter out private/embedding fields and return normalized dict."""
    res = {key: value for key, value in item.items() if key != "embedding"}
    if "primary_color" in res and "color" not in res:
        res["color"] = res["primary_color"]
    if "last_worn_at" in res and "last_worn_date" not in res:
        res["last_worn_date"] = res["last_worn_at"]
    return res

