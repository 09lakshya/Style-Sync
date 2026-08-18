from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_maker, serialize_model
from app.core.models import WardrobeItem


import asyncio

_seed_lock = asyncio.Lock()


class WardrobeRepository:
    async def list_items(self, user_id: str, item_type: str | None = None) -> list[dict[str, Any]]:
        """List wardrobe items for a user, optionally filtered by clothing type, eliminating duplicate items."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = select(WardrobeItem).where(WardrobeItem.user_id == user_id)
            if item_type and item_type.lower() != "all":
                stmt = stmt.where(WardrobeItem.type == item_type.lower())
            stmt = stmt.order_by(WardrobeItem.created_at.desc())
            
            result = await session.execute(stmt)
            items = result.scalars().all()
            
            seen_ids = set()
            unique_items = []
            for item in items:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    unique_items.append(serialize_model(item))
            return unique_items

    async def get_item_by_id(self, item_id: str, user_id: str) -> dict[str, Any] | None:
        """Find a specific wardrobe item belonging to a user."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = select(WardrobeItem).where(WardrobeItem.id == item_id, WardrobeItem.user_id == user_id)
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()
            return serialize_model(item)

    async def create_item(self, item_data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new wardrobe item document."""
        maker = get_session_maker()
        async with maker() as session:
            # Pop unsupported fields or map them
            if "_id" in item_data:
                del item_data["_id"]
                
            item = WardrobeItem(**item_data)
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return serialize_model(item)

    async def update_item(self, item_id: str, user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update fields on a wardrobe item document."""
        maker = get_session_maker()
        async with maker() as session:
            if "updated_at" not in updates:
                updates["updated_at"] = datetime.now(timezone.utc)
                
            stmt = (
                update(WardrobeItem)
                .where(WardrobeItem.id == item_id, WardrobeItem.user_id == user_id)
                .values(**updates)
                .execution_options(synchronize_session="fetch")
            )
            await session.execute(stmt)
            await session.commit()
            
            stmt = select(WardrobeItem).where(WardrobeItem.id == item_id, WardrobeItem.user_id == user_id)
            result = await session.execute(stmt)
            updated_item = result.scalar_one_or_none()
            return serialize_model(updated_item)

    async def delete_item(self, item_id: str, user_id: str) -> bool:
        """Delete a wardrobe item by ID and user ID."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = delete(WardrobeItem).where(WardrobeItem.id == item_id, WardrobeItem.user_id == user_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def increment_wear_count(self, item_id: str, user_id: str) -> dict[str, Any] | None:
        """Increment the wear count of an item and record last worn timestamp."""
        maker = get_session_maker()
        now = datetime.now(timezone.utc)
        async with maker() as session:
            stmt = select(WardrobeItem).where(WardrobeItem.id == item_id, WardrobeItem.user_id == user_id)
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()
            
            if not item:
                return None
                
            item.wear_count += 1
            item.last_worn_at = now
            item.updated_at = now
            
            await session.commit()
            await session.refresh(item)
            return serialize_model(item)

    async def seed_initial_demo_items_if_empty(self, user_id: str) -> None:
        """No-op: allow users to maintain an empty digital wardrobe when all items are cleared."""
        pass



wardrobe_repository = WardrobeRepository()
