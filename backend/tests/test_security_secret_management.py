import pytest
from cryptography.fernet import Fernet

from app import security_utils


VALID_KEY = "WNeIS0sn-8vByPhTT--dXc0WdzgmXZiMdhNwSPKJoXY="


def test_encrypt_and_decrypt_round_trip(monkeypatch):
    monkeypatch.setattr(security_utils, "settings", type("Settings", (), {"ENCRYPTION_KEY": VALID_KEY})())

    value = "segredo-sensivel-123"
    encrypted = security_utils.encrypt_secret(value)

    assert encrypted != value
    assert security_utils.decrypt_secret(encrypted) == value


def test_decrypt_secret_supports_rotation_key(monkeypatch):
    current_key = Fernet.generate_key().decode()
    previous_key = Fernet.generate_key().decode()
    monkeypatch.setattr(
        security_utils,
        "settings",
        type(
            "Settings",
            (),
            {"ENCRYPTION_KEY": current_key, "ENCRYPTION_KEY_ROTATION_KEYS": [previous_key]},
        )(),
    )

    encrypted = security_utils.encrypt_secret("segredo-rotacionado", key=previous_key)
    assert security_utils.decrypt_secret(encrypted) == "segredo-rotacionado"


def test_invalid_encryption_key_is_rejected(monkeypatch):
    monkeypatch.setattr(security_utils, "settings", type("Settings", (), {"ENCRYPTION_KEY": "not-valid"})())

    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        security_utils.encrypt_secret("segredo")
