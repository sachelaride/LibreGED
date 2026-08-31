import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_historico_xml_endpoint():
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "modelos", "historico", "023.15729.json")
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    response = client.post("/api/documents/historico/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "xml" in data
    
    xml_output = data["xml"]
    
    # Check if basic namespaces and root elements exist
    assert "<DocumentoHistoricoEscolarFinal" in xml_output
    assert "xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"" in xml_output
    assert "<infHistoricoEscolar versao=\"1.05\">" in xml_output
    assert "<Aluno>" in xml_output
    assert "<Nome>LUANA MARCHIORETTO</Nome>" in xml_output
