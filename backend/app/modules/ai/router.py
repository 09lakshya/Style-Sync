from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Dict, Any
from PIL import Image
import io

from app.modules.ai.classifier_manager import classifier_manager

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/classify")
async def classify_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Endpoint to manually classify an image and return predicted category and confidence.
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

    predicted_category, confidence = classifier_manager.predict(image)

    if predicted_category is None:
        raise HTTPException(status_code=500, detail="Prediction failed.")

    return {
        "predicted_category": predicted_category,
        "prediction_confidence": confidence,
        "model_version": classifier_manager.model_version
    }
