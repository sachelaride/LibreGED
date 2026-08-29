import json
import os
from pathlib import Path
from xml.etree import ElementTree

from fastapi import HTTPException, UploadFile


DEFAULT_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024
ALLOWED_MEDIA_TYPES = {
    ".json": {"application/json"},
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".xml": {"application/xml", "text/xml"},
}


def get_max_upload_size() -> int:
    from app.config import settings
    return settings.MAX_UPLOAD_SIZE_BYTES


def read_validated_upload(file: UploadFile, file_name: str) -> bytes:
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
    _validate_content(extension, payload)
    return payload


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
        ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise HTTPException(status_code=422, detail="invalid XML content") from error
