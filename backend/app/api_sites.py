from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models
from app.auth import get_current_active_user, require_site_role
from app.models_ecm import Site, SiteMember
from app.schemas_ecm import SiteCreate, SiteResponse, SiteMemberCreate, SiteMemberResponse
import uuid

router = APIRouter(prefix="/api/ecm/sites", tags=["ECM Sites"])

SiteManagerRole = Depends(require_site_role(["SiteManager"]))
SiteWriteRole = Depends(require_site_role(["SiteManager", "SiteCollaborator", "SiteContributor"]))
SiteReadRole = Depends(require_site_role(["SiteManager", "SiteCollaborator", "SiteContributor", "SiteConsumer"]))

@router.get("", response_model=List[SiteResponse])
def list_sites(db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    """
    Lista todos os sites em que o usuário tem acesso ou são públicos na instituição
    """
    if user.role == "admin_global":
        return db.query(Site).all()
        
    # Get sites user is member of OR are PUBLIC in their institution
    return db.query(Site).filter(
        Site.institution_id == user.institution_id,
        (Site.visibility == "PUBLIC") | (Site.members.any(SiteMember.user_id == user.id))
    ).all()

@router.post("", response_model=SiteResponse)
def create_site(payload: SiteCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)):
    """
    Cria um novo Site (Espaço Colaborativo). O criador automaticamente se torna SiteManager.
    """
    site = Site(
        id=str(uuid.uuid4()),
        name=payload.name,
        title=payload.title,
        description=payload.description,
        visibility=payload.visibility,
        institution_id=user.institution_id,
        created_by=user.id
    )
    db.add(site)
    db.commit()
    
    # Criador vira SiteManager
    member = SiteMember(
        site_id=site.id,
        user_id=user.id,
        role="SiteManager"
    )
    db.add(member)
    db.commit()
    db.refresh(site)
    
    return site

@router.get("/{site_id}", response_model=SiteResponse)
def get_site(site_id: str, db: Session = Depends(get_db), user: models.User = SiteReadRole):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if user.role != "admin_global" and site.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Site not found")
    return site

@router.delete("/{site_id}")
def delete_site(site_id: str, db: Session = Depends(get_db), user: models.User = SiteManagerRole):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if user.role != "admin_global" and site.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Site not found")
        
    db.delete(site)
    db.commit()
    return {"message": "Site removed successfully"}

@router.post("/{site_id}/members", response_model=SiteMemberResponse)
def add_site_member(site_id: str, payload: SiteMemberCreate, db: Session = Depends(get_db), user: models.User = SiteManagerRole):
    # Verifica se o site existe
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if user.role != "admin_global" and site.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Site not found")
        
    # Verifica se o usuario existe
    target_user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.institution_id != site.institution_id:
        raise HTTPException(status_code=422, detail="User belongs to another institution")
        
    # Validar Role
    valid_roles = ["SiteManager", "SiteCollaborator", "SiteContributor", "SiteConsumer"]
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
        
    # Checar se ja é membro, e atualizar
    member = db.query(SiteMember).filter(SiteMember.site_id == site_id, SiteMember.user_id == target_user.id).first()
    if member:
        member.role = payload.role
    else:
        member = SiteMember(site_id=site_id, user_id=target_user.id, role=payload.role)
        db.add(member)
        
    db.commit()
    db.refresh(member)
    return member

@router.delete("/{site_id}/members/{user_id}")
def remove_site_member(site_id: str, user_id: str, db: Session = Depends(get_db), user: models.User = SiteManagerRole):
    site = db.query(Site).filter(Site.id == site_id).first()
    if site and user.role != "admin_global" and site.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Site not found")
    member = db.query(SiteMember).filter(SiteMember.site_id == site_id, SiteMember.user_id == user_id).first()
    if member:
        db.delete(member)
        db.commit()
    return {"message": "Member removed successfully"}
