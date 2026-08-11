from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import require_user
from app.modules.recommendations.service import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/outfits")
async def recommend_outfits(
    occasion: str | None = None,
    season: str | None = None,
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    return await recommendation_service.get_outfit_recommendations(
        user_id=user_id,
        occasion=occasion,
        season=season,
    )
