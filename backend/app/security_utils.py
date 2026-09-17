from __future__ import annotations

from typing import Iterable, Sequence

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _validate_encryption_key(raw_key: str) -> str:
    """Validate Fernet-compatible secret keys and reject insecure placeholders."""
    if not raw_key or raw_key.strip() in {"", "CHANGE_ME", "YOUR_SUPER_SECRET_KEY_HERE_FOR_MVP", "DEFAULT"}:
        raise ValueError(
            "ENCRYPTION_KEY is missing or still using a placeholder value. "
            "Set a valid Fernet key in the environment for this deployment."
        )

    try:
        Fernet(raw_key.encode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive guard for invalid config
        raise ValueError(
            "ENCRYPTION_KEY must be a valid Fernet key (32-byte URL-safe base64 value)."
        ) from exc
    return raw_key


def _iter_cipher_keys(legacy_keys: Sequence[str] | None = None) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for key in ([getattr(settings, "ENCRYPTION_KEY", None)] + list(legacy_keys or []) + list(getattr(settings, "ENCRYPTION_KEY_ROTATION_KEYS", []) or [])):
        if key is None:
            continue
        normalized = str(key).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(normalized)
    return candidates


def _get_cipher(key: str | None = None) -> Fernet:
    """Create a Fernet cipher only from a validated deployment key."""
    selected_key = key or settings.ENCRYPTION_KEY
    _validate_encryption_key(selected_key)
    return Fernet(selected_key.encode("utf-8"))


def encrypt_secret(secret: str, key: str | None = None) -> str:
    if not secret:
        return ""
    cipher = _get_cipher(key)
    encrypted = cipher.encrypt(secret.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_secret(encrypted_secret: str, key: str | None = None, legacy_keys: Sequence[str] | None = None) -> str:
    if not encrypted_secret:
        return ""

    candidate_keys = _iter_cipher_keys(legacy_keys)
    if key is not None:
        candidate_keys = [str(key).strip(), *candidate_keys]

    for candidate_key in candidate_keys:
        try:
            cipher = _get_cipher(candidate_key)
            decrypted = cipher.decrypt(encrypted_secret.encode("utf-8"))
            return decrypted.decode("utf-8")
        except (InvalidToken, TypeError, ValueError):
            continue

    raise ValueError(
        "Unable to decrypt the secret with the active key or any configured rotation key. "
        "Check the environment configuration and available recovery keys."
    )
