import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import engine, get_db
from app.models import Base
from sqlalchemy.orm import sessionmaker
from app import models
from app.auth import get_password_hash, create_access_token
from datetime import timedelta

# ... keep imports ...

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    inst_id = "test-admin-inst"
    db.add(models.Institution(id=inst_id, name="Test Inst", cnpj="000", legal_name="Test Inst"))
    
    db.add(models.User(
        id="admin-inst",
        username="admin_inst",
        hashed_password=get_password_hash("test"),
        role="admin_instituicao",
        institution_id=inst_id
    ))
    
    db.add(models.User(
        id="user-inst",
        username="user_inst",
        hashed_password=get_password_hash("test"),
        role="recepcao",
        institution_id=inst_id
    ))
    
    db.commit()
    db.close()
    
    yield
    Base.metadata.drop_all(bind=engine)

def override_admin_inst():
    return models.User(
        id="admin-inst",
        username="admin_inst",
        role="admin_instituicao",
        institution_id="test-admin-inst"
    )

def test_admin_instituicao_can_access_admin_api():
    from app.auth import get_current_active_user
    app.dependency_overrides[get_current_active_user] = override_admin_inst
    
    headers = {}
    
    res = client.get("/api/admin/settings", headers=headers)
    print("RESPONSE JSON:", res.json())
    assert res.status_code == 200, res.text
    assert res.json()["max_upload_size_mb"] == 10
    
    res = client.put("/api/admin/settings", headers=headers, json={
        "max_upload_size_mb": 50,
        "allowed_mime_types": "application/pdf"
    })
    assert res.status_code == 200
    assert res.json()["max_upload_size_mb"] == 50

def override_recepcao():
    return models.User(
        id="user-inst",
        username="user_inst",
        role="recepcao",
        institution_id="test-admin-inst"
    )

def test_recepcao_cannot_access_admin_api():
    from app.auth import get_current_active_user
    app.dependency_overrides[get_current_active_user] = override_recepcao
    
    headers = {}
    
    res = client.get("/api/admin/settings", headers=headers)
    assert res.status_code == 403, res.text
    assert res.json()["detail"] == "Operation not permitted"
