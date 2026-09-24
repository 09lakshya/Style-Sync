from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Dict, Any
from PIL import Image
import io

from app.modules.ai.classifier_manager import classifier_manager

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/classify")
async def classify_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Endpoint to manually classify an image.

    Returns all three axes -- occasion, season, tradition -- because the model
    answers them independently. `predicted_category` is the single strongest
    label, kept so existing callers keep working, but it necessarily discards
    the other two answers.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read image: {e}")

    if not classifier_manager.is_loaded:
        raise HTTPException(status_code=503, detail="Classification model is not loaded or unavailable.")

    axes = classifier_manager.predict_axes(image)
    if axes is None:
        raise HTTPException(status_code=500, detail="Prediction failed.")

    predicted_category, confidence = classifier_manager.single_label(axes["probabilities"])

    return {
        # A garment that clears no threshold on any axis is a real outcome, not
        # an error: predicted_category is null and the axes below say why.
        "predicted_category": predicted_category,
        "prediction_confidence": confidence,
        "occasion": axes["occasion"],
        "season": axes["season"],
        "tradition": axes["tradition"],
        "probabilities": axes["probabilities"],
        "thresholds": axes["thresholds"],
        "model_version": classifier_manager.model_version,
    }
