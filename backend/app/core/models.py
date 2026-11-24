import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, JSON, DateTime, ForeignKey
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import declarative_base, relationship


@compiles(String, "mysql")
def _mysql_string(type_, compiler, **kw):
    # SQLite takes a bare String, MySQL needs a length. 255 covers every
    # id, name and label here; URL columns are Text instead.
    if type_.length is None and not isinstance(type_, Text):
        return "VARCHAR(255)"
    return compiler.visit_string(type_, **kw)

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    password_salt = Column(String, default="")
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    wardrobe_items = relationship("WardrobeItem", back_populates="user", cascade="all, delete-orphan")
    shopping_checks = relationship("ShoppingCheck", back_populates="user", cascade="all, delete-orphan")

class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    
    # Media
    image_url = Column(Text)  # may hold a base64 data URI when Cloudinary is off
    thumbnail_url = Column(Text)  # may hold a base64 data URI when Cloudinary is off
    medium_url = Column(Text)  # may hold a base64 data URI when Cloudinary is off
    public_id = Column(String)
    format = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    bytes = Column(Integer)
    
    # Metadata
    type = Column(String)
    category = Column(String, index=True)
    primary_color = Column(String, index=True)
    secondary_colors = Column(JSON, default=list)
    pattern = Column(String)
    sleeve_type = Column(String)
    fabric = Column(String)
    season = Column(JSON, default=list)
    occasion = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    confidence = Column(JSON, default=dict)
    
    brand = Column(String, nullable=True)
    purchase_date = Column(DateTime(timezone=True), nullable=True)
    wear_count = Column(Integer, default=0, index=True)
    last_worn_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    # ML Classification
    predicted_category = Column(String, nullable=True)
    prediction_confidence = Column(Float, nullable=True)
    model_version = Column(String, nullable=True)
    # The classifier answers occasion, season and tradition independently, and
    # predicted_category can only hold one of the three. This keeps all of them,
    # along with the raw probabilities: thresholds have been recalibrated twice
    # already, and storing the scores means a recalibration can refresh every
    # item's verdicts without running the model over everyone's photos again.
    predicted_axes = Column(JSON, default=dict)
    
    embedding_id = Column(String, nullable=True) 
    
    user = relationship("User", back_populates="wardrobe_items")
    embedding_obj = relationship("Embedding", back_populates="item", uselist=False, cascade="all, delete-orphan")

class Embedding(Base):
    __tablename__ = "item_embeddings"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    item_id = Column(String, ForeignKey("wardrobe_items.id", ondelete="CASCADE"), unique=True, index=True)
    user_id = Column(String, index=True)
    model_name = Column(String, default="clip-vit-base-patch32")
    embedding = Column(JSON, nullable=False) # JSON array of floats
    embedding_dim = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    item = relationship("WardrobeItem", back_populates="embedding_obj")

class ShoppingCheck(Base):
    __tablename__ = "shopping_checks"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query_image_url = Column(Text)  # may hold a base64 data URI when Cloudinary is off
    similar_items = Column(JSON, default=list)
    decision = Column(String)
    highest_similarity = Column(Float)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    user = relationship("User", back_populates="shopping_checks")
