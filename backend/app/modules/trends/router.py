from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.dependencies import require_user
from app.modules.trends.service import trends_service

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("")
async def trend_feed(
    season: str | None = Query(None, description="Filter by season, e.g. fall, winter."),
    occasion: str | None = Query(None, description="Filter by occasion, e.g. work, party."),
    sort: str = Query("momentum", pattern="^(momentum|match|title)$"),
    limit: int | None = Query(None, ge=1, le=50),
    all_genders: bool = Query(False, description="Ignore the profile gender and show every trend."),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Current-season trends, each scored against what this user already owns.

    Filtered to the trends cut for the gender chosen at sign-up unless
    `all_genders` is set.
    """
    return await trends_service.get_feed(
        user_id=user_id,
        season=season,
        occasion=occasion,
        sort=sort,
        limit=limit,
        include_all_genders=all_genders,
    )


@router.get("/signals")
async def trend_signals(user_id: str = Depends(require_user)) -> dict[str, object]:
    """Trends within the user's own wardrobe: colour rotation, momentum, neglect."""
    return await trends_service.get_signals(user_id)


@router.get("/{trend_id}")
async def trend_detail(trend_id: str, user_id: str = Depends(require_user)) -> dict[str, object]:
    trend = await trends_service.get_trend(user_id, trend_id)
    if not trend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trend '{trend_id}' not found.",
        )
    return trend
