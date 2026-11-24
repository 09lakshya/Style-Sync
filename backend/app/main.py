import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import close_db, connect_db
from app.modules.ai.clip_manager import clip_manager
from app.modules.ai.classifier_manager import classifier_manager
from app.modules.ai.router import router as ai_router
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.outfits.router import router as outfits_router
from app.modules.recommendations.router import router as recommendations_router
from app.modules.shopping.router import router as shopping_router
from app.modules.trends.router import router as trends_router
from app.modules.wardrobe.router import router as wardrobe_router

logger = logging.getLogger("stylesync.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and load AI models
    await connect_db()
    clip_manager.load_model()
    classifier_manager.load_model()
    yield
    # Shutdown
    await close_db()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

allowed_origins = [
    *(origin.strip().rstrip("/") for origin in settings.frontend_origin.split(",") if origin.strip()),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
ALLOWED_ORIGIN_PATTERN = re.compile(r"http://(localhost|127\.0\.0\.1)(:\d+)?")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=ALLOWED_ORIGIN_PATTERN.pattern,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict[str, str]:
    """CORS headers for an error response, for the app's own origins only.

    An unhandled exception is answered outside CORSMiddleware, so without these
    the browser hides the error from the frontend. They must not echo any
    origin that asks: with credentials allowed, that would let any site read
    the response.
    """
    origin = request.headers.get("origin", "")
    if origin in allowed_origins or ALLOWED_ORIGIN_PATTERN.fullmatch(origin):
        return {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true", "Vary": "Origin"}
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Keep the exception's own headers (Retry-After, WWW-Authenticate).
    headers = {**(exc.headers or {}), **_cors_headers(request)}
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # The details go to the log, not to the client: exception text can name
    # tables, file paths and config.
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. Please try again."},
        headers=_cors_headers(request),
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(wardrobe_router, prefix=settings.api_v1_prefix)
app.include_router(shopping_router, prefix=settings.api_v1_prefix)
app.include_router(recommendations_router, prefix=settings.api_v1_prefix)
app.include_router(analytics_router, prefix=settings.api_v1_prefix)
app.include_router(trends_router, prefix=settings.api_v1_prefix)
app.include_router(outfits_router, prefix=settings.api_v1_prefix)
app.include_router(ai_router, prefix=settings.api_v1_prefix)
