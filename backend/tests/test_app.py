from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_institution():
    response = client.post(
        "/api/institutions",
        json={
            "name": "IES Teste",
            "cnpj": "12.345.678/0001-99",
            "legal_name": "IES Teste Ltda",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "IES Teste"
    assert payload["cnpj"] == "12.345.678/0001-99"


def test_create_student_guardian_enrollment_and_document():
    institution_response = client.post(
        "/api/institutions",
        json={
            "name": "IES Teste",
            "cnpj": "12.345.678/0001-99",
            "legal_name": "IES Teste Ltda",
        },
    )
    institution_id = institution_response.json()["id"]

    student_response = client.post(
        "/api/students",
        json={
            "institution_id": institution_id,
            "full_name": "Maria da Silva",
            "birth_date": "2008-03-15",
            "cpf": "12345678901",
            "email": "maria@email.com",
        },
    )
    assert student_response.status_code == 200
    student_id = student_response.json()["id"]

    guardian_response = client.post(
        f"/api/students/{student_id}/guardians",
        json={
            "full_name": "João da Silva",
            "cpf": "10987654321",
            "email": "joao@email.com",
            "relationship_type": "pai",
        },
    )
    assert guardian_response.status_code == 200
    assert guardian_response.json()["student_id"] == student_id

    enrollment_response = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution_id,
            "student_id": student_id,
            "course_name": "Ensino Fundamental I",
            "class_name": "5A",
            "year": 2026,
            "status": "active",
        },
    )
    assert enrollment_response.status_code == 200
    enrollment = enrollment_response.json()
    assert enrollment["student_id"] == student_id
    assert enrollment["course_name"] == "Ensino Fundamental I"

    document_response = client.post(
        "/api/documents",
        json={
            "institution_id": institution_id,
            "student_id": student_id,
            "enrollment_id": enrollment["id"],
            "document_type": "matricula",
            "title": "Contrato de matrícula",
            "status": "pending",
        },
    )
    assert document_response.status_code == 200
    document = document_response.json()
    assert document["title"] == "Contrato de matrícula"
    assert document["student_id"] == student_id
