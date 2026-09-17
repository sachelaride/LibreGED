from uuid import uuid4

from fastapi.testclient import TestClient
from app.auth import get_current_active_user
from app.database import SessionLocal
from app.models import Institution, User
from app.main import app

client = TestClient(app)


def test_create_dynamic_aspect_global():
    # Admin_global creating a global aspect
    response = client.post(
        "/api/ecm/dictionary/aspects",
        json={
            "name": "custom:financeiro",
            "title": "Financeiro",
            "description": "Metadados financeiros",
            "is_global": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "custom:financeiro"
    assert data["institution_id"] is None
    
    aspect_id = data["id"]
    
    # Add a property to it
    prop_response = client.post(
        f"/api/ecm/dictionary/aspects/{aspect_id}/properties",
        json={
            "name": "custom:valor",
            "title": "Valor R$",
            "data_type": "float",
            "required": True
        }
    )
    assert prop_response.status_code == 200
    prop_data = prop_response.json()
    assert prop_data["name"] == "custom:valor"
    assert prop_data["data_type"] == "float"
    
def test_create_dynamic_aspect_institution():
    # Admin_instituicao creating a local aspect
    institution_id = str(uuid4())
    with SessionLocal() as db:
        db.add(Institution(
            id=institution_id,
            name="IES ECM",
            cnpj="91.000.000/0001-00",
            legal_name="IES ECM Ltda",
        ))
        db.add(User(
            id=str(uuid4()),
            username="ecm_admin",
            hashed_password="teste",
            role="admin_instituicao",
            institution_id=institution_id,
        ))
        db.commit()

    app.dependency_overrides[get_current_active_user] = lambda: User(
        id="ecm-admin-test",
        username="ecm_admin",
        hashed_password="teste",
        role="admin_instituicao",
        institution_id=institution_id,
    )
    response = client.post(
        "/api/ecm/dictionary/aspects",
        json={
            "name": "custom:local",
            "title": "Local Aspect",
            "is_global": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "custom:local"
    assert data["institution_id"] is not None
