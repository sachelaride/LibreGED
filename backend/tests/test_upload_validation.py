from io import BytesIO

from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
import pytest
from starlette.datastructures import Headers

from app import models, storage
from app.database import SessionLocal
from app.main import app
from app.upload_validation import read_validated_upload


client = TestClient(app)


def upload_file(name: str, content: bytes, media_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=name,
        headers=Headers({"content-type": media_type}),
    )


@pytest.mark.parametrize(
    ("name", "content", "media_type"),
    [
        ("documento.pdf", b"%PDF-1.7\nconteudo", "application/pdf"),
        ("documento.xml", b"<?xml version='1.0'?><documento />", "application/xml"),
        ("documento.json", b'{"status": "ok"}', "application/json"),
        ("documento.txt", b"conteudo academico", "text/plain"),
    ],
)
def test_accepts_supported_content(name: str, content: bytes, media_type: str):
    assert read_validated_upload(upload_file(name, content, media_type), name) == content


@pytest.mark.parametrize(
    ("name", "content", "media_type", "expected_status"),
    [
        ("programa.exe", b"MZ", "application/octet-stream", 415),
        ("falso.pdf", b"nao e pdf", "application/pdf", 422),
        ("falso.xml", b"<documento>", "application/xml", 422),
        ("entidade.xml", b"<!DOCTYPE x [<!ENTITY y 'z'>]><x>&y;</x>", "application/xml", 422),
        ("falso.json", b"{invalido}", "application/json", 422),
        ("vazio.txt", b"", "text/plain", 422),
        ("arquivo.pdf", b"%PDF-1.7", "text/plain", 415),
    ],
)
def test_rejects_unsupported_or_mismatched_content(
    name: str,
    content: bytes,
    media_type: str,
    expected_status: int,
):
    with pytest.raises(HTTPException) as captured:
        read_validated_upload(upload_file(name, content, media_type), name)

    assert captured.value.status_code == expected_status


def test_enforces_configured_size_limit():
    from app.config import settings
    old_value = settings.MAX_UPLOAD_SIZE_BYTES
    settings.MAX_UPLOAD_SIZE_BYTES = 4
    try:
        with pytest.raises(HTTPException) as captured:
            read_validated_upload(upload_file("grande.txt", b"12345", "text/plain"), "grande.txt")
        assert captured.value.status_code == 413
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = old_value


def test_rejected_upload_leaves_no_file_version_or_audit():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Upload Seguro",
            "cnpj": "56.000.000/0001-00",
            "legal_name": "IES Upload Seguro Ltda",
        },
    ).json()
    student = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Aluno Upload",
            "birth_date": "2005-01-01",
            "cpf": "60470480494",
            "email": "upload@example.org",
        },
    ).json()
    enrollment = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "course_name": "Curso Upload",
            "class_name": "A",
            "year": 2026,
            "status": "active",
        },
    ).json()
    document = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "enrollment_id": enrollment["id"],
            "document_type": "historico",
            "title": "Historico Upload",
            "status": "pending",
        },
    ).json()

    files_before = set(storage.STORAGE_ROOT.iterdir())
    audit_before = client.get("/api/audit").json()
    response = client.post(
        f"/api/documents/{document['id']}/upload",
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 415
    assert set(storage.STORAGE_ROOT.iterdir()) == files_before
    assert client.get("/api/audit").json() == audit_before

    db = SessionLocal()
    try:
        version_count = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == document["id"])
            .count()
        )
        assert version_count == 0
    finally:
        db.close()
