from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, models_templates
from app import auth
from app.schemas_templates import GEDTemplateCreate, GEDTemplateUpdate, GEDTemplateResponse

router = APIRouter()

@router.get("/templates", response_model=List[GEDTemplateResponse], tags=["Admin - Templates"])
def get_templates(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    return db.query(models_templates.GEDTemplate).all()

@router.post("/templates", response_model=GEDTemplateResponse, tags=["Admin - Templates"])
def create_template(template_in: GEDTemplateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    template = models_templates.GEDTemplate(
        name=template_in.name,
        html_content=template_in.html_content,
        is_active=template_in.is_active
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

@router.put("/templates/{template_id}", response_model=GEDTemplateResponse, tags=["Admin - Templates"])
def update_template(template_id: str, template_in: GEDTemplateUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    template = db.query(models_templates.GEDTemplate).filter(models_templates.GEDTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    if template_in.name is not None:
        template.name = template_in.name
    if template_in.html_content is not None:
        template.html_content = template_in.html_content
    if template_in.is_active is not None:
        template.is_active = template_in.is_active
        
    db.commit()
    db.refresh(template)
    return template
