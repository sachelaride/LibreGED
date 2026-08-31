import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_curriculo_xml_endpoint():
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "modelos", "curriculum escolar", "1.json")
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    response = client.post("/api/documents/curriculo/generate", json=payload)
    assert response.status_code == 200
    xml_output = response.json()["xml"]
    
    # Check namespaces and basic elements
    assert "<CurriculoEscolar" in xml_output
    assert "<infCurriculoEscolar versao=\"1.05\"" in xml_output
    assert "<DadosCurso>" in xml_output
    assert "<IesEmissora>" in xml_output
    
    # Check if capitalized recursive function worked
    assert "<NomeCurso>" in xml_output
    
    # Check list structures
    assert "<infEtiquetas>" in xml_output
    assert "<Etiqueta>" in xml_output
    assert "<infEstruturaCurricular>" in xml_output
    assert "<UnidadeCurricular>" in xml_output
    assert "<infCriteriosIntegralizacao>" in xml_output
    assert "<CriterioIntegralizacaoRotulos>" in xml_output
    
    # Check nested list within Categoria
    assert "<infEstruturaAtividadesComplementares>" in xml_output
    assert "<Categoria>" in xml_output
    assert "<Atividades>" in xml_output
    assert "<Atividade>" in xml_output
