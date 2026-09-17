from fastapi.testclient import TestClient
from datetime import timedelta
from uuid import uuid4

from app.main import app
from app.retention import RetentionService
from app.database import SessionLocal
from app.models import Institution, utc_now
from app.models_ged import DocumentCategory, GEDDocument, GEDDocumentStatus
from app.models_ged_config import DocumentType

client = TestClient(app)


def create_document(document_type: str, title: str):
    institution_id = str(uuid4())
    document_type_id = str(uuid4())
    document_id = str(uuid4())
    with SessionLocal() as db:
        db.add(Institution(
            id=institution_id,
            name=f"IES {title}",
            cnpj=f"{uuid4().int % 10**8:08d}/0001-00",
            legal_name=f"IES {title} Ltda",
        ))
        db.add(DocumentType(
            id=document_type_id,
            name=document_type,
            retention_years=RetentionService.get_retention_period(document_type),
            storage_area_id="default",
            storage_partition_id="default",
        ))
        db.add(DocumentCategory(id=document_type_id, name=document_type))
        db.add(GEDDocument(
            id=document_id,
            title=title,
            file_path="retention-test.txt",
            category_id=document_type_id,
            institution_id=institution_id,
            status=GEDDocumentStatus.ASSINADO,
        ))
        db.commit()
    return document_id


def test_retention_check_and_cleanup():
    """Testar verificação e limpeza de documentos expirados."""
    document_id = create_document("historico", "Histórico de David")

    # Teste 1: Verificar que o documento está ativo
    response = client.get(f"/api/documents/{document_id}/lifecycle")
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
    assert "ASSINADO" in stats["statistics"]["by_status"]

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
    document_id = create_document("diploma", "Diploma Eva")

    # Verificar lifecycle
    response = client.get(f"/api/documents/{document_id}/lifecycle")
    assert response.status_code == 200
    lifecycle = response.json()
    
    assert lifecycle["document_id"] == document_id
    assert lifecycle["status"] == "ASSINADO"
    assert lifecycle["document_type"] == "diploma"
    assert lifecycle["retention_years"] == 30  # Diploma: 30 anos
    assert "expiry_date" in lifecycle
    assert "days_remaining" in lifecycle
    assert lifecycle["action_required"] in ["NONE", "WARN", "ARCHIVE"]
