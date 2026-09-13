from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app import models
from app import auth
from app.schemas_institutions import InstitutionCreate, InstitutionResponse
from app.schemas_pagination import PaginatedResponse
import math
from pydantic import BaseModel, Field

class InstitutionUpdate(BaseModel):
    name: str = Field(..., min_length=2)
    legal_name: str = Field(..., min_length=2)

router = APIRouter(prefix="/api")

@router.get("/institutions", response_model=PaginatedResponse[InstitutionResponse], tags=["Admin - Institutions"])
def get_institutions(
    page: int = 1, 
    size: int = 50, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.role_checker(["admin_global"]))
):
    query = db.query(models.Institution)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/institutions", response_model=InstitutionResponse, tags=["Admin - Institutions"])
def create_institution(
    institution: InstitutionCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.role_checker(["admin_global"]))
):
    existing = db.query(models.Institution).filter_by(cnpj=institution.cnpj).first()
    if existing:
        raise HTTPException(status_code=409, detail="Instituição com este CNPJ já existe")
    
    new_inst = models.Institution(
        id=str(uuid.uuid4()),
        name=institution.name,
        cnpj=institution.cnpj,
        legal_name=institution.legal_name
    )
    db.add(new_inst)
    db.commit()
    db.refresh(new_inst)
    
    # Create default settings for this institution
    settings = models.InstitutionSettings(
        id=str(uuid.uuid4()),
        institution_id=new_inst.id
    )
    db.add(settings)
    
    from app.main import add_audit
    add_audit(db, "institution", new_inst.id, "created", "Institution created")
    
    db.commit()
    
    return new_inst

@router.put("/institutions/{institution_id}", response_model=InstitutionResponse, tags=["Admin - Institutions"])
def update_institution(
    institution_id: str,
    payload: InstitutionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.role_checker(["admin_global"]))
):
    inst = db.query(models.Institution).filter(models.Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")
    
    inst.name = payload.name
    inst.legal_name = payload.legal_name
    
    from app.main import add_audit
    add_audit(db, "institution", inst.id, "updated", f"Institution {inst.cnpj} updated by {current_user.username}", current_user.id)
    
    db.commit()
    db.refresh(inst)
    return inst

@router.delete("/institutions/{institution_id}", status_code=204, tags=["Admin - Institutions"])
def delete_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.role_checker(["admin_global"]))
):
    inst = db.query(models.Institution).filter(models.Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")
    
    from app.main import add_audit
    add_audit(db, "institution", inst.id, "deleted", f"Institution {inst.cnpj} deleted by {current_user.username}", current_user.id)
    
    # Let SQLAlchemy throw IntegrityError if there are children. main.py handles it and returns 409.
    db.delete(inst)
    db.commit()
    return None
