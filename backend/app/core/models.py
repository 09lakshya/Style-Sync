import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

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
    image_url = Column(String)
    thumbnail_url = Column(String)
    medium_url = Column(String)
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
    query_image_url = Column(String)
    similar_items = Column(JSON, default=list)
    decision = Column(String)
    highest_similarity = Column(Float)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    user = relationship("User", back_populates="shopping_checks")
