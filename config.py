# ============================================================
# App Configuration
# File: backend/config.py
# ============================================================

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "NagarSeva AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "nagarseva_db"
    
    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production-use-256bit"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    ALLOWED_EXTENSIONS: list = ["jpg", "jpeg", "png", "mp4", "mov"]
    
    # AI/ML
    AI_MODEL_PATH: str = "ai/models"
    ENABLE_AI_ANALYSIS: bool = True
    
    # Firebase (for notifications)
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS: Optional[str] = None
    
    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    
    # Google Maps
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
