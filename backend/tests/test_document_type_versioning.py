from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_document_type_policy_versioning():
    create_response = client.post(
        "/api/document-types",
        json={
            "name": "Histórico Escolar Versionado",
            "retention_years": 5,
            "legal_hold": False,
            "access_policy": {"roles": ["academico", "auditor"]},
            "signature_rule": {"required": True, "order": ["secretaria", "direcao"]},
        },
    )
    assert create_response.status_code == 200, create_response.text
    document_type = create_response.json()
    document_type_id = document_type["id"]
    assert document_type["active_version"] == 1

    versions_response = client.get(f"/api/document-types/{document_type_id}/versions")
    assert versions_response.status_code == 200
    assert versions_response.json()[0]["status"] == "ACTIVE"

    draft_response = client.post(
        f"/api/document-types/{document_type_id}/versions",
        json={
            "name": "Histórico Escolar Versionado",
            "retention_years": 10,
            "legal_hold": True,
            "access_policy": {"roles": ["auditor"]},
            "signature_rule": {"required": True, "minimum_signers": 2},
        },
    )
    assert draft_response.status_code == 200, draft_response.text
    assert draft_response.json()["version"] == 2
    assert draft_response.json()["status"] == "DRAFT"

    activate_response = client.post(
        f"/api/document-types/{document_type_id}/versions/2/activate"
    )
    assert activate_response.status_code == 200, activate_response.text
    assert activate_response.json()["status"] == "ACTIVE"

    current_response = client.get("/api/document-types")
    current = next(item for item in current_response.json()["items"] if item["id"] == document_type_id)
    assert current["active_version"] == 2
    assert current["retention_years"] == 10
    assert current["legal_hold"] is True
    assert current["access_policy"] == {"roles": ["auditor"]}
    assert current["signature_rule"] == {"required": True, "minimum_signers": 2}
