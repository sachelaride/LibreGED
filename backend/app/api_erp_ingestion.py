from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import User
from app.models_ged import (
    DocumentCategory,
    ExternalIngestionAudit,
    GEDAcademicPhase,
    GEDDocument,
    GEDDocumentStatus,
    FilaProcessamento,
)
from app.schemas_erp import (
    ConnectorStatus,
    ConnectorStatusContract,
    ConnectorStatusUpdate,
    IngestionPayload,
    IngestionResponse,
)
import hashlib
import json

router = APIRouter()


@router.get(
    "/api/integration/erp/connector/status",
    response_model=ConnectorStatusContract,
    tags=["Integração ERP"],
)
def connector_status_contract():
    """Exposes the formal status contract used by the ERP connector to reconcile ingestion jobs."""
    return ConnectorStatusContract(
        status=ConnectorStatus.QUEUED,
        message="Contrato de status do conector ERP ativo. A integração deve reportar RECEIVED, QUEUED, PROCESSING, ACCEPTED, REJECTED, DUPLICATE, FAILED ou COMPLETED.",
        idempotency_key=None,
        document_id=None,
        correlation_id=None,
        source_system="erp-connector",
        last_updated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/api/integration/erp/reconciliation", tags=["Integração ERP"])
def reconcile_erp_ingestions(
    db: Session = Depends(get_db),
    administrator: User = Depends(get_current_admin),
):
    """Report ERP ingestions whose local document or queue state diverged."""
    audits = db.query(ExternalIngestionAudit).all()
    missing_documents = []
    missing_queue = []
    queue_statuses = {}
    mismatched_statuses = {}
    expected_statuses = {
        ConnectorStatus.RECEIVED: "PENDENTE",
        ConnectorStatus.QUEUED: "PENDENTE",
        ConnectorStatus.PROCESSING: "PROCESSANDO",
        ConnectorStatus.ACCEPTED: "CONCLUIDO",
        ConnectorStatus.COMPLETED: "CONCLUIDO",
        ConnectorStatus.REJECTED: "FALHA",
        ConnectorStatus.DUPLICATE: "FALHA",
        ConnectorStatus.FAILED: "FALHA",
    }
    for audit in audits:
        if not audit.document_id:
            missing_documents.append(audit.id)
            continue
        document = db.get(GEDDocument, audit.document_id)
        if document is None:
            missing_documents.append(audit.id)
            continue
        queue = db.query(FilaProcessamento).filter_by(documento_id=document.id).order_by(
            FilaProcessamento.created_at.desc()
        ).first()
        if queue is None:
            missing_queue.append(document.id)
            continue
        queue_statuses[document.id] = queue.status
        # Local status is used as a diagnostic summary for reconciliation; this keeps
        # the contract aligned with the queue-state model without introducing new storage.
        if queue.status not in {"PENDENTE", "PROCESSANDO", "CONCLUIDO", "FALHA"}:
            mismatched_statuses[document.id] = {
                "document_status": document.status.value if hasattr(document.status, "value") else str(document.status),
                "queue_status": queue.status,
                "reason": "unsupported_local_status",
            }

    report = {
        "audits_checked": len(audits),
        "missing_documents": missing_documents,
        "missing_queue": missing_queue,
        "queue_statuses": queue_statuses,
        "mismatched_statuses": mismatched_statuses,
        "consistent": not missing_documents and not missing_queue and not mismatched_statuses,
        "scope": "erp_ingestion_to_local_document_queue",
        "expected_statuses": {status.value: expected_statuses[status] for status in expected_statuses},
    }
    from app.main import add_audit
    add_audit(
        db,
        "integration",
        "erp-reconciliation",
        "erp_reconciliation",
        json.dumps(report, ensure_ascii=False),
        administrator.id,
    )
    db.commit()
    return report


@router.post(
    "/api/integration/erp/connector/status",
    response_model=ConnectorStatusContract,
    tags=["Integração ERP"],
)
def upsert_connector_status_contract(
    payload: ConnectorStatusUpdate,
    db: Session = Depends(get_db),
    administrator: User = Depends(get_current_admin),
):
    """Receives a connector status update and reconciles it with the local document queue."""
    if payload.document_id:
        document = db.get(GEDDocument, payload.document_id)
        if document:
            queue = db.query(FilaProcessamento).filter_by(documento_id=document.id).order_by(
                FilaProcessamento.created_at.desc()
            ).first()
            if queue is None:
                queue = FilaProcessamento(documento_id=document.id, status="PENDENTE")
                db.add(queue)
            status_mapping = {
                ConnectorStatus.RECEIVED: "PENDENTE",
                ConnectorStatus.QUEUED: "PENDENTE",
                ConnectorStatus.PROCESSING: "PROCESSANDO",
                ConnectorStatus.ACCEPTED: "CONCLUIDO",
                ConnectorStatus.COMPLETED: "CONCLUIDO",
                ConnectorStatus.REJECTED: "FALHA",
                ConnectorStatus.DUPLICATE: "FALHA",
                ConnectorStatus.FAILED: "FALHA",
            }
            queue.status = status_mapping.get(payload.status, "PENDENTE")
            queue.updated_at = datetime.now(timezone.utc)

            if payload.status in {ConnectorStatus.ACCEPTED, ConnectorStatus.COMPLETED}:
                document.status = GEDDocumentStatus.VALIDO
            elif payload.status in {ConnectorStatus.REJECTED, ConnectorStatus.FAILED, ConnectorStatus.DUPLICATE}:
                document.status = GEDDocumentStatus.REJEITADO
            elif payload.status == ConnectorStatus.PROCESSING:
                document.status = GEDDocumentStatus.PENDENTE_VALIDACAO
            else:
                document.status = GEDDocumentStatus.RASCUNHO

    audit = None
    if payload.idempotency_key:
        audit = db.query(ExternalIngestionAudit).filter(
            ExternalIngestionAudit.idempotency_key == payload.idempotency_key
        ).first()
    elif payload.document_id:
        audit = db.query(ExternalIngestionAudit).filter(
            ExternalIngestionAudit.document_id == payload.document_id
        ).order_by(ExternalIngestionAudit.created_at.desc()).first()

    if audit is not None:
        if payload.correlation_id:
            audit.correlation_id = payload.correlation_id
        if payload.source_system:
            audit.source_system = payload.source_system
        if payload.document_id:
            audit.document_id = payload.document_id

    db.commit()
    response = ConnectorStatusContract(
        status=payload.status,
        message=payload.message,
        idempotency_key=payload.idempotency_key,
        document_id=payload.document_id,
        correlation_id=payload.correlation_id,
        source_system=payload.source_system,
        last_updated_at=payload.last_updated_at or datetime.now(timezone.utc).isoformat(),
    )
    from app.main import add_audit
    add_audit(
        db,
        "integration",
        "erp-connector-status",
        "status_update",
        json.dumps(response.model_dump(), ensure_ascii=False),
        administrator.id,
    )
    db.commit()
    return response

@router.post("/api/integration/erp/ingest", response_model=IngestionResponse, tags=["Integração ERP"])
def ingest_erp_data(
    payload: IngestionPayload,
    x_idempotency_key: str = Header(..., description="Chave única para evitar duplicidades na emissão do diploma"),
    x_correlation_id: str = Header(None, description="ID interno do ERP (ex: ID da requisição de formatura)"),
    x_source_system: str = Header(..., description="Nome do sistema de origem (ex: Sponte_v3)"),
    db: Session = Depends(get_db)
):
    """
    Recebe os dados do Aluno do ERP Acadêmico e cria um rascunho de Diploma no GED.
    Garante que não haverá duplicidade através do Idempotency Key.
    """
    
    # 1. Checagem de Idempotência
    existing_audit = db.query(ExternalIngestionAudit).filter(ExternalIngestionAudit.idempotency_key == x_idempotency_key).first()
    if existing_audit:
        # Se já processou, devolve os dados daquela mesma execução (sem re-processar)
        return IngestionResponse(
            message="Requisição ignorada por Idempotência (Já processada anteriormente).",
            document_id=existing_audit.document_id or "N/A",
            status="IDEMPOTENT_CACHE",
            idempotency_key=x_idempotency_key,
            audit_id=existing_audit.id
        )
    
    # 2. Computar o Hash Criptográfico do Payload Exato
    raw_json = payload.model_dump_json()
    payload_hash = hashlib.sha256(raw_json.encode('utf-8')).hexdigest()
    
    # 3. Processamento de Negócio
    # Procura a categoria de "Diploma" para vincular ao documento
    cat = db.query(DocumentCategory).filter(DocumentCategory.name.ilike("%Diploma%")).first()
    if not cat:
        # Cria uma fallback se não existir
        cat = DocumentCategory(name="Diploma", index_code="0099_DIP")
        db.add(cat)
        db.commit()
        db.refresh(cat)
        
    doc = GEDDocument(
        title=f"Diploma - {payload.aluno.nome}",
        category_id=cat.id,
        academic_phase=GEDAcademicPhase.DIPLOMACAO,
        status=GEDDocumentStatus.RASCUNHO,
        file_path="virtual_from_erp", # Como veio do ERP, ainda vamos gerar o XML real no pipeline
        extracted_metadata=raw_json,
        institution_id=payload.institution_id,
        modality=payload.aluno.curso.modalidade
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # 4. Grava a Auditoria Externa
    audit = ExternalIngestionAudit(
        correlation_id=x_correlation_id,
        idempotency_key=x_idempotency_key,
        source_system=x_source_system,
        raw_payload_hash=payload_hash,
        document_id=doc.id,
        callback_url=payload.callback_url
    )
    db.add(audit)
    
    # 5. Coloca na Fila de Processamento
    from app.models_ged import FilaProcessamento
    
    fila = FilaProcessamento(documento_id=doc.id)
    db.add(fila)
    
    db.commit()
    db.refresh(audit)
    db.refresh(fila)
    
    return IngestionResponse(
        message="Dados ingeridos com sucesso e enviados para a fila de processamento.",
        document_id=doc.id,
        status="QUEUED",
        idempotency_key=x_idempotency_key,
        audit_id=audit.id
    )
