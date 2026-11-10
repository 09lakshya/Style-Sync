from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    app_name: str = "StyleSync"
    api_v1_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5173"
    jwt_secret: str = "stylesync-dev-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    database_url: str = "sqlite+aiosqlite:///./stylesync.db"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder_prefix: str = "stylesync"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_image_mime_types: set[str] = {"image/jpeg", "image/png", "image/webp"}
    max_image_dimension: int = 4096
    clip_model_name: str = "openai/clip-vit-base-patch32"
    clip_confidence_threshold: float = 0.22
    # Two-way softmax (menswear vs womenswear): below this the result is too
    # close to call and styling falls back to unisex.
    gender_confidence_threshold: float = 0.70
    ai_device: str = "cpu"
    enable_clahe_preprocessing: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    @property
    def effective_gemini_api_key(self) -> str:
        return self.gemini_api_key or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

    @property
    def is_cloudinary_configured(self) -> bool:
        return bool(self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret)

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
