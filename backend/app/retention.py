from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import List, Dict
from sqlalchemy.orm import Session

from app import models


class DocumentLifecycle(str, Enum):
    """Estados do ciclo de vida de um documento."""
    DRAFT = "draft"
    PENDING = "pending"
    VALIDATED = "validated"
    SIGNED = "signed"
    ARCHIVED = "archived"
    DELETED = "deleted"


# Política de retenção por tipo de documento (em anos)
RETENTION_POLICIES: Dict[str, int] = {
    "diploma": 30,  # Indefinido, manter por 30 anos
    "historico": 5,  # Lei 9.394/96 (LDB) - 5 anos
    "contrato": 7,  # Lei 8.078/90 (CDC) - 7 anos
    "certidao": 10,  # Documentos certificados - 10 anos
    "declaracao": 3,  # Declarações simples - 3 anos
    "comprovante": 3,  # Comprovantes - 3 anos
}

# Política default se tipo não estiver listado
DEFAULT_RETENTION_YEARS = 5


class RetentionService:
    """Gerenciador de ciclo de vida de documentos acadêmicos."""

    @staticmethod
    def get_retention_period(document_type: str) -> int:
        """Obter período de retenção em anos para um tipo de documento."""
        return RETENTION_POLICIES.get(document_type, DEFAULT_RETENTION_YEARS)

    @staticmethod
    def calculate_expiry_date(created_at: datetime, document_type: str) -> datetime:
        """Calcular data de expiração baseado no tipo e data de criação."""
        retention_years = RetentionService.get_retention_period(document_type)
        return created_at + timedelta(days=365 * retention_years)

    @staticmethod
    def mark_for_archival(db: Session, document_id: str, reason: str = "retenção expirada") -> bool:
        """Marcar documento para arquivamento."""
        document = db.query(models.Document).filter(models.Document.id == document_id).first()
        if document is None:
            return False

        # Só arquivar se já estava validado/assinado
        if document.status not in ["validated", "signed"]:
            return False

        document.status = "archived"
        db.commit()

        # Auditoria
        audit = models.AuditEvent(
            id=str(len(db.query(models.AuditEvent).all()) + 1),
            document_id=document_id,
            entity="document",
            entity_id=document_id,
            action="archived",
            details=f"Documento arquivado: {reason}",
        )
        db.add(audit)
        db.commit()

        return True

    @staticmethod
    def check_retention_compliance(db: Session) -> List[Dict]:
        """Verificar quais documentos violam a política de retenção."""
        violations = []
        now = datetime.now(UTC).replace(tzinfo=None)

        for doc in db.query(models.Document).all():
            if doc.status in ["draft", "pending", "rejected"]:
                # Documentos não finalizados não contam para retenção
                continue

            expiry_date = RetentionService.calculate_expiry_date(doc.created_at, doc.document_type)
            days_until_expiry = (expiry_date - now).days

            if days_until_expiry < 0:
                # Documento expirou e deve ser arquivado
                violations.append({
                    "document_id": doc.id,
                    "student_name": db.query(models.Student).filter(models.Student.id == doc.student_id).first().full_name if db.query(models.Student).filter(models.Student.id == doc.student_id).first() else "Unknown",
                    "document_type": doc.document_type,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat(),
                    "expiry_date": expiry_date.isoformat(),
                    "days_overdue": abs(days_until_expiry),
                    "action": "ARCHIVE",
                })
            elif days_until_expiry < 30:
                # Documento vai expirar em menos de 30 dias
                violations.append({
                    "document_id": doc.id,
                    "student_name": db.query(models.Student).filter(models.Student.id == doc.student_id).first().full_name if db.query(models.Student).filter(models.Student.id == doc.student_id).first() else "Unknown",
                    "document_type": doc.document_type,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat(),
                    "expiry_date": expiry_date.isoformat(),
                    "days_until_expiry": days_until_expiry,
                    "action": "WARN",
                })

        return violations

    @staticmethod
    def execute_retention_cleanup(db: Session, dry_run: bool = True) -> Dict:
        """Executar limpeza de documentos expirados."""
        violations = RetentionService.check_retention_compliance(db)
        archived_count = 0
        warned_count = 0

        for violation in violations:
            if violation["action"] == "ARCHIVE":
                if not dry_run:
                    RetentionService.mark_for_archival(
                        db,
                        violation["document_id"],
                        reason=f"Retenção expirada em {violation['days_overdue']} dias"
                    )
                archived_count += 1
            elif violation["action"] == "WARN":
                warned_count += 1

        return {
            "dry_run": dry_run,
            "total_violations": len(violations),
            "to_archive": archived_count,
            "warnings": warned_count,
            "violations": violations,
        }

    @staticmethod
    def get_lifecycle_statistics(db: Session) -> Dict:
        """Obter estatísticas sobre o ciclo de vida dos documentos."""
        stats = {
            "by_status": {},
            "by_type": {},
            "by_retention_status": {
                "active": 0,
                "expiring_soon": 0,
                "expired": 0,
                "archived": 0,
            },
        }

        now = datetime.now(UTC).replace(tzinfo=None)

        for doc in db.query(models.Document).all():
            # Por status
            status = doc.status
            if status not in stats["by_status"]:
                stats["by_status"][status] = 0
            stats["by_status"][status] += 1

            # Por tipo
            doc_type = doc.document_type
            if doc_type not in stats["by_type"]:
                stats["by_type"][doc_type] = 0
            stats["by_type"][doc_type] += 1

            # Por estado de retenção
            if doc.status == "archived":
                stats["by_retention_status"]["archived"] += 1
            elif doc.status in ["draft", "pending", "rejected"]:
                # Não contam
                pass
            else:
                expiry_date = RetentionService.calculate_expiry_date(doc.created_at, doc.document_type)
                days_until_expiry = (expiry_date - now).days

                if days_until_expiry < 0:
                    stats["by_retention_status"]["expired"] += 1
                elif days_until_expiry < 30:
                    stats["by_retention_status"]["expiring_soon"] += 1
                else:
                    stats["by_retention_status"]["active"] += 1

        return stats
