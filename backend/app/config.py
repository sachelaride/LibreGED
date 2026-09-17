import os
from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_VALUES = {
    "",
    "CHANGE_ME",
    "DEFAULT",
    "YOUR_SUPER_SECRET_KEY_HERE_FOR_MVP",
    "REPLACE_ME",
    "TODO",
}


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = str(value).strip()
    return not normalized or normalized.upper() in {v.upper() for v in _PLACEHOLDER_VALUES}


def _normalize_list_value(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _validate_runtime_secrets(config: "BaseConfig") -> None:
    env = str(getattr(config, "ENVIRONMENT", "development")).lower()
    if env in {"test", "development"}:
        return

    secret_key = getattr(config, "SECRET_KEY", None)
    if _is_placeholder(secret_key):
        raise RuntimeError(
            "SECRET_KEY must be set to a non-placeholder value in staging/production environments."
        )

    encryption_key = getattr(config, "ENCRYPTION_KEY", None)
    if _is_placeholder(encryption_key):
        raise RuntimeError(
            "ENCRYPTION_KEY must be set to a non-placeholder value in staging/production environments."
        )

    if secret_key == encryption_key:
        raise RuntimeError(
            "SECRET_KEY and ENCRYPTION_KEY must be different values to avoid key reuse across JWT and data encryption."
        )

    try:
        Fernet(str(encryption_key).encode("utf-8"))
    except Exception as exc:  # pragma: no cover - validation guard on configuration
        raise RuntimeError(
            "ENCRYPTION_KEY must be a valid Fernet key (32-byte URL-safe base64 string)."
        ) from exc

    for rotation_key in _normalize_list_value(getattr(config, "ENCRYPTION_KEY_ROTATION_KEYS", [])):
        if _is_placeholder(rotation_key):
            raise RuntimeError(
                "ENCRYPTION_KEY_ROTATION_KEYS cannot include placeholders in staging/production environments."
            )
        if rotation_key == str(encryption_key):
            continue
        try:
            Fernet(rotation_key.encode("utf-8"))
        except Exception as exc:  # pragma: no cover - validation guard on configuration
            raise RuntimeError(
                "ENCRYPTION_KEY_ROTATION_KEYS must contain only valid Fernet keys."
            ) from exc

    for rotation_key in _normalize_list_value(getattr(config, "SECRET_KEY_ROTATION_KEYS", [])):
        if _is_placeholder(rotation_key):
            raise RuntimeError(
                "SECRET_KEY_ROTATION_KEYS cannot include placeholders in staging/production environments."
            )
        if rotation_key == str(secret_key):
            continue
        # A rotation key is a historical secret and is not used for signing until explicitly selected;
        # the validation here is therefore limited to plain non-placeholder integrity checks.
        if len(rotation_key) < 32:
            raise RuntimeError("SECRET_KEY_ROTATION_KEYS must contain non-empty values larger than the placeholder baseline.")


class BaseConfig(BaseSettings):
    DATABASE_URL: str
    ENVIRONMENT: str = "development"
    MAX_UPLOAD_SIZE_BYTES: int = 10485760
    FILEWATCH_MAX_RETRIES: int = 5
    FILEWATCH_RETRY_BASE_SECONDS: int = 60

    # JWT Auth
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_HERE_FOR_MVP"
    SECRET_KEY_ROTATION_KEYS: list[str] = Field(default_factory=list)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Data Encryption
    ENCRYPTION_KEY: str = "WNeIS0sn-8vByPhTT--dXc0WdzgmXZiMdhNwSPKJoXY="
    ENCRYPTION_KEY_ROTATION_KEYS: list[str] = Field(default_factory=list)


class DevelopmentConfig(BaseConfig):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/eduged_libre"
    ENVIRONMENT: str = "development"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class TestConfig(BaseConfig):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/eduged_libre_test"
    ENVIRONMENT: str = "test"
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        env_prefix="TEST_",
        extra="ignore",
    )


class StagingConfig(BaseConfig):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/staging_db"
    ENVIRONMENT: str = "staging"
    model_config = SettingsConfigDict(env_file=".env.staging", env_file_encoding="utf-8", extra="ignore")


class ProductionConfig(BaseConfig):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/prod_db"
    ENVIRONMENT: str = "production"
    model_config = SettingsConfigDict(env_file=".env.production", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> BaseConfig:
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "test":
        settings_obj = TestConfig()
    elif env in ["staging", "homologacao", "homologação"]:
        settings_obj = StagingConfig()
    elif env == "production":
        settings_obj = ProductionConfig()
    else:
        settings_obj = DevelopmentConfig()

    _validate_runtime_secrets(settings_obj)
    return settings_obj


settings = get_settings()
