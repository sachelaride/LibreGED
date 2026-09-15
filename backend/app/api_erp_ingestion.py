from fastapi import APIRouter, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas_erp import IngestionPayload, IngestionResponse
from app.models_ged import (
    ExternalIngestionAudit, GEDDocument, GEDDocumentStatus, DocumentCategory,
    GEDAcademicPhase, FilaProcessamento,
)
from app.auth import get_current_admin
from app.models import User
import hashlib
import json
import uuid

router = APIRouter()


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
        else:
            queue_statuses[document.id] = queue.status

    report = {
        "audits_checked": len(audits),
        "missing_documents": missing_documents,
        "missing_queue": missing_queue,
        "queue_statuses": queue_statuses,
        "consistent": not missing_documents and not missing_queue,
        "scope": "erp_ingestion_to_local_document_queue",
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
