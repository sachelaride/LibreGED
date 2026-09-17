from pathlib import Path
import hashlib

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models_ged_config import DocumentType


client = TestClient(app)


def create_document_type(name: str) -> str:
    document_type_id = name.lower().replace(" ", "-")
    db = SessionLocal()
    try:
        db.add(
            DocumentType(
                id=document_type_id,
                name=name,
                is_active=True,
                storage_area_id="default",
                storage_partition_id="default",
            )
        )
        db.commit()
    finally:
        db.close()
    return document_type_id


def create_institution(name: str, cnpj: str) -> dict:
    response = client.post(
        "/api/institutions",
        json={"name": name, "cnpj": cnpj, "legal_name": f"{name} Ltda"},
    )
    assert response.status_code == 200, response.json()
    return response.json()


def upload(document_type_id: str, title: str, content: bytes):
    return client.post(
        "/api/documents/upload",
        data={
            "title": title,
            "document_type_id": document_type_id,
            "indices_json": "[]",
        },
        files={"file": ("documento.txt", content, "text/plain")},
    )


def test_document_upload_and_audit():
    create_institution("IES Teste", "12.345.678/0001-99")
    document_type_id = create_document_type("Histórico Escolar")

    response = upload(
        document_type_id,
        "Histórico escolar",
        b"conteudo do historico escolar",
    )

    assert response.status_code == 200, response.json()
    payload = response.json()
    assert payload["title"] == "Histórico escolar"
    assert payload["status"] == "PENDENTE_VALIDACAO"
    assert payload["file_hash"] == hashlib.sha256(b"conteudo do historico escolar").hexdigest()
    assert Path(payload["file_path"]).read_bytes() == b"conteudo do historico escolar"

    audit = client.get("/api/audit")
    assert audit.status_code == 200
    assert len(audit.json()) > 0


def test_upload_rejects_unknown_document_type():
    response = upload("missing-document-type", "Documento", b"conteudo")

    assert response.status_code == 400
    assert response.json() == {"detail": "Tipo de Documento inválido."}


def test_upload_and_search_documents():
    create_institution("IES Busca", "10.000.000/0001-00")
    document_type_id = create_document_type("Contrato de Matrícula")

    response = upload(
        document_type_id,
        "Contrato de matrícula",
        b"conteudo do contrato",
    )
    assert response.status_code == 200, response.json()

    search_response = client.get(
        "/api/documents/search",
        params={"q": "Contrato de matrícula"},
    )
    assert search_response.status_code == 200, search_response.json()
    payload = search_response.json()
    assert payload["total"] >= 1
    assert any(item["title"] == "Contrato de matrícula" for item in payload["items"])


def test_document_details_and_retention_are_exposed_by_current_api():
    create_institution("IES GED", "11.111.111/0001-11")
    document_type_id = create_document_type("Histórico de Notas")
    response = upload(document_type_id, "Histórico de notas", b"notas")
    assert response.status_code == 200, response.json()
    document_id = response.json()["id"]

    details = client.get(f"/api/documents/{document_id}/details")
    assert details.status_code == 200, details.json()
    assert details.json()["id"] == document_id
