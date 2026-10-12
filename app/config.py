import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "ComicCraft"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    BASE_DIR: Path = BASE_DIR
    
    # API Keys
    GEMINI_API_KEY: str = ""
    HF_API_KEY: str = ""
    
    # Models (Configurable via environment variables)
    GEMINI_FLASH_MODEL: str = "gemini-3.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-3.5-flash"
    HF_IMAGE_MODEL: str = "runwayml/stable-diffusion-v1-5"
    IMAGE_PROVIDER: str = "auto"  # "auto", "pollinations", "hf", "canvas"
    
    # Storage paths
    STATIC_DIR: Path = BASE_DIR / "app" / "static"
    PANELS_DIR: Path = BASE_DIR / "app" / "static" / "panels"
    EXPORTS_DIR: Path = BASE_DIR / "app" / "static" / "exports"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/comiccraft.db"
    
    # Modes
    ENABLE_OFFLINE_DEMO: bool = True
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()

# Ensure directories exist
settings.PANELS_DIR.mkdir(parents=True, exist_ok=True)
settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
