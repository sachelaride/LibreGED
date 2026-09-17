from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models_ged_config import DocumentType


client = TestClient(app)


def create_document_type(name: str) -> str:
    document_type_id = name.lower().replace(" ", "-")
    with SessionLocal() as db:
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
    return document_type_id


def upload(document_type_id: str, title: str, content: bytes, student_id: str = None, group_id: str = None):
    payload = {
        "title": title,
        "document_type_id": document_type_id,
        "indices_json": "[]",
    }
    if student_id:
        payload["student_id"] = student_id
    if group_id:
        payload["group_id"] = group_id
    return client.post(
        "/api/documents/upload",
        data=payload,
        files={"file": ("documento.txt", content, "text/plain")},
    )


def test_document_search_uses_current_ged_contract():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Busca",
            "cnpj": "20.000.000/0001-00",
            "legal_name": "IES Busca Ltda",
        },
    )
    assert institution.status_code == 200, institution.json()

    document_type_id = create_document_type("Diploma")
    first = upload(
        document_type_id,
        "Diploma de Carlos Silva",
        b"conteudo academico de Carlos",
    )
    second = upload(
        document_type_id,
        "Historico de Ana Rosa",
        b"conteudo academico de Ana",
    )
    assert first.status_code == 200, first.json()
    assert second.status_code == 200, second.json()

    response = client.get("/api/documents/search", params={"q": "Carlos"})
    assert response.status_code == 200, response.json()
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Diploma de Carlos Silva"
    assert payload["items"][0]["status"] == "PENDENTE_VALIDACAO"
    assert payload["items"][0]["ocr_status"] in {"skipped", "success"}

    response = client.get("/api/documents/search", params={"q": "Diploma"})
    assert response.status_code == 200, response.json()
    assert response.json()["total"] == 1

    response = client.get("/api/documents/search", params={"q": "inexistente"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_document_search_accepts_filters_without_query():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Filtros",
            "cnpj": "21.000.000/0001-00",
            "legal_name": "IES Filtros Ltda",
        },
    )
    assert institution.status_code == 200, institution.json()

    document_type_id = create_document_type("Histórico")
    first = upload(
        document_type_id,
        "Histórico de Carlos",
        b"dados de Carlos em grupo turma-a",
        student_id="aluno-123",
        group_id="turma-a",
    )
    second = upload(
        document_type_id,
        "Histórico de Ana",
        b"dados de Ana em grupo turma-b",
        student_id="aluno-456",
        group_id="turma-b",
    )
    assert first.status_code == 200, first.json()
    assert second.status_code == 200, second.json()

    response = client.get("/api/documents/search", params={"student_id": "aluno-123"})
    assert response.status_code == 200, response.json()
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Histórico de Carlos"

    response = client.get("/api/documents/search", params={"group_id": "turma-b"})
    assert response.status_code == 200, response.json()
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Histórico de Ana"

    response = client.get("/api/documents/search", params={"document_type_id": document_type_id})
    assert response.status_code == 200, response.json()
    assert response.json()["total"] == 2
