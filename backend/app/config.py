import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class BaseConfig(BaseSettings):
    DATABASE_URL: str
    ENVIRONMENT: str = "development"
    MAX_UPLOAD_SIZE_BYTES: int = 10485760
    
    # JWT Auth
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_HERE_FOR_MVP"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Data Encryption
    ENCRYPTION_KEY: str = "WNeIS0sn-8vByPhTT--dXc0WdzgmXZiMdhNwSPKJoXY="

class DevelopmentConfig(BaseConfig):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/eduged_libre"
    ENVIRONMENT: str = "development"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

class TestConfig(BaseConfig):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/eduged_libre_test"
    ENVIRONMENT: str = "test"
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        env_prefix="TEST_",
        extra="ignore",
    )

class StagingConfig(BaseConfig):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/staging_db"
    ENVIRONMENT: str = "staging"
    model_config = SettingsConfigDict(env_file=".env.staging", env_file_encoding="utf-8", extra="ignore")

class ProductionConfig(BaseConfig):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/prod_db"
    ENVIRONMENT: str = "production"
    model_config = SettingsConfigDict(env_file=".env.production", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> BaseConfig:
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "test":
        return TestConfig()
    elif env in ["staging", "homologacao", "homologação"]:
        return StagingConfig()
    elif env == "production":
        return ProductionConfig()
    return DevelopmentConfig()

settings = get_settings()
