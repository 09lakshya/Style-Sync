from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.modules.auth.dependencies import require_user
from app.modules.media.validator import validate_image_bytes
from app.modules.recommendations.service import outfit_analysis_service, recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/analyze-outfit")
async def analyze_outfit(
    image: UploadFile = File(...),
    gender: str | None = Form(None),
    user_id: str = Depends(require_user),
) -> dict[str, object]:
    """Analyse one uploaded outfit image and return attributes plus styling advice.

    Gender is detected from the image; pass it only to override the detection.
    """
    file_bytes = await image.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image upload.")

    validate_image_bytes(file_bytes, image.content_type or "image/jpeg")

    return await outfit_analysis_service.analyze(
        file_bytes=file_bytes,
        filename=image.filename or "outfit.jpg",
        gender=gender,
    )


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
