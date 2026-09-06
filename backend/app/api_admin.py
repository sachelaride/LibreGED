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
from pydantic import BaseModel, ConfigDict
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["Administração"])

AdminRole = Depends(role_checker(["gestor_clinica"]))

# --- SCHEMAS ---

class InstitutionSettingsBase(BaseModel):
    max_upload_size_mb: int = 10
    allowed_mime_types: str = "application/pdf,image/jpeg,image/png"

class InstitutionSettingsResponse(InstitutionSettingsBase):
    id: str
    institution_id: str

class DocumentCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    workflow_id: Optional[str] = None
    is_active: bool = True

class DocumentCategoryResponse(DocumentCategoryBase):
    id: str
    institution_id: Optional[str] = None

# --- ROTAS ---

@router.get("/settings", response_model=InstitutionSettingsResponse)
def get_settings(db: Session = Depends(get_db), user: models.User = AdminRole):
    """Obtém as configurações da instituição do admin atual"""
    print(f"DEBUG: get_settings called with user={user.username}, role={user.role}")
    if user.role == "admin_global":
        raise HTTPException(status_code=400, detail="Admin global must specify institution_id (not implemented yet)")
        
    settings = db.query(models.InstitutionSettings).filter(
        models.InstitutionSettings.institution_id == user.institution_id
    ).first()
    
    if not settings:
        settings = models.InstitutionSettings(
            id=str(uuid4()),
            institution_id=user.institution_id
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        
    return settings

@router.put("/settings", response_model=InstitutionSettingsResponse)
def update_settings(payload: InstitutionSettingsBase, db: Session = Depends(get_db), user: models.User = AdminRole):
    """Atualiza as configurações da instituição do admin atual"""
    if user.role == "admin_global":
        raise HTTPException(status_code=400, detail="Admin global must specify institution_id (not implemented yet)")
        
    settings = db.query(models.InstitutionSettings).filter(
        models.InstitutionSettings.institution_id == user.institution_id
    ).first()
    
    if not settings:
        settings = models.InstitutionSettings(
            id=str(uuid4()),
            institution_id=user.institution_id
        )
        db.add(settings)
        
    settings.max_upload_size_mb = payload.max_upload_size_mb
    settings.allowed_mime_types = payload.allowed_mime_types
    
    db.commit()
    db.refresh(settings)
    
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
def get_ingestions(status: Optional[str] = None, db: Session = Depends(get_db), user: models.User = AdminRole):
    """Lista as ingestões da instituição, filtrando opcionalmente por status"""
    if user.role == "admin_global":
        raise HTTPException(status_code=400, detail="Admin global must specify institution_id")
        
    query = db.query(models.IngestionJob).filter(models.IngestionJob.institution_id == user.institution_id)
    if status:
        query = query.filter(models.IngestionJob.status == status.upper())
        
    return query.order_by(models.IngestionJob.created_at.desc()).limit(100).all()

@router.post("/ingestions/{job_id}/retry")
def retry_ingestion(job_id: str, db: Session = Depends(get_db), user: models.User = AdminRole):
    """Manda um job falho/quarentena de volta para incoming (retry)"""
    if user.role == "admin_global":
        raise HTTPException(status_code=400, detail="Admin global must specify institution_id")
        
    job = db.query(models.IngestionJob).filter(
        models.IngestionJob.id == job_id,
        models.IngestionJob.institution_id == user.institution_id
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
