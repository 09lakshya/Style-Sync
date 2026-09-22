from fastapi import APIRouter, Depends, Query

from app.modules.auth.dependencies import require_user
from app.modules.outfits.service import outfit_service

router = APIRouter(prefix="/outfits", tags=["outfits"])


@router.get("")
async def outfit_suggestions(
    occasion: str | None = Query(None, description="Filter to one occasion, e.g. work."),
    season: str | None = Query(None, description="Filter to one season, e.g. winter."),
    style: str | None = Query(None, description="Filter to western, fusion or traditional."),
    sort: str = Query("score", pattern="^(score|fresh)$"),
    limit: int = Query(12, ge=1, le=50),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Outfits built from this user's own wardrobe, with the reasoning shown."""
    return await outfit_service.suggest(
        user_id=user_id,
        occasion=occasion,
        season=season,
        style=style,
        sort=sort,
        limit=limit,
    )
