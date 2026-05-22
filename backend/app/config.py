from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://jmbariani:jmbariani_dev@localhost:5432/jmbariani"

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # OCR Settings
    TESSERACT_CMD: Optional[str] = None  # Use system default
    OCR_LANG: str = "eng+msa"  # English + Malay

    # JWT Auth
    SECRET_KEY: str = "jmbariani-dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # App
    APP_NAME: str = "JM Baryani HQ"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
