import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.database import db_manager
from app.main import app
from app.modules.ai.repository import embedding_repository
from app.modules.auth.repository import user_repository
from app.modules.auth.service import authenticate_user, create_access_token, register_user, verify_access_token
from app.modules.shopping.repository import shopping_repository
from app.modules.shopping.service import shopping_service
from app.modules.wardrobe.repository import wardrobe_repository
from app.modules.wardrobe.service import wardrobe_service


@pytest_asyncio.fixture(autouse=True)
async def mock_db():
    """Setup in-memory mock MongoDB database for isolated testing."""
    mock_client = AsyncMongoMockClient()
    mock_database = mock_client["stylesync_test"]
    db_manager.client = mock_client
    db_manager.db = mock_database
    yield mock_database
    mock_client.close()


@pytest.mark.asyncio
async def test_auth_registration_and_login():
    """Verify user registration, bcrypt hashing, and authentication."""
    # 1. Register a new user
    user = await register_user("Test User", "test@stylesync.dev", "SecurePassword123!")
    assert user is not None
    assert user["name"] == "Test User"
    assert user["email"] == "test@stylesync.dev"
    assert "id" in user
    assert "password_hash" not in user or user["password_hash"] != "SecurePassword123!"

    # 2. Duplicate registration should raise 409
    with pytest.raises(Exception) as exc_info:
        await register_user("Duplicate User", "test@stylesync.dev", "AnotherPassword123!")
    assert "409" in str(exc_info.value) or "Email already registered" in str(exc_info.value)

    # 3. Authenticate with valid password
    authenticated = await authenticate_user("test@stylesync.dev", "SecurePassword123!")
    assert authenticated is not None
    assert authenticated["id"] == user["id"]

    # 4. Authenticate with invalid password
    invalid_auth = await authenticate_user("test@stylesync.dev", "WrongPassword!")
    assert invalid_auth is None


@pytest.mark.asyncio
async def test_jwt_token_lifecycle():
    """Verify JWT token generation and verification."""
    user_id = "usr-test-12345"
    token = create_access_token(user_id)
    assert token is not None

    payload = verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "access"

    # Invalid token verification
    assert verify_access_token("invalid.jwt.token") is None


@pytest.mark.asyncio
async def test_wardrobe_persistence_and_embeddings():
    """Verify wardrobe items and item embeddings are saved to MongoDB."""
    user_id = "usr-test-wardrobe"

    # Create item
    item = await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        filename="blue_floral_summer_dress.jpg",
        name="Blue Floral Summer Dress",
        image_url="https://images.example.com/dress.jpg",
    )
    assert item is not None
    assert item["name"] == "Blue Floral Summer Dress"
    assert item["primary_color"] == "blue"
    assert item["type"] == "dress"
    assert item["pattern"] == "floral"

    # Verify item is in wardrobe_items collection
    items = await wardrobe_service.get_user_items(user_id)
    assert len(items) >= 1
    found = next((i for i in items if i["id"] == item["id"]), None)
    assert found is not None

    # Verify vector embedding was stored in item_embeddings collection
    embedding_doc = await embedding_repository.get_by_item_id(item["id"])
    assert embedding_doc is not None
    assert embedding_doc["user_id"] == user_id
    assert len(embedding_doc["embedding"]) in (64, 512)


@pytest.mark.asyncio
async def test_shopping_duplicate_check_and_audit():
    """Verify duplicate check logic and audit logging in shopping_checks collection."""
    user_id = "usr-test-shopping"

    # Add an item to user's wardrobe
    await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        filename="blue_floral_dress.jpg",
        name="Blue Floral Dress",
        image_url="https://images.example.com/blue_dress.jpg",
    )

    # Perform duplicate check with similar image filename
    result = await shopping_service.check_duplicate_purchase(
        user_id=user_id,
        filename="blue_floral_dress.jpg",
    )
    assert result is not None
    assert "decision" in result
    assert "highest_similarity" in result
    assert len(result["similar_items"]) > 0

    # Verify audit log was recorded in shopping_checks
    history = await shopping_repository.get_user_history(user_id)
    assert len(history) >= 1
    assert history[0]["decision"] == result["decision"]


@pytest.mark.asyncio
async def test_api_endpoints_via_fastapi_client():
    """Verify end-to-end REST API calls with JWT authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register
        reg_response = await client.post(
            "/api/v1/auth/register",
            json={"name": "API Tester", "email": "tester@stylesync.dev", "password": "SecurePassword123!"},
        )
        assert reg_response.status_code == 201
        reg_data = reg_response.json()
        token = reg_data["access_token"]
        assert token is not None

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Wardrobe Items
        wardrobe_res = await client.get("/api/v1/wardrobe/items", headers=headers)
        assert wardrobe_res.status_code == 200
        wardrobe_data = wardrobe_res.json()
        assert "items" in wardrobe_data

        # 3. Get Recommendations
        rec_res = await client.get("/api/v1/recommendations/outfits", headers=headers)
        assert rec_res.status_code == 200
        rec_data = rec_res.json()
        assert "recommendations" in rec_data

        # 4. Get Analytics
        ana_res = await client.get("/api/v1/analytics/wardrobe", headers=headers)
        assert ana_res.status_code == 200
        ana_data = ana_res.json()
        assert "total_items" in ana_data
        assert "category_distribution" in ana_data
