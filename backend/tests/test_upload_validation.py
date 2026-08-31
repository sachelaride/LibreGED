import pytest
import os
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ocr_upload():
    # 1. Criar Categoria "0001 - RG"
    cat_payload = {
        "index_code": "0001",
        "name": "Documento de Identificação (RG)",
        "description": "RG ou CNH",
        "is_active": True
    }
    cat_res = client.post("/api/ged/categories", json=cat_payload)
    
    # We might have conflict if DB isn't clean, but let's assume conftest cleans it
    if cat_res.status_code != 200 and cat_res.status_code != 409: # 409 if exists
        assert cat_res.status_code == 200
        
    # 2. Upload de um arquivo mock via Scanner
    file_content = b"fake image bytes representing an RG"
    
    upload_res = client.post(
        "/api/ged/documents/upload",
        data={
            "title": "RG do Aluno",
            "category_code": "0001",
            "academic_phase": "MATRICULA",
            "student_id": "12345"
        },
        files={"file": ("rg_falso.jpg", file_content, "image/jpeg")}
    )
    
    assert upload_res.status_code == 200
    res_json = upload_res.json()
    
    # Validar Status inicial de OCR (PENDENTE_VALIDACAO)
    assert res_json["status"] == "PENDENTE_VALIDACAO"
    
    # Validar se o metadado JSON da IA foi salvo
    assert res_json["extracted_metadata"] is not None
    
    metadata = json.loads(res_json["extracted_metadata"])
    assert metadata["document_is_valid"] is True
    assert metadata["extracted_fields"]["cpf"] == "123.456.789-00"
