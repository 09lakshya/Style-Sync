import logging
from typing import Any
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.ai.repository import embedding_repository
from app.modules.ai.service import ai_service, generate_embedding, infer_metadata
from app.modules.media.cloudinary_service import cloudinary_service
from app.modules.wardrobe.repository import wardrobe_repository

logger = logging.getLogger("stylesync.wardrobe.service")


from datetime import datetime, date, timezone

def _parse_datetime(val: Any) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(val, str) and val.strip():
        try:
            val_str = val.strip().replace("Z", "+00:00")
            if "T" in val_str:
                return datetime.fromisoformat(val_str)
            d = date.fromisoformat(val_str)
            return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
        except Exception:
            return None
    return None


class WardrobeService:
    async def get_user_items(self, user_id: str, item_type: str | None = None) -> list[dict[str, Any]]:
        """Retrieve user wardrobe items, ensuring initial demo items exist for new accounts."""
        await wardrobe_repository.seed_initial_demo_items_if_empty(user_id)
        return await wardrobe_repository.list_items(user_id, item_type)

    async def get_item_by_id(self, item_id: str, user_id: str) -> dict[str, Any]:
        """Fetch a single wardrobe item by ID, verifying ownership."""
        item = await wardrobe_repository.get_item_by_id(item_id, user_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wardrobe item '{item_id}' not found.",
            )
        return item

    async def create_item_from_upload(
        self,
        user_id: str,
        filename: str = "wardrobe-item.jpg",
        file_bytes: bytes | None = None,
        name: str | None = None,
        color: str | None = None,
        pattern: str | None = None,
        brand: str | None = None,
        purchase_date: str | datetime | None = None,
        occasion: str | list[str] | None = None,
        last_worn_date: str | datetime | None = None,
        image_url: str = "",
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Process wardrobe photo upload:
        1. If file_bytes provided: validate, optimize, and upload to Cloudinary
        2. If file_bytes not provided: use provided image_url or fallback
        3. Infer apparel metadata
        4. Save item record with Cloudinary URLs & dimensions in database
        5. Generate and persist vector embedding
        """
        if file_bytes is not None:
            media = await cloudinary_service.upload_image(
                file_bytes=file_bytes,
                user_id=user_id,
                content_type=content_type,
            )
            resolved_image_url = media.image_url
            resolved_thumbnail_url = media.thumbnail_url
            resolved_medium_url = media.medium_url
            resolved_public_id = media.public_id
            resolved_format = media.format
            resolved_width = media.width
            resolved_height = media.height
            resolved_bytes = media.bytes
        else:
            resolved_image_url = image_url or "https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=800&q=80"
            resolved_thumbnail_url = resolved_image_url
            resolved_medium_url = resolved_image_url
            resolved_public_id = cloudinary_service.build_public_id(user_id=user_id)
            resolved_format = "jpg"
            resolved_width = 800
            resolved_height = 800
            resolved_bytes = 0

        # 2. Extract metadata using AI (OpenCV + CLIP) or rule-based fallback
        if file_bytes is not None:
            metadata = ai_service.extract_clothing_metadata(file_bytes=file_bytes, filename=filename)
        else:
            metadata = infer_metadata(filename)

        item_name = name.strip() if name and name.strip() else filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        primary_color = color.strip() if color and color.strip() else metadata["primary_color"]
        item_pattern = pattern.strip() if pattern and pattern.strip() else metadata["pattern"]
        item_brand = brand.strip() if brand and brand.strip() else None
        item_purchase_date = _parse_datetime(purchase_date)
        item_last_worn_at = _parse_datetime(last_worn_date)

        if occasion:
            if isinstance(occasion, str):
                item_occasion = [occasion.strip()] if occasion.strip() else metadata["occasion"]
            elif isinstance(occasion, list):
                item_occasion = [o.strip() for o in occasion if o and o.strip()]
            else:
                item_occasion = metadata["occasion"]
        else:
            item_occasion = metadata["occasion"]

        # 3. Create record in database (includes embedding_id reference)
        item_doc = {
            "user_id": user_id,
            "name": item_name,
            "image_url": resolved_image_url,
            "thumbnail_url": resolved_thumbnail_url,
            "medium_url": resolved_medium_url,
            "public_id": resolved_public_id,
            "format": resolved_format,
            "width": resolved_width,
            "height": resolved_height,
            "bytes": resolved_bytes,
            "type": metadata.get("type", "dress"),
            "category": metadata.get("category", "dresses"),
            "primary_color": primary_color,
            "secondary_colors": metadata.get("secondary_colors", []),
            "pattern": item_pattern,
            "sleeve_type": metadata.get("sleeve_type", "short_sleeve"),
            "fabric": metadata.get("fabric", "user_review_needed"),
            "season": metadata.get("season", ["all_season"]),
            "occasion": item_occasion,
            "tags": metadata.get("tags", [item_pattern, primary_color]),
            "confidence": metadata.get("confidence", {}),
            "brand": item_brand,
            "purchase_date": item_purchase_date,
            "wear_count": 0,
            "last_worn_at": item_last_worn_at,
            "embedding_id": None,
        }

        try:
            created_item = await wardrobe_repository.create_item(item_doc)
            item_id = str(created_item["id"])

            # 4. Generate and save vector embedding in item_embeddings collection
            if file_bytes is not None:
                embedding = ai_service.generate_image_embedding(file_bytes)
            else:
                embedding = ai_service.generate_text_embedding(f"{filename}:{item_name}")

            embedding_record = await embedding_repository.save_embedding(
                item_id=item_id,
                user_id=user_id,
                embedding=embedding,
                model_name=settings.clip_model_name,
            )

            # Update item with embedding_id reference
            if embedding_record and "id" in embedding_record:
                await wardrobe_repository.update_item(item_id, user_id, {"embedding_id": embedding_record["id"]})
                created_item["embedding_id"] = embedding_record["id"]

            logger.info("Created wardrobe item id=%s for user_id=%s with public_id=%s", item_id, user_id, resolved_public_id)
            return created_item
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Failed to persist wardrobe item for user_id=%s: %s", user_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database or storage error while saving wardrobe item: {str(exc)}",
            )

    async def update_wardrobe_item_metadata(
        self,
        user_id: str,
        item_id: str,
        name: str | None = None,
        color: str | None = None,
        pattern: str | None = None,
        brand: str | None = None,
        purchase_date: str | datetime | None = None,
        occasion: str | list[str] | None = None,
        last_worn_date: str | datetime | None = None,
    ) -> dict[str, Any]:
        """Update metadata of an existing wardrobe item after verifying ownership."""
        await self.get_item_by_id(item_id, user_id)
        updates: dict[str, Any] = {}
        if name is not None and name.strip():
            updates["name"] = name.strip()
        if color is not None and color.strip():
            updates["primary_color"] = color.strip()
        if pattern is not None and pattern.strip():
            updates["pattern"] = pattern.strip()
        if brand is not None:
            updates["brand"] = brand.strip() if brand.strip() else None
        if purchase_date is not None:
            updates["purchase_date"] = _parse_datetime(purchase_date)
        if occasion is not None:
            if isinstance(occasion, str):
                updates["occasion"] = [occasion.strip()] if occasion.strip() else []
            elif isinstance(occasion, list):
                updates["occasion"] = [o.strip() for o in occasion if o and o.strip()]
        if last_worn_date is not None:
            updates["last_worn_at"] = _parse_datetime(last_worn_date)

        updated_item = await wardrobe_repository.update_item(item_id, user_id, updates)
        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wardrobe item '{item_id}' could not be updated.",
            )
        return updated_item

    async def replace_item_image(
        self,
        user_id: str,
        item_id: str,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Replace wardrobe item photo:
        1. Verify item ownership
        2. Upload new image and safely destroy previous Cloudinary asset
        3. Re-extract AI metadata and re-generate vector embedding
        4. Update database record with new image references and metadata
        """
        item = await self.get_item_by_id(item_id, user_id)
        old_public_id = item.get("public_id")

        # Upload new image and replace old asset
        media = await cloudinary_service.replace_image(
            old_public_id=old_public_id,
            file_bytes=file_bytes,
            user_id=user_id,
            item_id=item_id,
            content_type=content_type,
        )

        # Re-extract AI metadata
        metadata = ai_service.extract_clothing_metadata(file_bytes=file_bytes, filename=filename)

        updates = {
            "image_url": media.image_url,
            "thumbnail_url": media.thumbnail_url,
            "medium_url": media.medium_url,
            "public_id": media.public_id,
            "format": media.format,
            "width": media.width,
            "height": media.height,
            "bytes": media.bytes,
            "type": metadata["type"],
            "category": metadata["category"],
            "primary_color": item.get("primary_color") or metadata["primary_color"],
            "secondary_colors": metadata.get("secondary_colors", []),
            "pattern": item.get("pattern") or metadata["pattern"],
            "sleeve_type": metadata.get("sleeve_type", "short_sleeve"),
            "season": metadata["season"],
            "occasion": item.get("occasion") or metadata["occasion"],
            "confidence": metadata.get("confidence", {}),
        }

        updated_item = await wardrobe_repository.update_item(item_id, user_id, updates)
        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wardrobe item '{item_id}' could not be updated.",
            )

        # Re-compute and update embedding
        embedding = ai_service.generate_image_embedding(file_bytes)
        embedding_record = await embedding_repository.save_embedding(
            item_id=item_id,
            user_id=user_id,
            embedding=embedding,
            model_name=settings.clip_model_name,
        )
        if embedding_record and "id" in embedding_record:
            await wardrobe_repository.update_item(item_id, user_id, {"embedding_id": embedding_record["id"]})
            updated_item["embedding_id"] = embedding_record["id"]

        logger.info("Replaced image for wardrobe item id=%s (new public_id=%s)", item_id, media.public_id)
        return updated_item

    async def delete_wardrobe_item(self, user_id: str, item_id: str) -> bool:
        """
        Delete wardrobe item:
        1. Verify ownership
        2. Delete Cloudinary image asset
        3. Delete database item record and embedding record
        """
        item = await self.get_item_by_id(item_id, user_id)

        public_id = item.get("public_id")
        if public_id:
            try:
                await cloudinary_service.delete_image(public_id)
            except Exception as exc:
                logger.warning("Could not delete Cloudinary asset '%s' during item deletion: %s", public_id, exc)

        await embedding_repository.delete_by_item_id(item_id)
        deleted = await wardrobe_repository.delete_item(item_id, user_id)
        logger.info("Deleted wardrobe item id=%s for user_id=%s (result=%s)", item_id, user_id, deleted)
        return deleted

    async def record_item_worn(self, item_id: str, user_id: str) -> dict[str, Any]:
        """Mark an item as worn and increment its wear counter."""
        updated = await wardrobe_repository.increment_wear_count(item_id, user_id)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wardrobe item '{item_id}' not found.",
            )
        return updated


wardrobe_service = WardrobeService()

