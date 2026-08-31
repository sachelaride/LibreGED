import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_xsd_validation():
    # 1. Cadastra uma Categoria
    cat_res = client.post("/api/ged/categories", json={
        "index_code": "0099_xsd",
        "name": "Doc XSD",
        "description": "Teste"
    })
    
    if cat_res.status_code == 200:
        cat_id = cat_res.json()["id"]
    else:
        cat_id = "qualquer_coisa"
        
    # 2. Cria documento
    doc_res = client.post("/api/ged/documents", json={
        "title": "Diploma",
        "category_id": cat_id,
        "academic_phase": "DIPLOMACAO"
    })
    doc_id = doc_res.json()["id"]
    
    # 3. Dispara a validação XSD. O fallback vai tentar validar um XML que só tem <DadosAluno>, mas não tem <CPF> ou <DadosCurso>.
    # O mock_diploma.xsd EXIGE <CPF> e <DadosCurso>.
    val_res = client.post("/api/documents/validate-xsd", json={
        "document_id": doc_id,
        "xsd_filename": "mock_diploma.xsd"
    })
    
    # Esperamos que a validação falhe e retorne os erros (mesmo com HTTP 200 contendo valid: false)
    assert val_res.status_code == 200
    json_resp = val_res.json()
    assert json_resp["valid"] is False
    assert len(json_resp["errors"]) > 0
    
    # Verifica se os erros dizem algo sobre as tags faltando
    errors_str = " ".join(json_resp["errors"])
    assert "DadosCurso" in errors_str or "CPF" in errors_str
