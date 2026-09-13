from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app import models
from app import auth
from app.schemas_users import UserCreate, UserResponse
from app.schemas_pagination import PaginatedResponse
import math

router = APIRouter()

@router.get("/users", response_model=PaginatedResponse[UserResponse], tags=["Admin - Users"])
def get_users(
    page: int = 1, 
    size: int = 50, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.role_checker(["admin_global", "admin_instituicao"]))
):
    query = db.query(models.User)
    
    if current_user.role != "admin_global":
        query = query.filter(models.User.institution_id == current_user.institution_id)
        
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/users", response_model=UserResponse, tags=["Admin - Users"])
def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.role_checker(["admin_global", "admin_instituicao"]))
):
    existing = db.query(models.User).filter_by(username=user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuário já existe")
    
    institution_id = current_user.institution_id
    if current_user.role == "admin_global":
        institution_id = user.institution_id

    if current_user.role != "admin_global" and user.role == "admin_global":
        raise HTTPException(status_code=403, detail="Apenas admin global pode criar outro admin global")
    
    new_user = models.User(
        id=str(uuid.uuid4()),
        username=user.username,
        role=user.role,
        institution_id=institution_id,
        hashed_password=auth.get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

from app.schemas_users import UserUpdate

@router.put("/users/{user_id}", response_model=UserResponse, tags=["Admin - Users"])
def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.role_checker(["admin_global", "admin_instituicao"]))
):
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if current_user.role != "admin_global" and user.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Não permitido")

    if current_user.role != "admin_global" and user_in.role == "admin_global":
        raise HTTPException(status_code=403, detail="Apenas admin global pode gerenciar outro admin global")
    if user.role == "admin_global" and current_user.role != "admin_global":
        raise HTTPException(status_code=403, detail="Não permitido editar um admin global")

    if user_in.role is not None:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", tags=["Admin - Users"])
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.role_checker(["admin_global", "admin_instituicao"]))
):
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    if current_user.role != "admin_global" and user.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Não permitido")
        
    if user.role == "admin_global" and current_user.role != "admin_global":
        raise HTTPException(status_code=403, detail="Não permitido")
        
    # Soft delete
    user.is_active = False
    db.commit()
    return {"message": "Usuário removido logicamente"}


from app.document_permissions import PermissoesUsuario, ACOES, auditar, tem_permissao
from app.models_ged_config import UserDocumentType, DocumentType

@router.get("/users/me/document-permissions", tags=["Users"])
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    vinculos = db.query(UserDocumentType).filter_by(user_id=current_user.id).all()
    # Se for admin global, manda permissões fictícias ou avisa o front para liberar tudo.
    # Mas o front já checa `admin_global`.
    return {
        "vinculos": [{"document_type_id": v.document_type_id, "permissions": v.permissions} for v in vinculos],
        "is_admin_global": current_user.role == "admin_global"
    }


def usuario_administravel(db, administrador, usuario_id):
    usuario = db.query(models.User).filter_by(id=usuario_id).with_for_update().first()
    if usuario is None:
        raise HTTPException(404, "Usuário não encontrado.")
    if administrador.role != "admin_global":
        if (not administrador.institution_id or usuario.institution_id != administrador.institution_id
                or usuario.role == "admin_global"):
            raise HTTPException(403, "Usuário fora do escopo administrativo.")
    return usuario


@router.get("/users/{usuario_id}/document-permissions", tags=["Admin - Users"])
def consultar_permissoes(usuario_id: str, db: Session = Depends(get_db),
                         administrador: models.User = Depends(auth.get_current_admin)):
    usuario_administravel(db, administrador, usuario_id)
    vinculos = db.query(UserDocumentType).filter_by(user_id=usuario_id).all()
    tipos = db.query(DocumentType).order_by(DocumentType.name).all()
    return {
        "acoes": ACOES,
        "tipos": [{"id": t.id, "name": t.name, "is_active": t.is_active} for t in tipos],
        "vinculos": [{"document_type_id": v.document_type_id, "permissions": v.permissions} for v in vinculos],
    }


@router.put("/users/{usuario_id}/document-permissions", response_model=PermissoesUsuario, tags=["Admin - Users"])
def salvar_permissoes(usuario_id: str, dados: PermissoesUsuario, db: Session = Depends(get_db),
                      administrador: models.User = Depends(auth.get_current_admin)):
    usuario = usuario_administravel(db, administrador, usuario_id)
    if usuario.role == "admin_global":
        raise HTTPException(409, "O administrador global possui acesso administrativo integral.")
    ids = [v.document_type_id for v in dados.vinculos]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Tipo documental duplicado.")
    for vinculo in dados.vinculos:
        if db.get(DocumentType, vinculo.document_type_id) is None:
            raise HTTPException(404, "Tipo documental não encontrado.")
        if administrador.role != "admin_global":
            for acao in vinculo.permissions:
                if not tem_permissao(db, administrador, vinculo.document_type_id, acao):
                    raise HTTPException(403, "Não é permitido conceder um privilégio que você não possui.")
    anteriores = db.query(UserDocumentType).filter_by(user_id=usuario_id).all()
    import json
    antes = [{"document_type_id": v.document_type_id, "permissions": v.permissions} for v in anteriores]
    for vinculo in anteriores:
        db.delete(vinculo)
    for vinculo in dados.vinculos:
        db.add(UserDocumentType(user_id=usuario_id, document_type_id=vinculo.document_type_id,
                                permissions=sorted(set(vinculo.permissions))))
    auditar(db, administrador, "usuario", usuario_id, "permissoes_documentais_alteradas",
            json.dumps({"antes": antes, "depois": dados.model_dump()}, ensure_ascii=False))
    db.commit()
    return dados
