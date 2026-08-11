from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_maker, serialize_model
from app.core.models import Embedding


class EmbeddingRepository:
    async def save_embedding(
        self,
        item_id: str,
        user_id: str,
        embedding: list[float],
        model_name: str = "clip-vit-base-patch32",
    ) -> dict[str, Any]:
        """Save or update vector embedding for a wardrobe item."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = select(Embedding).where(Embedding.item_id == item_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.embedding = embedding
                existing.embedding_dim = len(embedding)
                existing.model_name = model_name
                await session.commit()
                await session.refresh(existing)
                return serialize_model(existing)
            else:
                new_embedding = Embedding(
                    item_id=item_id,
                    user_id=user_id,
                    model_name=model_name,
                    embedding=embedding,
                    embedding_dim=len(embedding),
                )
                session.add(new_embedding)
                await session.commit()
                await session.refresh(new_embedding)
                return serialize_model(new_embedding)

    async def get_by_item_id(self, item_id: str) -> dict[str, Any] | None:
        """Retrieve embedding record by item_id."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = select(Embedding).where(Embedding.item_id == item_id)
            result = await session.execute(stmt)
            emb = result.scalar_one_or_none()
            return serialize_model(emb)

    async def get_by_user_id(self, user_id: str) -> list[dict[str, Any]]:
        """Retrieve all embedding records for a given user."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = select(Embedding).where(Embedding.user_id == user_id).limit(1000)
            result = await session.execute(stmt)
            embs = result.scalars().all()
            return [serialize_model(emb) for emb in embs]

    async def get_all_embeddings(self) -> list[dict[str, Any]]:
        """Retrieve all embedding records across the platform for index rebuilding."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = select(Embedding).limit(10000)
            result = await session.execute(stmt)
            embs = result.scalars().all()
            return [serialize_model(emb) for emb in embs]

    async def delete_by_item_id(self, item_id: str) -> bool:
        """Delete embedding record when item is deleted."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = delete(Embedding).where(Embedding.item_id == item_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0


embedding_repository = EmbeddingRepository()
