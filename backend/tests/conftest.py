import os
import pytest
from app.core.config import settings

# Override database URL for tests to prevent modifying the development stylesync.db
settings.database_url = "sqlite+aiosqlite:///./test_stylesync.db"
