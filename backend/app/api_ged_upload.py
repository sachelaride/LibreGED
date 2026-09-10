from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.storage import save_file
from app.models_ged import GEDDocument, GEDDocumentStatus, GEDAcademicPhase, GEDDocumentIndexValue, DocumentTransitionHistory, DocumentCategory
from app.models_ged_config import DocumentType
from app.models_workflow import DocumentWorkflowInstance, WorkflowState
from app.schemas_ged import GEDDocumentResponse
from app.search import SearchService
import uuid
import json

from app.auth import get_current_active_user, check_document_type_access
from app.models import User, InstitutionSettings
from app.config_manager import config_manager

router = APIRouter()

@router.post("/api/documents/upload", response_model=GEDDocumentResponse, tags=["GED - Execução"])
async def upload_document(
    title: str = Form(...),
    document_type_id: str = Form(...),
    indices_json: str = Form("[]"), # Expects JSON string of list of dicts [{"index_id": "...", "value": "..."}]
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doc_type = db.query(DocumentType).filter(DocumentType.id == document_type_id).first()
    if not doc_type:
        raise HTTPException(status_code=400, detail="Tipo de Documento inválido.")
        
    check_document_type_access(db, current_user, document_type_id)
    
    settings = config_manager.get_settings(db, current_user.institution_id)
    antimalware_enabled = settings.get("antimalware_enabled", True)
    quarantine_enabled = settings.get("quarantine_enabled", True)
        
    from app.upload_validation import scan_for_malware
    content = await file.read()
    is_malware = scan_for_malware(content) if antimalware_enabled else False
    
    initial_doc_status = GEDDocumentStatus.PENDENTE_VALIDACAO
    if is_malware:
        if quarantine_enabled:
            initial_doc_status = GEDDocumentStatus.QUARENTENA
        else:
            raise HTTPException(status_code=406, detail="Malware detectado e a quarentena está desativada. O arquivo foi rejeitado.")
            
    file_ext = file.filename.split(".")[-1] if file.filename else "pdf"
    safe_name = f"{uuid.uuid4()}.{file_ext}"
    
    # Em um sistema real, o save_file usaria doc_type.storage_area_id e partition_id
    saved_path = save_file(safe_name, content, db=db, rule_name=doc_type.storage_area_id)

    # O modelo legado de GED exige uma categoria própria para a FK do documento.
    category = db.query(DocumentCategory).filter(DocumentCategory.id == doc_type.id).first()
    if not category:
        category = DocumentCategory(id=doc_type.id, name=doc_type.name)
        db.add(category)
        db.flush()

    persisted_user_id = db.query(User.id).filter(User.id == current_user.id).scalar()
    
    db_doc = GEDDocument(
        title=title,
        file_path=saved_path,
        category_id=doc_type.id, # Backward compatibility for existing schemas
        status=initial_doc_status,
        institution_id=current_user.institution_id,
        uploaded_by_user_id=persisted_user_id
    )
    db.add(db_doc)
    db.flush() # Get the document ID
    
    try:
        indices = json.loads(indices_json)
        for idx in indices:
            val = GEDDocumentIndexValue(
                document_id=db_doc.id,
                index_id=idx["index_id"],
                value=idx["value"]
            )
            db.add(val)
    except Exception as e:
        pass # Ignore JSON parsing error for now
        
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

    db.commit()
    db.refresh(db_doc)
    
    # Manter compatibilidade com o serviço de busca PostgreSQL.
    search_service = SearchService()
    search_service.index_document(
        db=db,
        document_id=db_doc.id,
        title=db_doc.title,
        content="Conteúdo OCR mockado", # Aqui no futuro conectamos o PyTesseract
        indices_data=indices_json
    )
    
    return db_doc

