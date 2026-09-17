import uuid

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models_ged_config import DocumentType


client = TestClient(app)


def test_get_rvdd_html():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES RVDD",
            "cnpj": "62.000.000/0001-00",
            "legal_name": "IES RVDD Ltda",
        },
    )
    assert institution.status_code == 200, institution.json()

    document_type_id = str(uuid.uuid4())
    db = SessionLocal()
    db.add(
        DocumentType(
            id=document_type_id,
            name="Documento RVDD",
            storage_area_id="dummy_area",
            storage_partition_id="dummy_partition",
            is_active=True,
        )
    )
    db.commit()
    db.close()

    document = client.post(
        "/api/documents/upload",
        data={
            "title": "Diploma de João",
            "document_type_id": document_type_id,
            "indices_json": "[]",
        },
        files={"file": ("diploma.xml", b"<Diploma/>", "application/xml")},
    )
    assert document.status_code == 200, document.json()
    document_id = document.json()["id"]

    response = client.post(
        f"/api/documents/{document_id}/representation",
        json={"student_name": "João da Silva", "course_name": "Curso"},
    )

    assert response.status_code == 200, response.json()
    html_content = response.json()["html_content"]
    assert "República Federativa do Brasil" in html_content
    assert "João da Silva" in html_content
    assert "data:image/png;base64," in html_content
    assert f"https://eduged_libre.edu.br/validar/{document_id}" in html_content
