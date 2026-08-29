import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    ENVIRONMENT: str = "development"
    MAX_UPLOAD_SIZE_BYTES: int = 10485760
    
    # JWT Auth
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_HERE_FOR_MVP"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
