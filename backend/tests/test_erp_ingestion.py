import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Institution

client = TestClient(app)


def test_connector_status_contract():
    res = client.get("/api/integration/erp/connector/status")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] in {"RECEIVED", "QUEUED", "PROCESSING", "ACCEPTED", "REJECTED", "DUPLICATE", "FAILED", "COMPLETED"}
    assert payload["source_system"] == "erp-connector"
    assert payload["message"]


def test_erp_ingestion_idempotency():
    with SessionLocal() as db:
        db.add(Institution(
            id="inst-123",
            name="IES ERP",
            cnpj="21.000.000/0001-00",
            legal_name="IES ERP Ltda",
        ))
        db.commit()

    payload = {
        "aluno": {
            "nome": "Maria Silva",
            "cpf": "123.456.789-01",
            "matricula": "2020101",
            "curso": {
                "codigo_mec": "12345",
                "nome": "Direito",
                "carga_horaria": 4000,
                "modalidade": "EAD"
            }
        },
        "data_conclusao": "2024-12-15",
        "institution_id": "inst-123"
    }
    
    headers = {
        "X-Idempotency-Key": "req_xyz_999",
        "X-Correlation-Id": "batch_456",
        "X-Source-System": "TOTVS_RM_v12"
    }
    
    # 1. Primeira Requisição (Deve Processar)
    res1 = client.post("/api/integration/erp/ingest", json=payload, headers=headers)
    assert res1.status_code == 200
    json1 = res1.json()
    assert json1["status"] == "QUEUED"
    doc_id1 = json1["document_id"]
    
    # 2. Segunda Requisição IDÊNTICA (Deve retornar CACHE / Ignorar)
    res2 = client.post("/api/integration/erp/ingest", json=payload, headers=headers)
    assert res2.status_code == 200
    json2 = res2.json()
    assert json2["status"] == "IDEMPOTENT_CACHE"
    # O document ID retornado tem que ser exatamente o mesmo gerado na primeira execução
    assert json2["document_id"] == doc_id1
