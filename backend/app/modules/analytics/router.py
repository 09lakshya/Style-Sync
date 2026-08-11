from fastapi import APIRouter, Depends

from app.modules.analytics.service import analytics_service
from app.modules.auth.dependencies import require_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/wardrobe")
async def wardrobe_analytics(user_id: str = Depends(require_user)) -> dict[str, object]:
    return await analytics_service.get_user_wardrobe_analytics(user_id)
