from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models_ged import GEDDocument, GEDDocumentStatus
from app.models_ged_config import DocumentType


client = TestClient(app)


def test_ged_upload_starts_in_validation_state():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Estado",
            "cnpj": "22.222.222/0001-22",
            "legal_name": "IES Estado Ltda",
        },
    )
    assert institution.status_code == 200, institution.json()

    db = SessionLocal()
    try:
        document_type = DocumentType(
            id="tipo-estado",
            name="Comprovante de Residência",
            is_active=True,
            storage_area_id="default",
            storage_partition_id="default",
        )
        db.add(document_type)
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/documents/upload",
        data={
            "title": "Conta de Luz",
            "document_type_id": "tipo-estado",
            "indices_json": "[]",
        },
        files={"file": ("conta.txt", b"endereco", "text/plain")},
    )
    assert response.status_code == 200, response.json()
    assert response.json()["status"] == GEDDocumentStatus.PENDENTE_VALIDACAO.value

    db = SessionLocal()
    try:
        document = db.query(GEDDocument).filter_by(id=response.json()["id"]).one()
        assert document.status == GEDDocumentStatus.PENDENTE_VALIDACAO
    finally:
        db.close()
