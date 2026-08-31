from fastapi import APIRouter, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas_erp import IngestionPayload, IngestionResponse
from app.models_ged import ExternalIngestionAudit, GEDDocument, GEDDocumentStatus, DocumentCategory, GEDAcademicPhase
import hashlib
import json
import uuid

router = APIRouter()

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
        extracted_metadata=raw_json
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
        document_id=doc.id
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    
    return IngestionResponse(
        message="Dados ingeridos com sucesso e rascunho criado.",
        document_id=doc.id,
        status="PROCESSED",
        idempotency_key=x_idempotency_key,
        audit_id=audit.id
    )
