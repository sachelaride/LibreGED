from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
import shutil
import os
from pathlib import Path

from app.database import get_db
from app import models, models_ged
from app.auth import get_current_active_user, role_checker
from pydantic import BaseModel, ConfigDict, Field
from app.auth import get_current_admin, get_current_active_user, role_checker
from typing import List
from uuid import uuid4
import json

router = APIRouter(prefix="/api/admin", tags=["Administração"])

AdminRole = Depends(role_checker(["admin_global", "admin_instituicao"]))
OperadorRole = Depends(role_checker(["admin_global", "admin_instituicao", "operador"]))

from app.models_config import ConfigProposal
from app.schemas_config import ConfigProposalCreate, ConfigProposalResponse
from app.config_manager import config_manager
from datetime import datetime, UTC

def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)

# --- SCHEMAS ---

class InstitutionSettingsBase(BaseModel):
    max_upload_size_mb: int = Field(default=10, ge=1, le=1024)
    allowed_mime_types: str = Field(default="application/pdf,image/jpeg,image/png")
    antimalware_enabled: bool = Field(default=True)
    quarantine_enabled: bool = Field(default=True)
    quarantine_policy: str = Field(default="manual")

class InstitutionSettingsResponse(InstitutionSettingsBase):
    id: str
    institution_id: str

class DocumentCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    workflow_id: Optional[str] = None
    is_active: bool = True

class DocumentCategoryCreate(DocumentCategoryBase):
    code: Optional[str] = None
    retention_years: Optional[int] = None

class DocumentCategoryResponse(DocumentCategoryBase):
    id: str
    institution_id: Optional[str] = None

# --- ROTAS ---

@router.get("/settings", response_model=InstitutionSettingsResponse)
def get_settings(
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = OperadorRole
):
    """Obtém as configurações da instituição do admin atual"""
    target_inst_id = institution_id or user.institution_id
    if user.role == "admin_global" and not target_inst_id:
        # Default to first institution for global admin to avoid crash in UI if none specified
        first_inst = db.query(models.Institution).first()
        if not first_inst:
            raise HTTPException(status_code=400, detail="Nenhuma instituição cadastrada no sistema.")
        target_inst_id = first_inst.id
        
    settings = db.query(models.InstitutionSettings).filter(
        models.InstitutionSettings.institution_id == target_inst_id
    ).first()
    
    if not settings:
        settings = models.InstitutionSettings(
            id=str(uuid4()),
            institution_id=target_inst_id
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        
    return settings

@router.put("/settings", response_model=InstitutionSettingsResponse)
def propose_settings_update(
    payload: InstitutionSettingsBase,
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = OperadorRole
):
    """Propõe uma atualização nas configurações da instituição. Auto-aprova se for gestor/admin."""
    target_inst_id = institution_id or user.institution_id
    if user.role == "admin_global" and not target_inst_id:
        first_inst = db.query(models.Institution).first()
        if not first_inst:
            raise HTTPException(status_code=400, detail="Nenhuma instituição cadastrada no sistema.")
        target_inst_id = first_inst.id
        
    settings = db.query(models.InstitutionSettings).filter(
        models.InstitutionSettings.institution_id == target_inst_id
    ).first()
    
    previous_json = None
    if settings:
        previous_json = json.dumps({
            "max_upload_size_mb": settings.max_upload_size_mb,
            "allowed_mime_types": settings.allowed_mime_types,
            "antimalware_enabled": settings.antimalware_enabled,
            "quarantine_enabled": settings.quarantine_enabled,
            "quarantine_policy": settings.quarantine_policy
        })
        
    payload_json = payload.model_dump_json()
    
    proposal = ConfigProposal(
        id=str(uuid4()),
        institution_id=target_inst_id,
        proposed_by_id=user.id,
        payload_json=payload_json,
        previous_payload_json=previous_json,
        status="PENDING"
    )
    
    # Auto-aprovar se for admin/gestor
    if user.role in ["admin_global", "admin_instituicao"]:
        proposal.status = "APPROVED"
        proposal.approved_by_id = user.id
        proposal.approved_at = utc_now()
        
        if not settings:
            settings = models.InstitutionSettings(
                id=str(uuid4()),
                institution_id=target_inst_id
            )
            db.add(settings)
            
        settings.max_upload_size_mb = payload.max_upload_size_mb
        settings.allowed_mime_types = payload.allowed_mime_types
        settings.antimalware_enabled = payload.antimalware_enabled
        settings.quarantine_enabled = payload.quarantine_enabled
        settings.quarantine_policy = payload.quarantine_policy
        
        # Invalida o cache (Hot Reload)
        config_manager.invalidate(user.institution_id)
        
    db.add(proposal)
    db.commit()
    db.refresh(settings)

    return settings

@router.get("/settings/proposals", response_model=List[ConfigProposalResponse])
def get_proposals(db: Session = Depends(get_db), user: models.User = OperadorRole):
    return db.query(ConfigProposal).filter(
        ConfigProposal.institution_id == user.institution_id
    ).order_by(ConfigProposal.created_at.desc()).all()

@router.post("/settings/proposals/{proposal_id}/approve", response_model=InstitutionSettingsResponse)
def approve_proposal(proposal_id: str, db: Session = Depends(get_db), user: models.User = AdminRole):
    """Aprova uma proposta pendente e aplica as configurações."""
    proposal = db.query(ConfigProposal).filter(
        ConfigProposal.id == proposal_id, 
        ConfigProposal.institution_id == user.institution_id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
        
    if proposal.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only pending proposals can be approved")
        
    payload = json.loads(proposal.payload_json)
    
    settings = db.query(models.InstitutionSettings).filter(
        models.InstitutionSettings.institution_id == user.institution_id
    ).first()
    
    if not settings:
        settings = models.InstitutionSettings(
            id=str(uuid4()),
            institution_id=user.institution_id
        )
        db.add(settings)
        
    settings.max_upload_size_mb = payload.get("max_upload_size_mb", 10)
    settings.allowed_mime_types = payload.get("allowed_mime_types", "")
    settings.antimalware_enabled = payload.get("antimalware_enabled", False)
    settings.quarantine_enabled = payload.get("quarantine_enabled", False)
    settings.quarantine_policy = payload.get("quarantine_policy", "manual")
    
    proposal.status = "APPROVED"
    proposal.approved_by_id = user.id
    proposal.approved_at = utc_now()
    
    db.commit()
    db.refresh(settings)
    
    # Hot Reload Invalidate
    config_manager.invalidate(user.institution_id)
    
    return settings

@router.post("/settings/proposals/{proposal_id}/reject", response_model=ConfigProposalResponse)
def reject_proposal(proposal_id: str, db: Session = Depends(get_db), user: models.User = AdminRole):
    """Rejeita uma proposta pendente."""
    proposal = db.query(ConfigProposal).filter(
        ConfigProposal.id == proposal_id, 
        ConfigProposal.institution_id == user.institution_id
    ).first()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
        
    if proposal.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only pending proposals can be rejected")
        
    proposal.status = "REJECTED"
    db.commit()
    db.refresh(proposal)
    return proposal

@router.post("/settings/proposals/{proposal_id}/revert", response_model=InstitutionSettingsResponse)
def revert_proposal(proposal_id: str, db: Session = Depends(get_db), user: models.User = AdminRole):
    """Reverte a configuração usando o previous_payload_json de uma proposta."""
    proposal = db.query(ConfigProposal).filter(
        ConfigProposal.id == proposal_id, 
        ConfigProposal.institution_id == user.institution_id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
        
    if proposal.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Cannot revert a non-approved proposal")
        
    if not proposal.previous_payload_json:
        raise HTTPException(status_code=400, detail="No previous payload to revert to")
        
    prev_data = json.loads(proposal.previous_payload_json)
    
    settings = db.query(models.InstitutionSettings).filter(
        models.InstitutionSettings.institution_id == user.institution_id
    ).first()
    
    settings.max_upload_size_mb = prev_data.get("max_upload_size_mb", 10)
    settings.allowed_mime_types = prev_data.get("allowed_mime_types", "")
    settings.antimalware_enabled = prev_data.get("antimalware_enabled", False)
    settings.quarantine_enabled = prev_data.get("quarantine_enabled", False)
    settings.quarantine_policy = prev_data.get("quarantine_policy", "manual")
    
    proposal.status = "REVERTED"
    
    db.commit()
    db.refresh(settings)
    
    # Hot Reload Invalidate
    config_manager.invalidate(user.institution_id)
    
    return settings

@router.get("/document-types", response_model=List[DocumentCategoryResponse])
def list_document_types(db: Session = Depends(get_db), user: models.User = AdminRole):
    """Lista os tipos documentais da instituição"""
    query = db.query(models_ged.DocumentCategory)
    
    if user.role != "admin_global":
        # Retorna categorias globais (institution_id=None) e categorias da instituição
        query = query.filter((models_ged.DocumentCategory.institution_id == user.institution_id) | (models_ged.DocumentCategory.institution_id == None))
        
    return query.all()

@router.post("/document-types", response_model=DocumentCategoryResponse)
def create_document_type(payload: DocumentCategoryCreate, db: Session = Depends(get_db), user: models.User = AdminRole):
    """Cria uma nova categoria documental para a instituição do admin"""
    if user.role == "admin_global":
        raise HTTPException(status_code=400, detail="Admin global must specify institution_id")
        
    doc_type = models_ged.DocumentCategory(
        id=str(uuid4()),
        institution_id=user.institution_id,
        name=payload.name,
        code=payload.code,
        retention_years=payload.retention_years,
        is_active=payload.is_active
    )
    db.add(doc_type)
    db.commit()
    db.refresh(doc_type)
    return doc_type

# --- INGESTIONS ---
class IngestionJobResponse(BaseModel):
    id: str
    status: str
    file_path: str
    manifest_path: str
    error_message: Optional[str] = None
    retries: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

@router.get("/ingestions", response_model=list[IngestionJobResponse])
def get_ingestions(
    status: Optional[str] = None, 
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db), 
    user: models.User = AdminRole
):
    """Lista as ingestões da instituição, filtrando opcionalmente por status"""
    target_inst_id = institution_id or user.institution_id
    if user.role == "admin_global" and not target_inst_id:
        first_inst = db.query(models.Institution).first()
        if not first_inst:
            raise HTTPException(status_code=400, detail="Nenhuma instituição cadastrada no sistema.")
        target_inst_id = first_inst.id
        
    query = db.query(models.IngestionJob).filter(models.IngestionJob.institution_id == target_inst_id)
    if status:
        query = query.filter(models.IngestionJob.status == status.upper())
        
    return query.order_by(models.IngestionJob.created_at.desc()).limit(100).all()

@router.post("/ingestions/{job_id}/retry")
def retry_ingestion(
    job_id: str, 
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db), 
    user: models.User = AdminRole
):
    """Manda um job falho/quarentena de volta para incoming (retry)"""
    target_inst_id = institution_id or user.institution_id
    if user.role == "admin_global" and not target_inst_id:
        first_inst = db.query(models.Institution).first()
        if not first_inst:
            raise HTTPException(status_code=400, detail="Nenhuma instituição cadastrada no sistema.")
        target_inst_id = first_inst.id
        
    job = db.query(models.IngestionJob).filter(
        models.IngestionJob.id == job_id,
        models.IngestionJob.institution_id == target_inst_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
        
    if job.status not in ["QUARANTINE", "FAILED"]:
        raise HTTPException(status_code=400, detail="Can only retry QUARANTINE or FAILED jobs")
        
    from app.filewatch import DIR_INCOMING
    
    # Move files back to incoming
    try:
        pdf_name = Path(job.file_path).name
        man_name = Path(job.manifest_path).name
        if os.path.exists(job.file_path):
            shutil.move(job.file_path, str(DIR_INCOMING / pdf_name))
        if os.path.exists(job.manifest_path):
            shutil.move(job.manifest_path, str(DIR_INCOMING / man_name))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move files: {e}")
        
    job.status = "PENDING"
    job.error_message = None
    job.retries += 1
    db.commit()
    
    return {"message": "Job sent to retry"}
