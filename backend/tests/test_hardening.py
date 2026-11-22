import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import connect_db, db_manager
from app.core.models import Base
from app.main import app
from app.modules.ai.gemini_service import gemini_service
from app.modules.auth.rate_limit import LoginRateLimiter, login_rate_limiter


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await connect_db()
    if db_manager.engine is not None:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    login_rate_limiter._failures.clear()
    gemini_service._paused_until = 0.0
    yield
    gemini_service._paused_until = 0.0


# --- Gemini quota --------------------------------------------------------

def _response(status: int, headers: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.headers = headers or {}
    return response


def test_a_429_stops_at_the_first_model_and_pauses_gemini(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = _response(429, {"retry-after": "30"})
        assert asyncio.run(gemini_service.detect_clothing_item(b"img")) is None
        assert post.call_count == 1, "the other models share the quota; trying them only adds wait"
        assert gemini_service.is_paused

        # While paused, callers fall back without a network call at all.
        assert asyncio.run(gemini_service.detect_clothing_item(b"img")) is None
        assert post.call_count == 1


def test_the_api_key_goes_in_a_header_not_the_url(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "secret-key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as post:
        post.return_value = _response(503)
        asyncio.run(gemini_service.detect_clothing_item(b"img"))
        url = post.call_args.args[0]
        assert "secret-key" not in url
        assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "secret-key"


# --- login rate limit ----------------------------------------------------

def test_the_limiter_blocks_after_repeated_failures_and_recovers():
    limiter = LoginRateLimiter(max_failures=3, window_seconds=100)
    for t in range(3):
        assert limiter.retry_after("A@x.com", "1.2.3.4", now=t) == 0
        limiter.record_failure("a@x.com", "1.2.3.4", now=t)
    assert limiter.retry_after("a@x.com", "1.2.3.4", now=3) > 0
    assert limiter.retry_after("a@x.com", "9.9.9.9", now=3) == 0, "another address is not blocked"
    assert limiter.retry_after("a@x.com", "1.2.3.4", now=101) == 0, "the oldest failure has aged out"


@pytest.mark.asyncio
async def test_login_answers_429_with_retry_after_after_five_failures():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver/api/v1") as client:
        await client.post("/auth/register", json={"name": "Guess", "email": "g@example.com", "password": "Password123!"})
        for _ in range(5):
            bad = await client.post("/auth/login", json={"email": "g@example.com", "password": "wrong-pass"})
            assert bad.status_code == 401
        blocked = await client.post("/auth/login", json={"email": "g@example.com", "password": "Password123!"})
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) > 0


# --- error responses ------------------------------------------------------

@pytest.mark.asyncio
async def test_error_responses_only_allow_the_apps_own_origins():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver/api/v1") as client:
        evil = await client.get("/wardrobe/items", headers={"Origin": "https://evil.example"})
        assert evil.status_code == 401
        assert "access-control-allow-origin" not in evil.headers

        local = await client.get("/wardrobe/items", headers={"Origin": "http://localhost:5173"})
        assert local.headers.get("access-control-allow-origin") == "http://localhost:5173"
