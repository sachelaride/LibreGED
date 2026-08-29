from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _document_id():
    institution = client.post("/api/institutions", json={"name": "IES", "cnpj": "12345678000199", "legal_name": "IES Legal"}).json()
    student = client.post("/api/students", json={"institution_id": institution["id"], "full_name": "Ana Silva", "birth_date": "2010-01-01", "cpf": "12345678901", "email": "ana@example.org"}).json()
    enrollment = client.post("/api/enrollments", json={"institution_id": institution["id"], "student_id": student["id"], "course_name": "Curso", "class_name": "A", "year": 2026}).json()
    return client.post("/api/documents", json={"institution_id": institution["id"], "student_id": student["id"], "enrollment_id": enrollment["id"], "document_type": "diploma", "title": "Diploma"}).json()["id"]


def _request(**overrides):
    payload = {"student_name": "Ana Silva", "course_name": "Curso", "status": "pending", "document_type": "diploma", "schema_version": "diploma-1", "namespace": "https://example.org/diploma/1", "environment": "homologation"}
    payload.update(overrides)
    return payload


def test_xml_without_schema_version_is_blocked_and_audited():
    document_id = _document_id()
    response = client.post(f"/api/documents/{document_id}/xml", json=_request(schema_version=None))
    assert response.status_code == 409
    assert "version inference is forbidden" in response.json()["detail"]
    audit = client.get("/api/audit").json()
    assert any(event["action"] == "xml_generation_blocked" for event in audit)


def test_xml_with_unapproved_or_incompatible_schema_is_blocked():
    document_id = _document_id()
    created = client.post("/api/schema-versions", json={"code": "diploma-1", "document_type": "diploma", "namespace": "https://example.org/diploma/1", "xsd_hash": "b" * 64, "status": "proposed", "valid_from": "2020-01-01T00:00:00", "environment": "homologation"})
    assert created.status_code == 201
    response = client.post(f"/api/documents/{document_id}/xml", json=_request())
    assert response.status_code == 409
    assert "not approved" in response.json()["detail"]
