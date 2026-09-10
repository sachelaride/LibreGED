from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from app.database import get_db
from app.models import User
from app.auth import get_current_active_user
from app.models_ecm import DynamicAspect, DynamicProperty
from app.schemas_ecm import DynamicAspectCreate, DynamicAspectResponse, DynamicPropertyCreate, DynamicPropertyResponse

router = APIRouter()

@router.get("/api/ecm/dictionary/aspects", response_model=List[DynamicAspectResponse], tags=["ECM Dictionary"])
def list_aspects(db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Lista todos os aspectos disponiveis para o usuario logado (globais + os da sua instituicao).
    """
    aspects = db.query(DynamicAspect).filter(
        or_(
            DynamicAspect.institution_id == None,
            DynamicAspect.institution_id == user.institution_id
        )
    ).all()
    return aspects

@router.post("/api/ecm/dictionary/aspects", response_model=DynamicAspectResponse, tags=["ECM Dictionary"])
def create_aspect(payload: DynamicAspectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Cria um novo aspecto dinamico.
    """
    # Verifica se ja existe com esse nome
    existing = db.query(DynamicAspect).filter(DynamicAspect.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Aspect with this name already exists")
        
    institution_id = None if payload.is_global else user.institution_id
    
    # Apenas admin global pode criar aspectos globais
    if payload.is_global and user.role != "admin_global":
        raise HTTPException(status_code=403, detail="Only global admins can create global aspects")
        
    aspect = DynamicAspect(
        name=payload.name,
        title=payload.title,
        description=payload.description,
        institution_id=institution_id
    )
    db.add(aspect)
    db.commit()
    db.refresh(aspect)
    return aspect

@router.get("/api/ecm/dictionary/aspects/{aspect_id}", response_model=DynamicAspectResponse, tags=["ECM Dictionary"])
def get_aspect(aspect_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    aspect = db.query(DynamicAspect).filter(DynamicAspect.id == aspect_id).first()
    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")
        
    if aspect.institution_id and aspect.institution_id != user.institution_id:
        raise HTTPException(status_code=403, detail="Not allowed to view this aspect")
        
    return aspect

@router.post("/api/ecm/dictionary/aspects/{aspect_id}/properties", response_model=DynamicPropertyResponse, tags=["ECM Dictionary"])
def add_property_to_aspect(aspect_id: str, payload: DynamicPropertyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """
    Adiciona uma nova propriedade a um aspecto existente.
    """
    aspect = db.query(DynamicAspect).filter(DynamicAspect.id == aspect_id).first()
    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")
        
    # Validar permissao
    if aspect.institution_id is None and user.role != "admin_global":
        raise HTTPException(status_code=403, detail="Only global admins can modify global aspects")
    if aspect.institution_id and aspect.institution_id != user.institution_id:
        raise HTTPException(status_code=403, detail="Not allowed to modify this aspect")
        
    # Verificar se propriedade ja existe no aspecto
    existing = db.query(DynamicProperty).filter(
        DynamicProperty.aspect_id == aspect.id,
        DynamicProperty.name == payload.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Property with this name already exists in this aspect")
        
    prop = DynamicProperty(
        aspect_id=aspect.id,
        name=payload.name,
        title=payload.title,
        data_type=payload.data_type,
        required=payload.required,
        multiple=payload.multiple,
        options_json=payload.options_json
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop
