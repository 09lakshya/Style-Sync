import io
import logging
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.media.schemas import ImageValidationResult

logger = logging.getLogger("stylesync.media.validator")


def validate_image_bytes(content: bytes, content_type: str | None = None) -> ImageValidationResult:
    """
    Perform deep validation on raw image bytes:
    1. Size constraint check (rejects oversized payloads)
    2. MIME type validation
    3. Magic byte & Pillow parser integrity check (rejects corrupted/executable payloads)
    4. Dimension sanity checks (within configured bounds)
    """
    # 1. Size constraint check
    size_bytes = len(content)
    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file provided.",
        )

    if size_bytes > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image size exceeds the maximum allowed limit of {max_mb} MB.",
        )

    # 2. Inspect with Pillow
    try:
        # First verify data integrity
        stream = io.BytesIO(content)
        with Image.open(stream) as img:
            img.verify()
            img_format = (img.format or "").lower()

        # Reopen for metadata inspection since verify() closes image state
        stream.seek(0)
        with Image.open(stream) as img:
            width, height = img.size

    except (UnidentifiedImageError, ValueError, SyntaxError) as exc:
        logger.warning("Uploaded file failed image verification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file is not a valid or supported image.",
        )
    except Exception as exc:
        logger.warning("Corrupted image stream encountered: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted image file could not be processed.",
        )

    # Normalize format
    if img_format == "jpeg":
        img_format = "jpg"

    allowed_formats = {"jpg", "jpeg", "png", "webp"}
    if img_format not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image format: '{img_format}'. Only JPG, PNG, and WebP are supported.",
        )

    # 3. Dimension constraints
    if width < 10 or height < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image dimensions ({width}x{height}) are too small. Minimum resolution is 10x10.",
        )

    if width > settings.max_image_dimension or height > settings.max_image_dimension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image dimensions ({width}x{height}) exceed maximum allowed dimension of {settings.max_image_dimension}px.",
        )

    resolved_mime = f"image/{'jpeg' if img_format == 'jpg' else img_format}"
    return ImageValidationResult(
        content_type=resolved_mime,
        format=img_format,
        width=width,
        height=height,
        bytes_count=size_bytes,
    )
