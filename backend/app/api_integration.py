from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models
from app.auth import get_current_active_user, role_checker
from app.models_integration import IntegrationConfig
from app.schemas_integration import IntegrationConfigCreate, IntegrationConfigUpdate, IntegrationConfigResponse
from app.security_utils import encrypt_secret

router = APIRouter(tags=["Administração - Integrações"])

IntegrationRoles = Depends(role_checker(["admin_global", "admin_instituicao"]))

def _format_response(config: IntegrationConfig) -> IntegrationConfigResponse:
    return IntegrationConfigResponse(
        id=config.id,
        institution_id=config.institution_id,
        name=config.name,
        integration_type=config.integration_type,
        base_url=config.base_url,
        is_active=config.is_active,
        has_secret=bool(config.encrypted_secret),
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@router.get("/api/integrations", response_model=List[IntegrationConfigResponse])
def list_integrations(
    db: Session = Depends(get_db),
    current_user: models.User = IntegrationRoles
):
    query = db.query(IntegrationConfig)
    if current_user.role != "admin_global":
        query = query.filter(IntegrationConfig.institution_id == current_user.institution_id)
        
    configs = query.all()
    return [_format_response(c) for c in configs]

@router.post("/api/integrations", response_model=IntegrationConfigResponse, status_code=status.HTTP_201_CREATED)
def create_integration(
    payload: IntegrationConfigCreate,
    db: Session = Depends(get_db),
    current_user: models.User = IntegrationRoles
):
    inst_id = current_user.institution_id
    if not inst_id:
        raise HTTPException(status_code=400, detail="Admin global precisa selecionar instituição alvo (MVP não suporta ainda)")
        
    enc_secret = encrypt_secret(payload.secret) if payload.secret else None
    
    config = IntegrationConfig(
        institution_id=inst_id,
        name=payload.name,
        integration_type=payload.integration_type,
        base_url=payload.base_url,
        encrypted_secret=enc_secret,
        is_active=payload.is_active
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    
    from app.main import add_audit
    add_audit(db, "integration", config.id, "create", f"Criada integração {config.name}", current_user.id)
    
    return _format_response(config)

@router.put("/api/integrations/{config_id}", response_model=IntegrationConfigResponse)
def update_integration(
    config_id: str,
    payload: IntegrationConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = IntegrationRoles
):
    config = db.query(IntegrationConfig).filter(IntegrationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Integração não encontrada")
        
    if current_user.role != "admin_global" and config.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    config.name = payload.name
    config.integration_type = payload.integration_type
    config.base_url = payload.base_url
    config.is_active = payload.is_active
    
    # Se o cliente enviar um secret, atualizamos. Se vier None/Vazio, mantemos o que já estava lá (não sobrescreve).
    if payload.secret:
        config.encrypted_secret = encrypt_secret(payload.secret)
        
    db.commit()
    db.refresh(config)
    
    from app.main import add_audit
    add_audit(db, "integration", config.id, "update", f"Atualizada integração {config.name}", current_user.id)
    
    return _format_response(config)

@router.delete("/api/integrations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = IntegrationRoles
):
    config = db.query(IntegrationConfig).filter(IntegrationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Integração não encontrada")
        
    if current_user.role != "admin_global" and config.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    from app.main import add_audit
    add_audit(db, "integration", config.id, "delete", f"Deletada integração {config.name}", current_user.id)
    
    db.delete(config)
    db.commit()
    return None
