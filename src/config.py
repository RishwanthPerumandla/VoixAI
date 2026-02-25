"""
VoixAI v3.0 - Configuration Management
Loads settings from environment variables
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # --------------------------------------------
    # API Keys
    # --------------------------------------------
    groq_api_key: str = Field(alias="GROQ_API_KEY")
    deepgram_api_key: str = Field(alias="DEEPGRAM_API_KEY")
    cartesia_api_key: str = Field(alias="CARTESIA_API_KEY")
    daily_api_key: str = Field(alias="DAILY_API_KEY")
    
    # --------------------------------------------
    # Local Services
    # --------------------------------------------
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    
    database_path: str = Field(default="data/voixai.db", alias="DATABASE_PATH")
    
    # --------------------------------------------
    # Application Settings
    # --------------------------------------------
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    port: int = Field(default=8000, alias="PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # --------------------------------------------
    # Feature Flags
    # --------------------------------------------
    enable_interruptions: bool = Field(default=True, alias="ENABLE_INTERRUPTIONS")
    enable_tts_cache: bool = Field(default=True, alias="ENABLE_TTS_CACHE")
    enable_vector_search: bool = Field(default=True, alias="ENABLE_VECTOR_SEARCH")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def ensure_data_dir(self):
        """Ensure data directory exists"""
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
