from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import close_db, connect_db
from app.modules.ai.clip_manager import clip_manager
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.recommendations.router import router as recommendations_router
from app.modules.shopping.router import router as shopping_router
from app.modules.wardrobe.router import router as wardrobe_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and load pretrained CLIP model once
    await connect_db()
    clip_manager.load_model()
    yield
    # Shutdown
    await close_db()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(wardrobe_router, prefix=settings.api_v1_prefix)
app.include_router(shopping_router, prefix=settings.api_v1_prefix)
app.include_router(recommendations_router, prefix=settings.api_v1_prefix)
app.include_router(analytics_router, prefix=settings.api_v1_prefix)
