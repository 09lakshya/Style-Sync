from datetime import datetime, timezone
from pydantic import BaseModel, Field


class MediaUploadResult(BaseModel):
    """Normalized DTO representing the result of a cloud media upload."""

    public_id: str
    image_url: str
    thumbnail_url: str
    medium_url: str
    format: str
    width: int
    height: int
    bytes: int
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ImageValidationResult(BaseModel):
    """Result of image integrity and dimension validation."""

    content_type: str
    format: str
    width: int
    height: int
    bytes_count: int
