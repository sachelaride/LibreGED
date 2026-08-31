import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ged_state_machine():
    # 1. Create category
    cat_payload = {
        "name": "Comprovante de Residência",
        "description": "Documentos de endereço"
    }
    cat_res = client.post("/api/ged/categories", json=cat_payload)
    assert cat_res.status_code == 200
    cat_id = cat_res.json()["id"]
    
    # 2. Create document (Starts as RASCUNHO)
    doc_payload = {
        "title": "Conta de Luz - João",
        "category_id": cat_id,
        "academic_phase": "MATRICULA"
    }
    doc_res = client.post("/api/ged/documents", json=doc_payload)
    assert doc_res.status_code == 200
    doc_id = doc_res.json()["id"]
    assert doc_res.json()["status"] == "RASCUNHO"
    
    # 3. Transition to PENDENTE_VALIDACAO
    trans_payload = {
        "status": "PENDENTE_VALIDACAO",
        "comments": "Enviado pelo portal do aluno"
    }
    t1_res = client.patch(f"/api/ged/documents/{doc_id}/status", json=trans_payload)
    assert t1_res.status_code == 200
    assert t1_res.json()["from_status"] == "RASCUNHO"
    assert t1_res.json()["to_status"] == "PENDENTE_VALIDACAO"
    
    # 4. Transition to REJEITADO
    t2_res = client.patch(f"/api/ged/documents/{doc_id}/status", json={
        "status": "REJEITADO",
        "comments": "Foto borrada"
    })
    assert t2_res.status_code == 200
    assert t2_res.json()["to_status"] == "REJEITADO"
    
    # 5. Invalid Transition to ASSINADO
    t3_res = client.patch(f"/api/ged/documents/{doc_id}/status", json={
        "status": "ASSINADO"
    })
    assert t3_res.status_code == 400
    assert "Não é possível transicionar" in t3_res.json()["detail"]
