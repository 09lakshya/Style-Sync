from fastapi import APIRouter, Depends, Query

from app.modules.analytics.service import analytics_service
from app.modules.auth.dependencies import require_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/wardrobe")
async def wardrobe_analytics(
    # Date.getTimezoneOffset() from the browser, so "today" is the viewer's day.
    tz_offset_minutes: int = Query(default=0, ge=-14 * 60, le=14 * 60),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    return await analytics_service.get_user_wardrobe_analytics(user_id, tz_offset_minutes)
