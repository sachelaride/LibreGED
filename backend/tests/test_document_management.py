import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import api_ged_upload
from app.main import app


client = TestClient(app)


def test_classified_upload_uses_index_defaults_and_combines_search_filters(
    tmp_path, monkeypatch
):
    def save_file(filename, content, **kwargs):
        path = Path(tmp_path) / filename
        path.write_bytes(content)
        return str(path)

    monkeypatch.setattr(api_ged_upload, "save_file", save_file)
    institution_response = client.post(
        "/api/institutions",
        json={
            "name": "IES Gestão Documental",
            "cnpj": "12.345.678/0001-90",
            "legal_name": "IES Gestão Documental Ltda",
        },
    )
    assert institution_response.status_code == 200, institution_response.json()

    document_type_response = client.post(
        "/api/document-types", json={"name": "Documentos Pessoais"}
    )
    assert document_type_response.status_code == 200, document_type_response.json()
    document_type_id = document_type_response.json()["id"]
    classification_response = client.post(
        f"/api/document-types/{document_type_id}/classifications",
        json={"name": "RG"},
    )
    assert classification_response.status_code == 200, classification_response.json()
    classification_id = classification_response.json()["id"]

    index_ids = []
    for name, value in (("CPF de teste", "12345678901"), ("Matrícula de teste", "202600123")):
        index_response = client.post(
            "/api/indices",
            json={
                "name": name,
                "type": "Texto",
                "default_value": value,
                "is_searchable": True,
            },
        )
        assert index_response.status_code == 200, index_response.json()
        index_id = index_response.json()["id"]
        index_ids.append(index_id)
        mapping_response = client.post(
            f"/api/document-types/{document_type_id}/indices",
            json={"index_id": index_id, "is_required": True},
        )
        assert mapping_response.status_code == 200, mapping_response.json()

    upload_response = client.post(
        "/api/documents/upload",
        data={
            "title": "RG de teste",
            "document_type_id": document_type_id,
            "classification_id": classification_id,
            "indices_json": "[]",
            "ocr_enabled": "false",
        },
        files={"file": ("rg.txt", b"conteudo de teste", "text/plain")},
    )
    assert upload_response.status_code == 200, upload_response.json()
    assert upload_response.json()["classification_id"] == classification_id

    other_upload_response = client.post(
        "/api/documents/upload",
        data={
            "title": "RG de outro aluno",
            "document_type_id": document_type_id,
            "classification_id": classification_id,
            "indices_json": json.dumps([
                {"index_id": index_ids[0], "value": "99999999999"},
                {"index_id": index_ids[1], "value": "202600123"},
            ]),
            "ocr_enabled": "false",
        },
        files={"file": ("rg-outro.txt", b"outro conteudo", "text/plain")},
    )
    assert other_upload_response.status_code == 200, other_upload_response.json()

    search_response = client.get(
        "/api/documents/search",
        params={
            "document_type_id": document_type_id,
            "index_filters": json.dumps([
                {"index_id": index_ids[0], "value": "123456"},
                {"index_id": index_ids[1], "value": "202600"},
            ]),
        },
    )
    assert search_response.status_code == 200, search_response.json()
    assert search_response.json()["total"] == 1
    result = next(item for item in search_response.json()["items"] if item["title"] == "RG de teste")
    assert result["classification"] == {"id": classification_id, "name": "RG"}
    assert result["created_at"]
    assert {index["value"] for index in result["indices"]} >= {"12345678901", "202600123"}
    classification_search = client.get(
        "/api/documents/search",
        params={
            "classification_id": classification_id,
            "document_type_id": document_type_id,
        },
    )
    assert classification_search.status_code == 200, classification_search.json()
    assert classification_search.json()["total"] == 2

    omitted_classification_response = client.post(
        "/api/documents/upload",
        data={
            "title": "RG sem classificação",
            "document_type_id": document_type_id,
            "indices_json": "[]",
            "ocr_enabled": "false",
        },
        files={"file": ("rg.txt", b"conteudo", "text/plain")},
    )
    assert omitted_classification_response.status_code == 422

    index_response = client.get("/api/indices")
    current_index = next(
        item for item in index_response.json()["items"] if item["id"] == index_ids[0]
    )
    updated_index = client.put(
        f"/api/indices/{index_ids[0]}",
        json={
            "name": current_index["name"],
            "type": current_index["type"],
            "options": current_index["options"],
            "mask": current_index["mask"],
            "default_value": current_index["default_value"],
            "is_searchable": False,
            "auto_increment": current_index["auto_increment"],
            "is_active": current_index["is_active"],
        },
    )
    assert updated_index.status_code == 200, updated_index.json()
    rejected_search = client.get(
        "/api/documents/search",
        params={
            "document_type_id": document_type_id,
            "index_filters": json.dumps([
                {"index_id": index_ids[0], "value": "123456"},
            ]),
        },
    )
    assert rejected_search.status_code == 422
