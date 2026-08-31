import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_erp_ingestion_idempotency():
    payload = {
        "aluno": {
            "nome": "Maria Silva",
            "cpf": "123.456.789-01",
            "matricula": "2020101",
            "curso": {
                "codigo_mec": "12345",
                "nome": "Direito",
                "carga_horaria": 4000
            }
        },
        "data_conclusao": "2024-12-15"
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
    assert json1["status"] == "PROCESSED"
    doc_id1 = json1["document_id"]
    
    # 2. Segunda Requisição IDÊNTICA (Deve retornar CACHE / Ignorar)
    res2 = client.post("/api/integration/erp/ingest", json=payload, headers=headers)
    assert res2.status_code == 200
    json2 = res2.json()
    assert json2["status"] == "IDEMPOTENT_CACHE"
    # O document ID retornado tem que ser exatamente o mesmo gerado na primeira execução
    assert json2["document_id"] == doc_id1
