from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal

client = TestClient(app)


def create_test_institution(name: str, cnpj: str) -> str:
    response = client.post(
        "/api/institutions",
        json={
            "name": name,
            "cnpj": cnpj,
            "legal_name": f"{name} Ltda",
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()["id"]


def test_ocr_upload():
    from app.database import get_db
    from app.models_ged_config import DocumentType
    import uuid
    
    institution_id = create_test_institution(
        "IES OCR",
        "77.777.777/0001-77",
    )
    db = SessionLocal()
    doc_type_id = str(uuid.uuid4())
    doc_type = DocumentType(
        id=doc_type_id, 
        name="Documento de Identificação (RG)", 
        storage_area_id="dummy_area",
        storage_partition_id="dummy_partition",
        is_active=True
    )
    db.add(doc_type)
    db.commit()
    
    db.close()
        
    # 2. Upload de um arquivo mock via Scanner
    file_content = b"\xff\xd8fake image bytes representing an RG"
    
    upload_res = client.post(
        "/api/documents/upload",
        data={
            "title": "RG do Aluno",
            "document_type_id": doc_type_id,
            "indices_json": "[]"
        },
        files={"file": ("rg_falso.jpg", file_content, "image/jpeg")}
    )
    
    assert upload_res.status_code == 200, upload_res.json()
    res_json = upload_res.json()
    
    # Validar Status inicial de OCR (PENDENTE_VALIDACAO)
    assert res_json["status"] == "PENDENTE_VALIDACAO"


def test_upload_rejects_malware_eicar():
    from app.database import get_db
    from app.models_ged_config import DocumentType
    import uuid
    
    create_test_institution(
        "IES Antimalware",
        "88.888.888/0001-88",
    )
    db = SessionLocal()
    doc_type_id = str(uuid.uuid4())
    doc_type = DocumentType(
        id=doc_type_id, 
        name="Documento Fake", 
        storage_area_id="dummy_area",
        storage_partition_id="dummy_partition",
        is_active=True
    )
    db.add(doc_type)
    db.commit()
    
    db.close()
        
    eicar_content = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    
    upload_res = client.post(
        "/api/documents/upload",
        data={
            "title": "Arquivo EICAR",
            "document_type_id": doc_type_id,
            "indices_json": "[]"
        },
        files={"file": ("eicar.txt", eicar_content, "text/plain")}
    )
    
    assert upload_res.status_code == 200, upload_res.json()
    assert upload_res.json()["status"] == "QUARENTENA"
