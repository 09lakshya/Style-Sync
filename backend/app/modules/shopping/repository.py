from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_maker, serialize_model
from app.core.models import ShoppingCheck


class ShoppingRepository:
    async def log_check(
        self,
        user_id: str,
        query_image_url: str,
        similar_items: list[dict[str, Any]],
        decision: str,
        highest_similarity: float,
    ) -> dict[str, Any]:
        """Record duplicate shopping check audit log."""
        maker = get_session_maker()
        async with maker() as session:
            check = ShoppingCheck(
                user_id=user_id,
                query_image_url=query_image_url,
                similar_items=similar_items,
                decision=decision,
                highest_similarity=highest_similarity,
            )
            session.add(check)
            await session.commit()
            await session.refresh(check)
            return serialize_model(check)

    async def get_user_history(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent shopping duplicate checks for user."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = (
                select(ShoppingCheck)
                .where(ShoppingCheck.user_id == user_id)
                .order_by(ShoppingCheck.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            checks = result.scalars().all()
            return [serialize_model(check) for check in checks]


shopping_repository = ShoppingRepository()
