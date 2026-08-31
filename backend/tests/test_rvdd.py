import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_rvdd_html():
    # 1. Cria Categoria
    cat_res = client.post("/api/ged/categories", json={
        "index_code": "0100_rvdd",
        "name": "Doc RVDD",
        "description": "Teste"
    })
    
    if cat_res.status_code == 200:
        cat_id = cat_res.json()["id"]
    else:
        cat_id = "mock"
        
    # 2. Cria documento
    doc_res = client.post("/api/ged/documents", json={
        "title": "Diploma de João",
        "category_id": cat_id,
        "academic_phase": "DIPLOMACAO"
    })
    doc_id = doc_res.json()["id"]
    
    # 3. Chama RVDD
    res = client.get(f"/api/documents/{doc_id}/rvdd")
    
    assert res.status_code == 200
    html_content = res.text
    
    # Validações estruturais do HTML
    assert "República Federativa do Brasil" in html_content
    assert "João da Silva" in html_content # Injetado pelo rvdd_generator.py devido ao "João" no título
    assert "data:image/png;base64," in html_content # O QR Code foi gerado
    assert f"https://libreged.edu.br/validar/{doc_id}" in html_content
