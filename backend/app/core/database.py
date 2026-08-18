import logging
from typing import AsyncGenerator, Any

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.models import Base

logger = logging.getLogger("stylesync.database")

class DatabaseManager:
    engine = None
    session_maker = None

db_manager = DatabaseManager()

async def _migrate_sqlite_columns(conn) -> None:
    """Ensure all columns defined in SQLAlchemy models exist in SQLite tables."""
    for table_name, table in Base.metadata.tables.items():
        res = await conn.exec_driver_sql(f"PRAGMA table_info('{table_name}')")
        existing_cols = {row[1] for row in res.fetchall()}
        if not existing_cols:
            continue
        for col in table.columns:
            if col.name not in existing_cols:
                col_type = "TEXT"
                type_str = str(col.type).upper()
                if "INT" in type_str:
                    col_type = "INTEGER"
                elif "FLOAT" in type_str or "NUMERIC" in type_str or "REAL" in type_str:
                    col_type = "FLOAT"
                elif "JSON" in type_str:
                    col_type = "JSON"
                logger.info("Auto-migrating SQLite table '%s': adding column '%s' (%s)", table_name, col.name, col_type)
                await conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}")

async def connect_db() -> None:
    """Initialize SQLAlchemy AsyncEngine and create tables."""
    try:
        # Create AsyncEngine
        db_manager.engine = create_async_engine(
            settings.database_url,
            echo=False,
        )
        
        # Create session factory
        db_manager.session_maker = async_sessionmaker(
            bind=db_manager.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Initialize tables & auto-migrate missing columns
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _migrate_sqlite_columns(conn)
            
        logger.info("Successfully connected to SQL database and initialized tables.")
    except Exception as exc:
        logger.warning(
            "Could not connect to SQL database (%s). Application will run in connected-or-degraded mode: %s",
            settings.database_url,
            exc,
        )

async def close_db() -> None:
    """Close the SQLAlchemy engine connection."""
    if db_manager.engine is not None:
        await db_manager.engine.dispose()
        logger.info("SQL database connection closed.")

def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the session maker factory."""
    if db_manager.session_maker is None:
        db_manager.engine = create_async_engine(
            settings.database_url,
            echo=False,
        )
        db_manager.session_maker = async_sessionmaker(
            bind=db_manager.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return db_manager.session_maker

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting an async session."""
    maker = get_session_maker()
    async with maker() as session:
        yield session

def serialize_model(model: Any) -> dict[str, Any] | None:
    """Convert SQLAlchemy model to a clean dictionary."""
    if model is None:
        return None
    
    if isinstance(model, dict):
        return model

    result = {}
    for column in model.__table__.columns:
        val = getattr(model, column.name)
        if hasattr(val, "isoformat"):
            result[column.name] = val.isoformat()
        else:
            result[column.name] = val
            
    return result
