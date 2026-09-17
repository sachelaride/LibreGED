import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.storage import save_file
from app.models_ged import GEDDocument, GEDDocumentStatus, GEDAcademicPhase, GEDDocumentIndexValue, DocumentTransitionHistory, DocumentCategory
from app.models_ged_config import DocumentType
from app.models_workflow import DocumentWorkflowInstance, WorkflowState
from app.schemas_ged import GEDDocumentResponse
from app.search import SearchService
from app.ocr_engine import DocumentAnalyzer

from app.auth import get_current_active_user, check_document_type_access
from app.models import User, InstitutionSettings
from app.config_manager import config_manager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/api/documents/upload", response_model=GEDDocumentResponse, tags=["GED - Execução"])
async def upload_document(
    title: str = Form(...),
    document_type_id: str = Form(...),
    indices_json: str = Form("[]"), # Expects JSON string of list of dicts [{"index_id": "...", "value": "..."}]
    document_purpose: str = Form("official"),
    student_id: Optional[str] = Form(None),
    group_id: Optional[str] = Form(None),
    ocr_engine: str = Form("auto"),
    ocr_enabled: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if document_purpose not in {"official", "conference"}:
        raise HTTPException(422, "Finalidade documental inválida.")
    doc_type = db.query(DocumentType).filter(DocumentType.id == document_type_id).first()
    if not doc_type:
        raise HTTPException(status_code=400, detail="Tipo de Documento inválido.")
        
    check_document_type_access(db, current_user, document_type_id)
    from app.document_permissions import exigir_permissao
    exigir_permissao(db, current_user, document_type_id, "cadastrar")
    if not doc_type.is_active:
        raise HTTPException(409, "Tipo documental inativo.")

    if not current_user.institution_id:
        raise HTTPException(422, "Selecione uma instituição para cadastrar documentos.")

    try:
        indices_recebidos = json.loads(indices_json)
    except json.JSONDecodeError as erro:
        raise HTTPException(422, "indices_json deve conter JSON válido.") from erro
    from app.index_validation import validar_valores_indices
    indices = validar_valores_indices(
        db, document_type_id, current_user.institution_id, indices_recebidos)
    
    settings = config_manager.get_settings(db, current_user.institution_id)
    antimalware_enabled = settings.get("antimalware_enabled", True)
    quarantine_enabled = settings.get("quarantine_enabled", True)
        
    from app.upload_validation import read_validated_upload
    nome_arquivo = Path(file.filename or "").name
    if not nome_arquivo or nome_arquivo != file.filename:
        raise HTTPException(422, "Nome de arquivo inválido.")
    content, is_malware = read_validated_upload(
        file, nome_arquivo, antimalware_enabled=antimalware_enabled)
    
    initial_doc_status = GEDDocumentStatus.PENDENTE_VALIDACAO
    if is_malware:
        if quarantine_enabled:
            initial_doc_status = GEDDocumentStatus.QUARENTENA
        else:
            raise HTTPException(status_code=406, detail="Malware detectado e a quarentena está desativada. O arquivo foi rejeitado.")
            
    file_ext = file.filename.split(".")[-1] if file.filename else "pdf"
    safe_name = f"{uuid.uuid4()}.{file_ext}"
    
    saved_path = save_file(
        safe_name,
        content,
        db=db,
        rule_name=doc_type.storage_area_id,
        partition_name=doc_type.storage_partition_id,
    )
    file_hash = hashlib.sha256(content).hexdigest()

    # O modelo legado de GED exige uma categoria própria para a FK do documento.
    category = db.query(DocumentCategory).filter(DocumentCategory.id == doc_type.id).first()
    if not category:
        category = DocumentCategory(id=doc_type.id, name=doc_type.name)
        db.add(category)
        db.flush()

    persisted_user_id = db.query(User.id).filter(User.id == current_user.id).scalar()

    ocr_text = ""
    ocr_result = {"status": "skipped", "engine": "none", "text": ""}
    if ocr_enabled:
        analyzer = DocumentAnalyzer()
        ocr_result = analyzer.extract_text(
            file_path=saved_path,
            preferred_engine=ocr_engine or "auto",
            document_type=doc_type.name,
            language="pt",
        )
        ocr_text = (ocr_result or {}).get("text", "")

    metadata_payload = {
        "student_id": student_id,
        "group_id": group_id,
        "ocr_engine": ocr_result.get("engine"),
        "ocr_status": ocr_result.get("status"),
        "ocr_reason": ocr_result.get("reason"),
        "ocr_text": ocr_text[:4000],
        "indices": [{"index_id": indice.id, "value": valor} for indice, valor in indices],
    }

    db_doc = GEDDocument(
        title=title,
        file_path=saved_path,
        file_hash=file_hash,
        category_id=doc_type.id, # Backward compatibility for existing schemas
        status=initial_doc_status,
        institution_id=current_user.institution_id,
        campus_id=current_user.campus_id,
        uploaded_by_user_id=persisted_user_id,
        student_id=student_id,
        document_purpose=document_purpose,
        is_official=document_purpose == "official",
        extracted_metadata=json.dumps(metadata_payload, ensure_ascii=False),
    )
    db.add(db_doc)
    db.flush() # Get the document ID
    
    for indice, valor in indices:
        db.add(GEDDocumentIndexValue(
            document_id=db_doc.id,
            index_id=indice.id,
            value=valor,
        ))

    from app.main import add_audit
    add_audit(
        db,
        "document",
        db_doc.id,
        "created",
        "GED document uploaded.",
        persisted_user_id,
    )
        
    # Inicializar o Workflow se não estiver na quarentena
    if doc_type.workflow_id and initial_doc_status != GEDDocumentStatus.QUARENTENA:
        initial_state = db.query(WorkflowState).filter(
            WorkflowState.workflow_id == doc_type.workflow_id,
            WorkflowState.is_initial == True
        ).first()
        
        if initial_state:
            wkf_instance = DocumentWorkflowInstance(
                document_id=db_doc.id,
                workflow_id=doc_type.workflow_id,
                current_state_id=initial_state.id
            )
            db.add(wkf_instance)
            
            # Registrar a transição no histórico antigo também (para manter a esteira logada)
            transition = DocumentTransitionHistory(
                document_id=db_doc.id,
                from_status=None,
                to_status=GEDDocumentStatus.PENDENTE_VALIDACAO,
                changed_by_user_id=current_user.id,
                comments=f"Workflow iniciado no estado: {initial_state.label}"
            )
            db.add(transition)
    elif initial_doc_status == GEDDocumentStatus.QUARENTENA:
        transition = DocumentTransitionHistory(
            document_id=db_doc.id,
            from_status=None,
            to_status=GEDDocumentStatus.QUARENTENA,
            changed_by_user_id=current_user.id,
            comments="Arquivo isolado pela política de Antimalware."
        )
        db.add(transition)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Compensação: remover o arquivo físico que foi salvo.
        if os.path.exists(saved_path):
            try:
                os.remove(saved_path)
            except OSError:
                logger.warning("Falha ao remover arquivo persistido após erro de commit", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao salvar documento: {str(e)}")
    db.refresh(db_doc)
    
    # Manter compatibilidade com o serviço de busca PostgreSQL.
    search_service = SearchService()
    search_service.index_document(
        db=db,
        document_id=db_doc.id,
        title=db_doc.title,
        content=ocr_text[:4000] or db_doc.title,
        indices_data=json.dumps(
            [{"index_id": indice.id, "value": valor} for indice, valor in indices],
            ensure_ascii=False,
        )
    )

    return db_doc
