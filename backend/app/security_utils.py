from cryptography.fernet import Fernet
from app.config import settings
import base64

def _get_cipher() -> Fernet:
    # Ensure key is bytes and exactly 32 url-safe base64-encoded bytes
    key = settings.ENCRYPTION_KEY.encode('utf-8')
    return Fernet(key)

def encrypt_secret(secret: str) -> str:
    if not secret:
        return ""
    cipher = _get_cipher()
    encrypted = cipher.encrypt(secret.encode('utf-8'))
    return encrypted.decode('utf-8')

def decrypt_secret(encrypted_secret: str) -> str:
    if not encrypted_secret:
        return ""
    cipher = _get_cipher()
    decrypted = cipher.decrypt(encrypted_secret.encode('utf-8'))
    return decrypted.decode('utf-8')
