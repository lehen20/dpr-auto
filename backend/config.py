import os
from pathlib import Path
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    google_api_key: str
    upload_dir: str = "./uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: set = {
        "pdf","txt", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "json", "csv", "xml", "html", "md", "rtf"
    }
    gemini_model: str = "gemini-2.5-flash"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


def get_settings() -> Settings:
    return Settings()


def ensure_upload_dir(upload_dir: str) -> None:
    Path(upload_dir).mkdir(parents=True, exist_ok=True)