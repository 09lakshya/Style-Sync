import asyncio
import base64
import logging
import uuid
from typing import Any

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.media.schemas import MediaUploadResult
from app.modules.media.validator import validate_image_bytes

logger = logging.getLogger("stylesync.media.cloudinary")


class CloudinaryService:
    def __init__(self) -> None:
        self._is_configured = False
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Cloudinary SDK with environment credentials."""
        if settings.is_cloudinary_configured:
            cloudinary.config(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                secure=True,
            )
            self._is_configured = True
            logger.info("Cloudinary client initialized successfully for cloud: %s", settings.cloudinary_cloud_name)
        else:
            logger.info("Cloudinary credentials not set. Media service running in mock/local fallback mode.")
            self._is_configured = False

    def build_public_id(self, user_id: str, item_id: str | None = None) -> str:
        """Construct predictable and isolated asset path in Cloudinary."""
        asset_id = item_id or uuid.uuid4().hex
        prefix = settings.cloudinary_folder_prefix.strip("/")
        return f"{prefix}/users/{user_id}/wardrobe/{asset_id}"

    def build_optimized_urls(self, public_id: str, format_ext: str = "jpg") -> dict[str, str]:
        """Generate auto-optimized CDN transformation URLs for standard, medium, and thumbnail views."""
        if not self._is_configured:
            base = f"https://res.cloudinary.com/mock-cloud/image/upload"
            return {
                "image_url": f"{base}/q_auto,f_auto/{public_id}.{format_ext}",
                "medium_url": f"{base}/c_limit,w_800,h_800,q_auto,f_auto/{public_id}.{format_ext}",
                "thumbnail_url": f"{base}/c_fill,w_300,h_300,g_auto,q_auto,f_auto/{public_id}.{format_ext}",
            }

        image_url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            secure=True,
            quality="auto",
            fetch_format="auto",
        )
        medium_url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            secure=True,
            width=800,
            height=800,
            crop="limit",
            quality="auto",
            fetch_format="auto",
        )
        thumbnail_url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            secure=True,
            width=300,
            height=300,
            crop="fill",
            gravity="auto",
            quality="auto",
            fetch_format="auto",
        )
        return {
            "image_url": image_url,
            "medium_url": medium_url,
            "thumbnail_url": thumbnail_url,
        }

    async def upload_image(
        self,
        file_bytes: bytes,
        user_id: str,
        item_id: str | None = None,
        content_type: str | None = None,
        retries: int = 2,
    ) -> MediaUploadResult:
        """
        Validate, optimize, and upload image to Cloudinary asynchronously without blocking FastAPI event loop.
        """
        validation = validate_image_bytes(file_bytes, content_type)
        public_id = self.build_public_id(user_id=user_id, item_id=item_id)

        logger.info("Starting image upload for user_id=%s, public_id=%s, size=%d bytes", user_id, public_id, validation.bytes_count)

        if not self._is_configured:
            # Fallback mock for local development and offline test environments
            logger.info("Generating fallback local/mock Cloudinary record for public_id: %s", public_id)
            urls = self.build_optimized_urls(public_id, validation.format)
            # Store base64 data URI in fallback mode so preview works locally even without cloud credentials
            b64_uri = f"data:{validation.content_type};base64,{base64.b64encode(file_bytes).decode('ascii')}"
            return MediaUploadResult(
                public_id=public_id,
                image_url=b64_uri,
                medium_url=b64_uri,
                thumbnail_url=b64_uri,
                format=validation.format,
                width=validation.width,
                height=validation.height,
                bytes=validation.bytes_count,
            )

        # Upload to live Cloudinary with retry loop
        last_exception = None
        for attempt in range(1, retries + 1):
            try:
                def _sync_upload() -> dict[str, Any]:
                    return cloudinary.uploader.upload(
                        file_bytes,
                        public_id=public_id,
                        overwrite=True,
                        resource_type="image",
                        unique_filename=False,
                        use_filename=False,
                    )

                response = await asyncio.to_thread(_sync_upload)
                logger.info("Upload completed successfully for public_id=%s (attempt %d)", public_id, attempt)

                resolved_public_id = response.get("public_id", public_id)
                resolved_format = response.get("format", validation.format)
                urls = self.build_optimized_urls(resolved_public_id, resolved_format)

                return MediaUploadResult(
                    public_id=resolved_public_id,
                    image_url=urls["image_url"],
                    medium_url=urls["medium_url"],
                    thumbnail_url=urls["thumbnail_url"],
                    format=resolved_format,
                    width=response.get("width", validation.width),
                    height=response.get("height", validation.height),
                    bytes=response.get("bytes", validation.bytes_count),
                )
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Cloudinary upload attempt %d/%d failed for public_id=%s: %s",
                    attempt,
                    retries,
                    public_id,
                    exc,
                )
                if attempt < retries:
                    await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        logger.error("Cloudinary upload permanently failed for public_id=%s: %s", public_id, last_exception)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload image to cloud storage. Please try again.",
        )

    async def delete_image(self, public_id: str) -> bool:
        """Delete an asset from Cloudinary by its public_id."""
        if not public_id:
            return False

        logger.info("Starting Cloudinary deletion for public_id=%s", public_id)

        if not self._is_configured:
            logger.info("Mock mode: skipping remote Cloudinary deletion for public_id=%s", public_id)
            return True

        try:
            def _sync_destroy() -> dict[str, Any]:
                return cloudinary.uploader.destroy(public_id, invalidate=True)

            result = await asyncio.to_thread(_sync_destroy)
            res_str = result.get("result", "")
            logger.info("Cloudinary deletion result for public_id=%s: %s", public_id, res_str)
            return res_str in {"ok", "not found"}
        except Exception as exc:
            logger.error("Cloudinary deletion failed for public_id=%s: %s", public_id, exc)
            return False

    async def replace_image(
        self,
        old_public_id: str | None,
        file_bytes: bytes,
        user_id: str,
        item_id: str | None = None,
        content_type: str | None = None,
    ) -> MediaUploadResult:
        """
        Upload new image first; upon success, safely destroy the old image asset.
        """
        new_media = await self.upload_image(
            file_bytes=file_bytes,
            user_id=user_id,
            item_id=item_id,
            content_type=content_type,
        )

        # If previous public_id was different, clean it up asynchronously
        if old_public_id and old_public_id != new_media.public_id:
            try:
                await self.delete_image(old_public_id)
            except Exception as exc:
                logger.warning("Could not delete previous asset %s during replacement: %s", old_public_id, exc)

        return new_media


cloudinary_service = CloudinaryService()
