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

    response = client.get("/api/documents/search", params={"q": "Diploma"})
    assert response.status_code == 200, response.json()
    assert response.json()["total"] == 1

    response = client.get("/api/documents/search", params={"q": "inexistente"})
    assert response.status_code == 200
    assert response.json()["total"] == 0
