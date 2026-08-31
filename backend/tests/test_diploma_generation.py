import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_diploma_xml_endpoint():
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "modelos", "diplomas", "301.1973.json")
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Test Diplomado (Public)
    response = client.post("/api/documents/diploma/generate", json=payload)
    assert response.status_code == 200
    xml_output = response.json()["xml"]
    
    # Check namespaces and basic elements
    assert "<Diploma" in xml_output
    assert "<infDiploma versao=\"1.05\"" in xml_output
    assert "<Diplomado>" in xml_output
    assert "<Nome>LARISSA BIFARONI BALASSO</Nome>" in xml_output
    # Ensure private elements are NOT in this XML
    assert "<DadosPrivadosDiplomado>" not in xml_output

    # Test Institucional (Registro)
    response_acad = client.post("/api/documents/academico/generate", json=payload)
    assert response_acad.status_code == 200
    xml_output_acad = response_acad.json()["xml"]
    
    # Check namespaces and basic elements
    assert "<DocumentacaoAcademicaRegistro" in xml_output_acad
    assert "<RegistroReq versao=\"1.05\"" in xml_output_acad
    # Ensure private elements ARE in this XML
    assert "<DadosPrivadosDiplomado>" in xml_output_acad
    assert "<TermoResponsabilidadeEmissora>" in xml_output_acad
