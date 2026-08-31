import pytest
from app.academic_validator import validate_documents, ValidationRequest
from app.schemas_diploma import Model as DiplomaPayload, DadosDiploma, Diplomado, DadosCurso as DipDadosCurso
from app.schemas_historico import Model as HistoricoPayload, DocumentoHistoricoEscolarFinal, Aluno, DadosCurso as HistDadosCurso, HistoricoEscolar, CargaHorariaCursoIntegralizada
from app.schemas_curriculo import Model as CurriculoPayload, CriterioIntegralizacaoRotulo, CargasHorariasCriterio, DadosCurso as CurrDadosCurso

def get_mocked_diploma(cpf="12345678900", cod_curso="1001"):
    # This is a heavily simplified mock just to pass the Pydantic type checks and attributes.
    # To keep it simple, we use a simple MagicMock-like struct or construct partial pydantic models
    # if required. But since the schemas are strict, we should build valid pydantic objects.
    pass

# We can also test the endpoint using TestClient by loading the JSON files from `modelos`.
import json
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_validate_academic_documents_endpoint():
    # Load the 3 JSON models
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "modelos")
    
    dip_path = os.path.join(base_dir, "diplomas", "301.1973.json")
    hist_path = os.path.join(base_dir, "historico", "023.15729.json")
    curr_path = os.path.join(base_dir, "curriculum escolar", "1.json")
    
    with open(dip_path, "r", encoding="utf-8") as f:
        dip_json = json.load(f)
    with open(hist_path, "r", encoding="utf-8") as f:
        hist_json = json.load(f)
    with open(curr_path, "r", encoding="utf-8") as f:
        curr_json = json.load(f)
        
    payload = {
        "diploma": dip_json,
        "historico": hist_json,
        "curriculo": curr_json
    }
    
    # Send to the validation endpoint
    response = client.post("/api/documents/validate", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    # It might return some errors because these 3 JSON files belong to different sample students
    # But it shouldn't crash!
    assert "valid" in data
    assert "errors" in data
    
    # Now let's test a scenario where we force them to match
    # CPF from diploma
    cpf = dip_json["dadosDiploma"]["diplomado"]["cpf"]
    hist_json["documentoHistoricoEscolarFinal"]["aluno"]["cpf"] = cpf
    
    # Codigo Curso from diploma
    cod = dip_json["dadosDiploma"]["dadosCurso"]["codigoCursoEMEC"]
    hist_json["documentoHistoricoEscolarFinal"]["dadosCurso"]["codigoCursoEMEC"] = cod
    curr_json["dadosCurso"]["codigoCursoEMEC"] = cod
    
    # Hours (make historico larger than curr)
    hist_json["documentoHistoricoEscolarFinal"]["historicoEscolar"]["cargaHorariaCursoIntegralizada"]["cargaHorariaIntegralizadaHoraRelogio"] = "9999"
    
    payload_valid = {
        "diploma": dip_json,
        "historico": hist_json,
        "curriculo": curr_json
    }
    
    response_valid = client.post("/api/documents/validate", json=payload_valid)
    assert response_valid.status_code == 200
    assert response_valid.json()["valid"] == True
    assert len(response_valid.json()["errors"]) == 0
