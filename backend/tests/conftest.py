import os
import pytest
from app.core.config import settings

# Override database URL for tests to prevent modifying the development stylesync.db
settings.database_url = "sqlite+aiosqlite:///./test_stylesync.db"
# Clear Gemini API key by default in unit tests so test suite runs offline and lightning fast
settings.gemini_api_key = ""
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("GOOGLE_API_KEY", None)
