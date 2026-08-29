from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_advanced_search_documents():
    """Testar busca avançada com filtros múltiplos."""
    # Criar instituição
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Búsca",
            "cnpj": "20.000.000/0001-00",
            "legal_name": "IES Búsca Ltda",
        },
    ).json()

    # Criar dois alunos
    student1 = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Carlos Silva",
            "birth_date": "2010-05-15",
            "cpf": "44455566677",
            "email": "carlos@email.com",
        },
    ).json()

    student2 = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Ana Rosa",
            "birth_date": "2011-06-20",
            "cpf": "55566677788",
            "email": "ana@email.com",
        },
    ).json()

    # Criar matrículas
    enrollment1 = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution["id"],
            "student_id": student1["id"],
            "course_name": "Ensino Médio",
            "class_name": "3A",
            "year": 2026,
            "status": "active",
        },
    ).json()

    enrollment2 = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution["id"],
            "student_id": student2["id"],
            "course_name": "Fundamental II",
            "class_name": "9B",
            "year": 2026,
            "status": "active",
        },
    ).json()

    # Criar documentos
    doc1 = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student1["id"],
            "enrollment_id": enrollment1["id"],
            "document_type": "diploma",
            "title": "Diploma Ensino Médio 2024",
            "status": "signed",
        },
    ).json()

    doc2 = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student1["id"],
            "enrollment_id": enrollment1["id"],
            "document_type": "historico",
            "title": "Histórico Carlos 2024",
            "status": "validated",
        },
    ).json()

    doc3 = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student2["id"],
            "enrollment_id": enrollment2["id"],
            "document_type": "diploma",
            "title": "Diploma Fundamental II",
            "status": "pending",
        },
    ).json()

    # Teste 1: Buscar por nome do aluno
    response = client.post(
        "/api/documents/advanced-search",
        json={"student_name": "Carlos Silva"},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 2  # Carlos tem 2 documentos
    assert any("Carlos" in r.get("student_name", "") for r in results)

    # Teste 2: Buscar por tipo de documento
    response = client.post(
        "/api/documents/advanced-search",
        json={"document_type": "diploma"},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 2  # 2 diplomas (um signed, um pending)

    # Teste 3: Buscar por status
    response = client.post(
        "/api/documents/advanced-search",
        json={"status": "signed"},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert all(r.get("status") == "signed" for r in results)

    # Teste 4: Buscar combinado (aluno + tipo)
    response = client.post(
        "/api/documents/advanced-search",
        json={
            "student_name": "Carlos Silva",
            "document_type": "historico",
        },
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert any(r.get("document_type") == "historico" for r in results)

    # Teste 5: Buscar com query full-text
    response = client.post(
        "/api/documents/advanced-search",
        json={"query": "Carlos"},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1

    # Teste 6: Buscar por instituição
    response = client.post(
        "/api/documents/advanced-search",
        json={"institution_id": institution["id"]},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 3  # Todos os 3 documentos
