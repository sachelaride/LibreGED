import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import User, Institution, Campus
from app.models_ged_config import DocumentType, UserDocumentType
from app.auth import get_password_hash
import uuid

client = TestClient(app)

def test_rbac_upload_forbidden():
    db_gen = app.dependency_overrides.get(get_db, get_db)()
    db = next(db_gen)
    
    inst_id = str(uuid.uuid4())
    inst = Institution(id=inst_id, name="Inst Teste", cnpj="12345678901234", legal_name="Inst Teste")
    db.add(inst)
    
    campus_id = str(uuid.uuid4())
    campus = Campus(id=campus_id, institution_id=inst_id, name="Campus Teste")
    db.add(campus)
    
    doc_type_id = str(uuid.uuid4())
    doc_type = DocumentType(id=doc_type_id, name="Doc Restrito", storage_area_id="dummy_area", storage_partition_id="dummy_partition")
    db.add(doc_type)
    
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id, 
        username="teste_rbac", 
        hashed_password=get_password_hash("123"), 
        role="academico",
        institution_id=inst_id,
        campus_id=campus_id
    )
    db.add(user)
    db.commit()

    try:
        next(db_gen)
    except StopIteration:
        pass
        
    from app.auth import get_current_active_user
    
    # Temporarily clear the global override in conftest.py
    old_override = app.dependency_overrides.get(get_current_active_user)
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]
        
    login_data = {"username": "teste_rbac", "password": "123"}
    res = client.post("/api/auth/token", data=login_data)
    assert res.status_code == 200
    token = res.json()["access_token"]
    
    file_content = b"\xff\xd8fake image"
    upload_res = client.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "Documento Teste",
            "document_type_id": doc_type_id,
            "indices_json": "[]"
        },
        files={"file": ("fake.jpg", file_content, "image/jpeg")}
    )
    
    # Restore the override
    if old_override:
        app.dependency_overrides[get_current_active_user] = old_override
        
    assert upload_res.status_code == 403
    assert upload_res.json()["detail"] == "Document type access forbidden"
