import uuid

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models_ged_config import DocumentType
from app.xsd_validator import validate_xml_against_xsd


client = TestClient(app)


def test_xsd_validation():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES XSD",
            "cnpj": "63.000.000/0001-00",
            "legal_name": "IES XSD Ltda",
        },
    )
    assert institution.status_code == 200, institution.json()

    document_type_id = str(uuid.uuid4())
    db = SessionLocal()
    db.add(
        DocumentType(
            id=document_type_id,
            name="Documento XSD",
            storage_area_id="dummy_area",
            storage_partition_id="dummy_partition",
            is_active=True,
        )
    )
    db.commit()
    db.close()

    schema = client.post(
        "/api/xsd",
        json={
            "document_type_id": document_type_id,
            "code": "mock_diploma",
            "namespace": "https://example.org/diploma/1",
            "xsd_hash": "b" * 64,
            "environment": "homologation",
        },
    )
    assert schema.status_code == 200, schema.json()
    approved = client.post(f"/api/xsd/{schema.json()['id']}/approve")
    assert approved.status_code == 200, approved.json()

    validation = client.post(
        "/api/xsd/validator",
        json={
            "xml_content": "<DadosAluno/>",
            "document_type_code": "mock_diploma",
            "environment": "homologation",
        },
    )

    assert validation.status_code == 200, validation.json()
    result = validation.json()
    assert result["valid"] is False
    assert result["errors"]


def test_official_history_v105_validator_uses_local_schema_bundle():
    response = client.post(
        "/api/xsd/validator/historico/v1.05",
        json={"xml_content": "<InvalidHistory/>"},
    )

    assert response.status_code == 200, response.json()
    result = response.json()
    assert result["schema_code"] == "HistoricoEscolarDigital_v1.05"
    assert result["valid"] is False
    assert any("No matching global declaration" in error for error in result["errors"])


def test_xsd_validator_rejects_paths_outside_the_schema_directory():
    valid, errors = validate_xml_against_xsd("<Invalid/>", "../mock_diploma.xsd")

    assert valid is False
    assert errors == ["Schema path must remain inside the XSD directory"]
