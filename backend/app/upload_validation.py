import json
import os
from pathlib import Path

from defusedxml import defuse_stdlib

defuse_stdlib()

from xml.etree import ElementTree  # nosec B405 - parser is hardened via defusedxml.defuse_stdlib()

from fastapi import HTTPException, UploadFile


DEFAULT_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024
ALLOWED_MEDIA_TYPES = {
    ".json": {"application/json"},
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".xml": {"application/xml", "text/xml"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}


def get_max_upload_size() -> int:
    from app.config import settings
    return settings.MAX_UPLOAD_SIZE_BYTES


def read_validated_upload(file: UploadFile, file_name: str, antimalware_enabled: bool = True) -> tuple[bytes, bool]:
    extension = Path(file_name).suffix.lower()
    allowed_media_types = ALLOWED_MEDIA_TYPES.get(extension)
    if allowed_media_types is None:
        raise HTTPException(status_code=415, detail="unsupported file extension")

    media_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if media_type not in allowed_media_types:
        raise HTTPException(status_code=415, detail="content type does not match file extension")

    max_size = get_max_upload_size()
    content = bytearray()
    while True:
        chunk = file.file.read(min(READ_CHUNK_SIZE, max_size - len(content) + 1))
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="file exceeds maximum upload size")

    if not content:
        raise HTTPException(status_code=422, detail="empty files are not allowed")

    payload = bytes(content)
    is_malware = False
    if antimalware_enabled:
        is_malware = scan_for_malware(payload)
    
    _validate_content(extension, payload)
    return payload, is_malware


def scan_for_malware(content: bytes) -> bool:
    # MVP: EICAR test signature detection
    eicar_signature = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    if eicar_signature in content:
        return True
    return False


def _decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail="text content must be UTF-8") from error


def _validate_content(extension: str, content: bytes) -> None:
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=422, detail="invalid PDF signature")
        return

    if extension in [".jpg", ".jpeg"]:
        # Basic check for JPEG magic number (FF D8).
        if not content.startswith(b"\xff\xd8"):
            raise HTTPException(status_code=422, detail="invalid JPEG signature")
        return

    if extension == ".png":
        # Basic check for PNG magic number (89 50 4E 47 0D 0A 1A 0A).
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status_code=422, detail="invalid PNG signature")
        return

    text = _decode_text(content)
    if extension == ".txt":
        if "\x00" in text:
            raise HTTPException(status_code=422, detail="text file contains binary data")
        return

    if extension == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=422, detail="invalid JSON content") from error
        return

    upper_text = text.upper()
    if "<!DOCTYPE" in upper_text or "<!ENTITY" in upper_text:
        raise HTTPException(status_code=422, detail="XML DTD and entities are not allowed")
    try:
        ElementTree.fromstring(text)  # nosec B314 - XML is parsed only after defuse_stdlib() hardening
    except ElementTree.ParseError as error:
        raise HTTPException(status_code=422, detail="invalid XML content") from error
