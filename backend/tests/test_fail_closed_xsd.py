import uuid

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models_ged_config import DocumentType


client = TestClient(app)


def _document_id(document_type_id: str) -> str:
    response = client.post(
        "/api/documents/upload",
        data={
            "title": "Diploma",
            "document_type_id": document_type_id,
            "indices_json": "[]",
        },
        files={"file": ("diploma.xml", b"<Diploma/>", "application/xml")},
    )
    assert response.status_code == 200, response.json()
    return response.json()["id"]


def _document_type_id() -> str:
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES XML",
            "cnpj": "64.000.000/0001-00",
            "legal_name": "IES XML Ltda",
        },
    )
    assert institution.status_code == 200, institution.json()

    document_type_id = str(uuid.uuid4())
    db = SessionLocal()
    db.add(
        DocumentType(
            id=document_type_id,
            name="Documento XML",
            storage_area_id="dummy_area",
            storage_partition_id="dummy_partition",
            is_active=True,
        )
    )
    db.commit()
    db.close()
    return document_type_id


def _request(**overrides):
    payload = {
        "student_name": "Ana Silva",
        "course_name": "Curso",
        "status": "pending",
        "document_type": "diploma",
        "schema_version": "diploma-1",
        "namespace": "https://example.org/diploma/1",
        "environment": "homologation",
    }
    payload.update(overrides)
    return payload


def test_xml_without_schema_version_is_blocked_and_audited():
    document_id = _document_id(_document_type_id())
    response = client.post(
        f"/api/documents/{document_id}/xml",
        json=_request(schema_version=None),
    )
    assert response.status_code == 409
    assert "version inference is forbidden" in response.json()["detail"]
    audit = client.get("/api/audit").json()
    assert any(event["action"] == "xml_generation_blocked" for event in audit)


def test_xml_with_unapproved_schema_is_blocked():
    document_type_id = _document_type_id()
    document_id = _document_id(document_type_id)
    created = client.post(
        "/api/xsd",
        json={
            "document_type_id": document_type_id,
            "code": "diploma-1",
            "namespace": "https://example.org/diploma/1",
            "xsd_hash": "b" * 64,
            "environment": "homologation",
        },
    )
    assert created.status_code == 200, created.json()

    response = client.post(
        f"/api/documents/{document_id}/xml",
        json=_request(),
    )
    assert response.status_code == 409
    assert "not approved" in response.json()["detail"]
