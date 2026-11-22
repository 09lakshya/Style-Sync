import logging
from typing import Any
from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.ai.repository import embedding_repository
from app.modules.ai.service import (
    ai_service,
    generate_embedding,
    infer_metadata,
)
from app.modules.media.cloudinary_service import cloudinary_service
from app.modules.wardrobe import normalise as norm
from app.modules.wardrobe.repository import wardrobe_repository

logger = logging.getLogger("stylesync.wardrobe.service")


from datetime import datetime, date, timezone

def _classify(file_bytes: bytes) -> tuple[str | None, float | None, dict[str, Any], str | None]:
    """Run the classifier once and return (category, confidence, axes, version).

    Both the detect-only path and the create path need exactly this, and they had
    drifted into two copies. Keeping one means the axes stored on an item cannot
    disagree with the axes shown in the form that previewed it.

    The stored axes deliberately drop the thresholds and model version that
    predict_axes also returns: the version has its own column, and repeating six
    thresholds on every row would copy a property of the model across thousands
    of items, where it would go stale the moment they are recalibrated.
    """
    try:
        import io as _io

        from PIL import Image

        from app.modules.ai.classifier_manager import classifier_manager

        if not classifier_manager.is_loaded:
            return None, None, {}, None

        pil_image = Image.open(_io.BytesIO(file_bytes))
        # One forward pass for all three axes, then collapse the same
        # probabilities to a single label. Calling predict() as well would
        # classify the photo twice for one upload.
        axes = classifier_manager.predict_axes(pil_image)
        if not axes:
            return None, None, {}, classifier_manager.model_version

        category, confidence = classifier_manager.single_label(axes["probabilities"])
        # A withheld axis is left out rather than stored empty, which would read
        # as the model answering "no season".
        stored = {
            axis: axes[axis] for axis in ("occasion", "season", "tradition") if axis in axes
        }
        stored["probabilities"] = axes["probabilities"]
        return category, confidence, stored, classifier_manager.model_version
    except Exception as exc:
        logger.warning("Classification model error: %s", exc)
        return None, None, {}, None


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


# Fields the add form has no input for. When the form was filled from a
# detection, these come from it instead of a second, less accurate local read
# of the same photo.
_DETECTION_FIELDS = ("season", "fabric", "secondary_colors", "sleeve_type", "occasion", "embellishment", "type")


def _merge_detection(metadata: dict[str, Any], detected: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(detected, dict):
        return metadata
    merged = dict(metadata)
    for field in _DETECTION_FIELDS:
        value = detected.get(field)
        if value not in (None, "", []):
            merged[field] = value
    tags = detected.get("tags")
    if isinstance(tags, list) and tags:
        merged["tags"] = [str(t).lstrip("#") for t in tags if t]
    if detected.get("name"):
        merged["suggested_name"] = str(detected["name"])
    return merged


def _from_gemini(detected: dict[str, Any] | None) -> bool:
    if not isinstance(detected, dict):
        return False
    if detected.get("detected_by") == "gemini":
        return True
    return str(detected.get("model_version") or "").lower().startswith("gemini")


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

    async def detect_item_metadata(
        self, file_bytes: bytes, filename: str = "wardrobe-item.jpg"
    ) -> dict[str, Any]:
        """Run detection on a photo and return the attributes, saving nothing.

        Mirrors what `create_item_from_upload` would store, so whatever the form
        shows is what gets written if the user accepts it unchanged.
        """
        from app.modules.ai.gemini_service import gemini_service

        if gemini_service.is_configured:
            lower = filename.lower()
            mime_type = (
                "image/png"
                if lower.endswith(".png")
                else "image/webp"
                if lower.endswith(".webp")
                else "image/jpeg"
            )
            gemini_result = await gemini_service.detect_clothing_item(
                file_bytes=file_bytes, mime_type=mime_type
            )
            if gemini_result:
                gemini_result["detected_by"] = "gemini"
                gemini_result["backup_reason"] = None
                return gemini_result

        metadata = ai_service.extract_clothing_metadata(file_bytes=file_bytes, filename=filename)

        predicted_category, confidence, predicted_axes, model_version = _classify(file_bytes)

        # Said out loud so the form can warn the user: the local models get the
        # garment wrong far more often than Gemini does.
        if not gemini_service.is_configured:
            backup_reason = "not_configured"
        elif gemini_service.is_paused:
            backup_reason = "quota"
        else:
            backup_reason = "unavailable"

        return {
            "detected_by": "backup",
            "backup_reason": backup_reason,
            "name": metadata.get("suggested_name"),
            "type": metadata.get("type"),
            "type_alternatives": metadata.get("type_alternatives", []),
            "category": metadata.get("category"),
            "is_ethnic": metadata.get("is_ethnic", False),
            "color": metadata.get("primary_color"),
            "secondary_colors": metadata.get("secondary_colors", []),
            "pattern": metadata.get("pattern"),
            "embellishment": metadata.get("embellishment"),
            "sleeve_type": metadata.get("sleeve_type"),
            "fabric": metadata.get("fabric"),
            "season": metadata.get("season", []),
            "occasion": metadata.get("occasion", []),
            "tags": metadata.get("tags", []),
            "confidence": metadata.get("confidence", {}),
            "predicted_category": predicted_category,
            "prediction_confidence": confidence,
            "predicted_axes": predicted_axes,
            "model_version": model_version,
        }

    async def create_item_from_upload(
        self,
        user_id: str,
        filename: str = "wardrobe-item.jpg",
        file_bytes: bytes | None = None,
        name: str | None = None,
        color: str | None = None,
        pattern: str | None = None,
        item_type: str | None = None,
        brand: str | None = None,
        purchase_date: str | datetime | None = None,
        occasion: str | list[str] | None = None,
        last_worn_date: str | datetime | None = None,
        image_url: str = "",
        content_type: str | None = None,
        detected: dict[str, Any] | None = None,
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
        metadata = _merge_detection(metadata, detected)

        # 2.5 Run Custom Classification Model
        pred_cat, pred_conf, pred_axes, mod_ver = (
            _classify(file_bytes) if file_bytes is not None else (None, None, {}, None))
        # When Gemini filled the form, record that it did, rather than the local
        # classifier's weaker reading of the same photo.
        if _from_gemini(detected):
            pred_axes = detected.get("predicted_axes") or pred_axes
            mod_ver = str(detected.get("model_version") or "gemini")
            pred_conf = None

        # A blank name is normal now that detection runs on upload: the detected
        # attributes read better than IMG_2831, so the filename is only a last resort.
        if name and name.strip():
            item_name = name.strip()
        else:
            item_name = (
                metadata.get("suggested_name")
                or filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
            )
        primary_color = norm.normalise_color(color) or norm.normalise_color(metadata["primary_color"])
        item_pattern = norm.normalise_pattern(pattern) or norm.normalise_pattern(metadata["pattern"])
        item_brand = brand.strip() if brand and brand.strip() else None

        # A corrected type has to carry its category with it, or an item the user
        # re-labelled as trousers stays filed under one_piece.
        resolved_type = norm.normalise_type(item_type) or norm.normalise_type(metadata.get("type")) or "dress"
        resolved_category = norm.category_for(resolved_type)
        resolved_tags = norm.tags_for_type(metadata.get("tags", []), metadata.get("type"), resolved_type)
        item_purchase_date = _parse_datetime(purchase_date)
        item_last_worn_at = _parse_datetime(last_worn_date)

        # The form picks one occasion; detection may have found several. Keep the
        # detected ones too when they agree with the user's pick, and lead with it.
        chosen = norm.normalise_occasions(occasion)
        detected_occasions = norm.normalise_occasions(metadata.get("occasion"))
        if chosen and chosen[0] in detected_occasions:
            item_occasion = chosen + [o for o in detected_occasions if o not in chosen]
        else:
            item_occasion = chosen or detected_occasions or ["casual"]

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
            "type": resolved_type,
            "category": resolved_category,
            "primary_color": primary_color,
            "secondary_colors": norm.normalise_colors(metadata.get("secondary_colors", [])),
            "pattern": item_pattern,
            "sleeve_type": norm.normalise_sleeve(metadata.get("sleeve_type")),
            "fabric": norm.normalise_fabric(metadata.get("fabric")) or "user_review_needed",
            "season": norm.normalise_seasons(metadata.get("season")) or ["all_season"],
            "occasion": item_occasion,
            "tags": resolved_tags,
            "confidence": metadata.get("confidence", {}),
            "brand": item_brand,
            "purchase_date": item_purchase_date,
            "wear_count": 0,
            "last_worn_at": item_last_worn_at,
            "embedding_id": None,
            "predicted_category": pred_cat,
            "prediction_confidence": pred_conf,
            "predicted_axes": pred_axes,
            "model_version": mod_ver,
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
                detail="Could not save the wardrobe item. Please try again.",
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
        wear_count: int | None = None,
        item_type: str | None = None,
        season: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """Update metadata of an existing wardrobe item after verifying ownership."""
        item = await self.get_item_by_id(item_id, user_id)
        updates: dict[str, Any] = {}
        if name is not None and name.strip():
            updates["name"] = name.strip()
        if color is not None and color.strip():
            updates["primary_color"] = norm.normalise_color(color)
        if pattern is not None and pattern.strip():
            updates["pattern"] = norm.normalise_pattern(pattern)
        new_type = norm.normalise_type(item_type)
        if new_type and new_type != item.get("type"):
            # Category and the ethnic tag follow the type, or a "gown" corrected
            # to "dress" would keep sorting and pairing as the old garment.
            updates["type"] = new_type
            updates["category"] = norm.category_for(new_type)
            updates["tags"] = norm.tags_for_type(item.get("tags") or [], item.get("type"), new_type)
        if season is not None:
            seasons = norm.normalise_seasons(season)
            if not seasons:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Pick at least one season.",
                )
            updates["season"] = seasons
        if brand is not None:
            updates["brand"] = brand.strip() if brand.strip() else None
        if purchase_date is not None:
            updates["purchase_date"] = _parse_datetime(purchase_date)
        if occasion is not None:
            occasions = norm.normalise_occasions(occasion)
            if not occasions:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Pick at least one occasion.",
                )
            updates["occasion"] = occasions
        if last_worn_date is not None:
            updates["last_worn_at"] = _parse_datetime(last_worn_date)
        if wear_count is not None:
            # A correction of the running total, so it may go down as well as up.
            if wear_count < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="wear_count cannot be negative.",
                )
            updates["wear_count"] = int(wear_count)

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

        # The item's details are kept: a new photo of the same garment should not
        # undo a type, season or occasion the user has corrected. Only the image
        # and its embedding change.
        updates = {
            "image_url": media.image_url,
            "thumbnail_url": media.thumbnail_url,
            "medium_url": media.medium_url,
            "public_id": media.public_id,
            "format": media.format,
            "width": media.width,
            "height": media.height,
            "bytes": media.bytes,
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

