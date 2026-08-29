from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_document_upload_and_audit():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Teste",
            "cnpj": "12.345.678/0001-99",
            "legal_name": "IES Teste Ltda",
        },
    ).json()

    student = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Ana Souza",
            "birth_date": "2010-01-10",
            "cpf": "11122233344",
            "email": "ana@email.com",
        },
    ).json()

    enrollment = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "course_name": "Ensino Fundamental II",
            "class_name": "8B",
            "year": 2026,
            "status": "active",
        },
    ).json()

    document = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "enrollment_id": enrollment["id"],
            "document_type": "historico",
            "title": "Histórico escolar",
            "status": "pending",
        },
    ).json()

    response = client.post(
        f"/api/documents/{document['id']}/upload",
        files={"file": ("historico.txt", b"conteudo do historico escolar", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == document["id"]
    assert payload["version"]["file_name"] == "historico.txt"

    audit = client.get("/api/audit")
    assert audit.status_code == 200
    assert len(audit.json()) > 0


def test_generate_xml_and_search_documents():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES XML",
            "cnpj": "10.000.000/0001-00",
            "legal_name": "IES XML Ltda",
        },
    ).json()

    student = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Bruno Pereira",
            "birth_date": "2011-07-22",
            "cpf": "22233344455",
            "email": "bruno@email.com",
        },
    ).json()

    enrollment = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "course_name": "Ensino Fundamental V",
            "class_name": "9A",
            "year": 2026,
            "status": "active",
        },
    ).json()

    document = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "enrollment_id": enrollment["id"],
            "document_type": "contrato",
            "title": "Contrato de matrícula",
            "status": "pending",
        },
    ).json()

    schema = client.post(
        "/api/schema-versions",
        json={
            "code": "contrato-1.0",
            "document_type": "contrato",
            "namespace": "https://example.org/contrato/1.0",
            "xsd_hash": "a" * 64,
            "status": "approved",
            "valid_from": "2020-01-01T00:00:00",
            "environment": "homologation",
        },
    )
    assert schema.status_code == 201

    xml_response = client.post(
        f"/api/documents/{document['id']}/xml",
        json={
            "student_name": "Bruno Pereira",
            "course_name": "Ensino Fundamental V",
            "status": "pending",
            "document_type": "contrato",
            "schema_version": "contrato-1.0",
            "namespace": "https://example.org/contrato/1.0",
        },
    )

    assert xml_response.status_code == 200
    xml_body = xml_response.json()["xml"]
    assert "<documento" in xml_body.lower()
    assert "Bruno Pereira" in xml_body
    assert xml_response.json()["schema_version"] == "contrato-1.0"

    search_response = client.get("/api/documents/search", params={"student_id": student["id"]})
    assert search_response.status_code == 200
    payload = search_response.json()
    assert len(payload) >= 1
    assert payload[0]["title"] == "Contrato de matrícula"


def test_generate_visual_representation_and_retention_policy():
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Visual",
            "cnpj": "11.111.111/0001-11",
            "legal_name": "IES Visual Ltda",
        },
    ).json()

    student = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Carla Mendes",
            "birth_date": "2012-03-12",
            "cpf": "33344455566",
            "email": "carla@email.com",
        },
    ).json()

    enrollment = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "course_name": "Ensino Médio",
            "class_name": "2A",
            "year": 2026,
            "status": "active",
        },
    ).json()

    document = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "enrollment_id": enrollment["id"],
            "document_type": "historico",
            "title": "Histórico de notas",
            "status": "validated",
        },
    ).json()

    representation_response = client.post(f"/api/documents/{document['id']}/representation")
    assert representation_response.status_code == 200
    representation = representation_response.json()
    assert representation["document_id"] == document["id"]
    assert "Carla Mendes" in representation["summary"]
    assert representation["visual_type"] == "academic-card"

    retention_response = client.get(f"/api/documents/{document['id']}/retention")
    assert retention_response.status_code == 200
    retention = retention_response.json()
    assert retention["document_id"] == document["id"]
    assert retention["retention_years"] >= 5
    assert retention["status"] == "active"
