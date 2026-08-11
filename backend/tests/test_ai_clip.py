import io
import math
import numpy as np
import pytest
import pytest_asyncio
from PIL import Image
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.config import settings
from app.core.database import db_manager
from app.main import app
from app.modules.ai.clip_manager import clip_manager
from app.modules.ai.preprocessor import preprocessor
from app.modules.ai.repository import embedding_repository
from app.modules.ai.service import ai_service, cosine_similarity
from app.modules.shopping.service import shopping_service
from app.modules.wardrobe.repository import wardrobe_repository
from app.modules.wardrobe.service import wardrobe_service


def create_synthetic_image_bytes(
    size: tuple[int, int] = (224, 224),
    color: str = "blue",
    format: str = "JPEG",
) -> bytes:
    """Helper to generate in-memory synthetic image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


@pytest_asyncio.fixture(autouse=True)
async def mock_db():
    """Setup isolated in-memory MongoDB mock database."""
    mock_client = AsyncMongoMockClient()
    mock_database = mock_client["stylesync_ai_test"]
    db_manager.client = mock_client
    db_manager.db = mock_database
    yield mock_database
    mock_client.close()


def test_preprocessor_decoding_and_clahe():
    """Verify OpenCV decoding, LAB CLAHE exposure enhancement, and PIL conversion."""
    image_bytes = create_synthetic_image_bytes(size=(300, 300), color="red", format="JPEG")

    # 1. Test raw BGR decoding
    bgr = preprocessor.decode_image_bytes(image_bytes)
    assert isinstance(bgr, np.ndarray)
    assert bgr.shape == (300, 300, 3)

    # 2. Test CLAHE enhancement
    enhanced = preprocessor.enhance_contrast_and_lighting(bgr)
    assert isinstance(enhanced, np.ndarray)
    assert enhanced.shape == (300, 300, 3)

    # 3. Test end-to-end preprocessing for model input
    pil_img = preprocessor.preprocess_for_clip(image_bytes, target_size=(224, 224))
    assert isinstance(pil_img, Image.Image)
    assert pil_img.size == (224, 224)
    assert pil_img.mode == "RGB"


def test_preprocessor_invalid_bytes_handling():
    """Verify invalid or corrupted byte streams are rejected with ValueError."""
    with pytest.raises(ValueError):
        preprocessor.decode_image_bytes(b"")

    with pytest.raises(ValueError):
        preprocessor.decode_image_bytes(b"corrupted_binary_data_stream_not_an_image")


def test_clip_manager_initialization():
    """Verify CLIP model manager initialization and status."""
    clip_manager.load_model()
    assert clip_manager.embedding_dim == 512


def test_clip_image_embedding_generation_and_l2_normalization():
    """Verify image embedding generates a 512-dim unit vector (L2 norm = 1.0)."""
    pil_image = Image.new("RGB", (224, 224), color="darkblue")
    embedding = clip_manager.generate_image_embedding(pil_image)

    assert isinstance(embedding, list)
    assert len(embedding) == 512
    for val in embedding:
        assert isinstance(val, float)

    # Compute Euclidean L2 norm
    l2_norm = math.sqrt(sum(v * v for v in embedding))
    assert math.isclose(l2_norm, 1.0, rel_tol=1e-3)


def test_clip_text_embedding_generation_and_l2_normalization():
    """Verify text query embedding generates a 512-dim unit vector."""
    query = "a casual blue denim jacket for spring"
    embedding = clip_manager.generate_text_embedding(query)

    assert isinstance(embedding, list)
    assert len(embedding) == 512

    l2_norm = math.sqrt(sum(v * v for v in embedding))
    assert math.isclose(l2_norm, 1.0, rel_tol=1e-3)


def test_zero_shot_classification_distribution():
    """Verify zero-shot classification produces sorted probabilities summing to ~1.0."""
    pil_image = Image.new("RGB", (224, 224), color="blue")
    labels = ["blue", "red", "green", "yellow", "black"]
    results = clip_manager.zero_shot_classify(pil_image, labels)

    assert len(results) == len(labels)
    # Check descending order
    probs = [prob for _, prob in results]
    assert probs == sorted(probs, reverse=True)
    assert math.isclose(sum(probs), 1.0, rel_tol=1e-2)


def test_ai_service_extract_clothing_metadata():
    """Verify AI service extracts clothing attributes and calibrated confidence scores."""
    image_bytes = create_synthetic_image_bytes(size=(250, 250), color="green", format="JPEG")
    metadata = ai_service.extract_clothing_metadata(image_bytes, filename="emerald_summer_dress.jpg")

    assert "type" in metadata
    assert "category" in metadata
    assert "primary_color" in metadata
    assert "pattern" in metadata
    assert "season" in metadata and isinstance(metadata["season"], list)
    assert "occasion" in metadata and isinstance(metadata["occasion"], list)
    assert "sleeve_type" in metadata
    assert "confidence" in metadata

    conf = metadata["confidence"]
    assert "type" in conf and isinstance(conf["type"], float)
    assert "category" in conf and isinstance(conf["category"], float)
    assert "color" in conf and isinstance(conf["color"], float)
    assert "pattern" in conf and isinstance(conf["pattern"], float)
    assert "season" in conf and isinstance(conf["season"], float)
    assert "occasion" in conf and isinstance(conf["occasion"], float)


@pytest.mark.asyncio
async def test_wardrobe_upload_end_to_end_ai_pipeline():
    """Verify wardrobe upload extracts AI metadata and saves L2-normalized 512-dim embedding."""
    user_id = "usr-ai-test-1"
    image_bytes = create_synthetic_image_bytes(size=(300, 300), color="black", format="JPEG")

    item = await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        file_bytes=image_bytes,
        filename="black_evening_blazer.jpg",
        name="Black Evening Blazer",
        content_type="image/jpeg",
    )

    item_id = str(item["id"])
    assert item["name"] == "Black Evening Blazer"
    assert "confidence" in item
    assert "embedding_id" in item and item["embedding_id"] is not None

    # Verify item persisted in MongoDB wardrobe_items
    saved_item = await wardrobe_repository.get_item_by_id(item_id, user_id)
    assert saved_item is not None
    assert saved_item["embedding_id"] == item["embedding_id"]

    # Verify vector embedding persisted in MongoDB item_embeddings
    embedding_doc = await embedding_repository.get_by_item_id(item_id)
    assert embedding_doc is not None
    assert embedding_doc["user_id"] == user_id
    assert embedding_doc["embedding_dim"] == 512
    assert len(embedding_doc["embedding"]) == 512


@pytest.mark.asyncio
async def test_shopping_duplicate_check_with_ai_image():
    """Verify shopping duplicate detection with multimodal image feature extraction."""
    user_id = "usr-ai-shopping-1"

    # Add item to user's wardrobe
    dress_bytes = create_synthetic_image_bytes(size=(200, 200), color="blue")
    await wardrobe_service.create_item_from_upload(
        user_id=user_id,
        file_bytes=dress_bytes,
        filename="royal_blue_dress.jpg",
        name="Royal Blue Dress",
        content_type="image/jpeg",
    )

    # Check shopping item with matching blue photo
    query_bytes = create_synthetic_image_bytes(size=(200, 200), color="blue")
    result = await shopping_service.check_duplicate_purchase(
        user_id=user_id,
        filename="new_blue_dress.jpg",
        file_bytes=query_bytes,
    )

    assert "decision" in result
    assert "highest_similarity" in result
    assert "similar_items" in result
    assert len(result["similar_items"]) >= 1
    assert result["similar_items"][0]["name"] == "Royal Blue Dress"


@pytest.mark.asyncio
async def test_fastapi_wardrobe_ai_upload_endpoint():
    """Verify FastAPI HTTP multipart endpoint returns AI metadata and confidence scores."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"name": "AI Tester", "email": "ai@stylesync.dev", "password": "SecurePassword123!"},
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload clothing item
        image_bytes = create_synthetic_image_bytes(size=(250, 250), color="red")
        files = {"image": ("red_silk_shirt.jpg", image_bytes, "image/jpeg")}
        data = {"name": "Red Silk Shirt"}

        upload_res = await client.post("/api/v1/wardrobe/items", headers=headers, files=files, data=data)
        assert upload_res.status_code == 201
        payload = upload_res.json()["item"]

        assert payload["name"] == "Red Silk Shirt"
        assert "confidence" in payload
        assert "category" in payload
        assert "primary_color" in payload
        assert "pattern" in payload
        assert "season" in payload
        assert "occasion" in payload
