def test_create_dynamic_aspect_global(client, admin_token_headers):
    # Admin_global creating a global aspect
    response = client.post(
        "/api/ecm/dictionary/aspects",
        headers=admin_token_headers,
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
        headers=admin_token_headers,
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
    
def test_create_dynamic_aspect_institution(client, admin_instituicao_token_headers):
    # Admin_instituicao creating a local aspect
    response = client.post(
        "/api/ecm/dictionary/aspects",
        headers=admin_instituicao_token_headers,
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
