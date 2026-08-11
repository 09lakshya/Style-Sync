from fastapi import APIRouter, Depends, File, UploadFile

from app.modules.auth.dependencies import require_user
from app.modules.shopping.service import shopping_service

router = APIRouter(prefix="/shopping", tags=["shopping"])


@router.post("/check")
async def check_duplicate_purchase(
    image: UploadFile = File(...),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    filename = image.filename or "shopping-item.jpg"
    file_bytes = await image.read()
    return await shopping_service.check_duplicate_purchase(
        user_id=user_id,
        filename=filename,
        file_bytes=file_bytes,
    )
