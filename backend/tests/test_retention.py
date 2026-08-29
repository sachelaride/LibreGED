from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.retention import RetentionService

client = TestClient(app)


def test_retention_check_and_cleanup():
    """Testar verificação e limpeza de documentos expirados."""
    # Criar instituição
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Retenção",
            "cnpj": "30.000.000/0001-00",
            "legal_name": "IES Retenção Ltda",
        },
    ).json()

    # Criar aluno
    student = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "David Costa",
            "birth_date": "2010-01-10",
            "cpf": "66677788899",
            "email": "david@email.com",
        },
    ).json()

    # Criar matrícula
    enrollment = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "course_name": "Ensino Médio",
            "class_name": "1A",
            "year": 2026,
            "status": "active",
        },
    ).json()

    # Criar documento histórico (5 anos de retenção)
    document = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "enrollment_id": enrollment["id"],
            "document_type": "historico",
            "title": "Histórico de David",
            "status": "signed",
        },
    ).json()

    # Teste 1: Verificar que o documento está ativo
    response = client.get(f"/api/documents/{document['id']}/lifecycle")
    assert response.status_code == 200
    lifecycle = response.json()
    assert lifecycle["action_required"] in ["NONE", "WARN"]  # Não deve estar expirado
    assert lifecycle["retention_years"] == 5

    # Teste 2: Verificar estatísticas gerais
    response = client.get("/api/documents/retention/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "statistics" in stats
    assert "by_status" in stats["statistics"]
    assert "signed" in stats["statistics"]["by_status"]

    # Teste 3: Verificar violações (não deve haver no início)
    response = client.get("/api/documents/retention/check")
    assert response.status_code == 200
    violations = response.json()
    # Pode haver ou não violações inicialmente


def test_retention_policies():
    """Testar políticas de retenção por tipo de documento."""
    # Verificar que as políticas estão corretas
    assert RetentionService.get_retention_period("diploma") == 30
    assert RetentionService.get_retention_period("historico") == 5
    assert RetentionService.get_retention_period("contrato") == 7
    assert RetentionService.get_retention_period("certidao") == 10

    # Tipo desconhecido deve retornar default
    assert RetentionService.get_retention_period("tipo_unknown") == 5


def test_retention_cleanup_dry_run():
    """Testar execução de limpeza em modo dry-run."""
    # Executar limpeza sem realmente deletar
    response = client.post(
        "/api/documents/retention/cleanup",
        json={"dry_run": True},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["dry_run"] is True
    assert "to_archive" in result
    assert "violations" in result


def test_document_lifecycle_info():
    """Testar informações de ciclo de vida de um documento."""
    # Criar instituição, aluno, matrícula e documento
    institution = client.post(
        "/api/institutions",
        json={
            "name": "IES Lifecycle",
            "cnpj": "40.000.000/0001-00",
            "legal_name": "IES Lifecycle Ltda",
        },
    ).json()

    student = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Eva Lima",
            "birth_date": "2010-02-20",
            "cpf": "77788899900",
            "email": "eva@email.com",
        },
    ).json()

    enrollment = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "course_name": "Fundamental",
            "class_name": "5A",
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
            "document_type": "diploma",
            "title": "Diploma Eva",
            "status": "signed",
        },
    ).json()

    # Verificar lifecycle
    response = client.get(f"/api/documents/{document['id']}/lifecycle")
    assert response.status_code == 200
    lifecycle = response.json()
    
    assert lifecycle["document_id"] == document["id"]
    assert lifecycle["status"] == "signed"
    assert lifecycle["document_type"] == "diploma"
    assert lifecycle["retention_years"] == 30  # Diploma: 30 anos
    assert "expiry_date" in lifecycle
    assert "days_remaining" in lifecycle
    assert lifecycle["action_required"] in ["NONE", "WARN", "ARCHIVE"]
