from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_maker, serialize_model
from app.core.models import User


class UserRepository:
    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        """Find a user by lowercased email address."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = select(User).where(User.email == email.lower().strip())
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return serialize_model(user)

    async def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Find a user by string id."""
        maker = get_session_maker()
        async with maker() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return serialize_model(user)

    async def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        password_salt: str = "",
        preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert a new user document and return serialized record."""
        maker = get_session_maker()
        async with maker() as session:
            user = User(
                name=name.strip(),
                email=email.lower().strip(),
                password_hash=password_hash,
                password_salt=password_salt,
                preferences=preferences or {
                    "preferred_colors": [],
                    "style_tags": [],
                    "notification_enabled": True,
                },
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return serialize_model(user)

    async def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update fields on a user document."""
        maker = get_session_maker()
        async with maker() as session:
            if "updated_at" not in updates:
                updates["updated_at"] = datetime.now(timezone.utc)
                
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(**updates)
                .execution_options(synchronize_session="fetch")
            )
            await session.execute(stmt)
            await session.commit()
            
            # Fetch the updated user
            select_stmt = select(User).where(User.id == user_id)
            result = await session.execute(select_stmt)
            updated_user = result.scalar_one_or_none()
            return serialize_model(updated_user)


user_repository = UserRepository()
