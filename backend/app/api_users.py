from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
from pydantic import BaseModel

from app.database import get_db
from app import models
from app.models import Campus
from app import auth
from app.schemas_users import (
    UserCreate, UserResponse, PermissionGroupCreate, PermissionGroupUpdate,
    PermissionGroupPermission,
)
from app.schemas_pagination import PaginatedResponse
import math

router = APIRouter()

class CampusResponse(BaseModel):
    id: str
    institution_id: str
    name: str

    class Config:
        from_attributes = True

@router.get("/campuses", response_model=List[CampusResponse], tags=["Admin - Users"])
def get_campuses(
    institution_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.role_checker(["admin_global", "admin_instituicao"])),
):
    if current_user.role == "admin_global":
        query = db.query(Campus)
        if institution_id:
            query = query.filter(Campus.institution_id == institution_id)
    else:
        if not current_user.institution_id:
            return []
        query = db.query(Campus).filter(Campus.institution_id == current_user.institution_id)
    return query.order_by(Campus.name).all()

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
        if institution_id and db.get(models.Institution, institution_id) is None:
            raise HTTPException(status_code=422, detail="Instituição não encontrada.")

    if current_user.role != "admin_global" and user.role == "admin_global":
        raise HTTPException(status_code=403, detail="Apenas admin global pode criar outro admin global")
    if user.campus_id:
        campus = db.get(Campus, user.campus_id)
        if campus is None or campus.institution_id != institution_id:
            raise HTTPException(status_code=422, detail="Campus não pertence à instituição do usuário.")

    new_user = models.User(
        id=str(uuid.uuid4()),
        username=user.username,
        role=user.role,
        institution_id=institution_id,
        campus_id=user.campus_id,
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
    if user_in.campus_id:
        campus = db.get(Campus, user_in.campus_id)
        if campus is None or campus.institution_id != user.institution_id:
            raise HTTPException(status_code=422, detail="Campus não pertence à instituição do usuário.")

    if user_in.role is not None:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.campus_id is not None:
        user.campus_id = user_in.campus_id
    elif "campus_id" in user_in.model_fields_set:
        user.campus_id = None

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
from app.models_ged_config import (
    UserDocumentType, DocumentType, PermissionGroup, PermissionGroupMember,
    PermissionGroupDocumentType,
)

@router.get("/users/me/document-permissions", tags=["Users"])
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    vinculos = db.query(UserDocumentType).filter_by(user_id=current_user.id).all()
    # Se for admin global, manda permissões fictícias ou avisa o front para liberar tudo.
    # Mas o front já checa `admin_global`.
    return {
        "vinculos": [{"document_type_id": v.document_type_id, "permissions": v.permissions,
                      "denied_permissions": v.denied_permissions} for v in vinculos],
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
        if set(vinculo.permissions) & set(vinculo.denied_permissions):
            raise HTTPException(422, "Uma ação não pode ser permitida e negada no mesmo vínculo.")
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
                                permissions=sorted(set(vinculo.permissions)),
                                denied_permissions=sorted(set(vinculo.denied_permissions))))
    auditar(db, administrador, "usuario", usuario_id, "permissoes_documentais_alteradas",
            json.dumps({"antes": antes, "depois": dados.model_dump()}, ensure_ascii=False))
    db.commit()
    return dados


def grupo_administravel(db, administrador, grupo_id):
    grupo = db.get(PermissionGroup, grupo_id)
    if grupo is None:
        raise HTTPException(404, "Grupo de permissões não encontrado.")
    if administrador.role != "admin_global" and grupo.institution_id != administrador.institution_id:
        raise HTTPException(403, "Grupo fora do escopo administrativo.")
    return grupo


@router.get("/permission-groups", tags=["Admin - Users"])
def listar_grupos(db: Session = Depends(get_db),
                  administrador: models.User = Depends(auth.get_current_admin)):
    query = db.query(PermissionGroup)
    if administrador.role != "admin_global":
        query = query.filter_by(institution_id=administrador.institution_id)
    return query.order_by(PermissionGroup.name).all()


@router.post("/permission-groups", tags=["Admin - Users"])
def criar_grupo(dados: PermissionGroupCreate, db: Session = Depends(get_db),
                administrador: models.User = Depends(auth.get_current_admin)):
    if administrador.role != "admin_global" and dados.institution_id != administrador.institution_id:
        raise HTTPException(403, "Grupo fora do escopo administrativo.")
    if db.get(models.Institution, dados.institution_id) is None:
        raise HTTPException(404, "Instituição não encontrada.")
    if dados.parent_group_id:
        parent = grupo_administravel(db, administrador, dados.parent_group_id)
        if parent.institution_id != dados.institution_id:
            raise HTTPException(422, "O grupo pai deve pertencer à mesma instituição.")
        vistos = {parent.id}
        while parent.parent_group_id:
            if parent.parent_group_id in vistos or parent.parent_group_id == parent.id:
                raise HTTPException(422, "A hierarquia de grupos contém um ciclo.")
            vistos.add(parent.parent_group_id)
            parent = db.get(PermissionGroup, parent.parent_group_id)
            if parent is None:
                raise HTTPException(422, "O grupo pai da hierarquia não existe.")
    grupo = PermissionGroup(name=dados.name.strip(), institution_id=dados.institution_id,
                            parent_group_id=dados.parent_group_id)
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@router.put("/permission-groups/{grupo_id}", tags=["Admin - Users"])
def atualizar_grupo(grupo_id: str, dados: PermissionGroupUpdate, db: Session = Depends(get_db),
                    administrador: models.User = Depends(auth.get_current_admin)):
    grupo = grupo_administravel(db, administrador, grupo_id)
    if dados.name is not None:
        grupo.name = dados.name.strip()
    if "parent_group_id" in dados.model_fields_set:
        if dados.parent_group_id is None:
            grupo.parent_group_id = None
        elif dados.parent_group_id == grupo.id:
            raise HTTPException(422, "Um grupo não pode ser pai de si mesmo.")
        else:
            parent = grupo_administravel(db, administrador, dados.parent_group_id)
            if parent.institution_id != grupo.institution_id:
                raise HTTPException(422, "O grupo pai deve pertencer à mesma instituição.")
            vistos = {grupo.id}
            while parent:
                if parent.id in vistos:
                    raise HTTPException(422, "A hierarquia de grupos contém um ciclo.")
                vistos.add(parent.id)
                parent = db.get(PermissionGroup, parent.parent_group_id) if parent.parent_group_id else None
            grupo.parent_group_id = dados.parent_group_id
    db.commit()
    db.refresh(grupo)
    return grupo


@router.delete("/permission-groups/{grupo_id}", status_code=204, tags=["Admin - Users"])
def excluir_grupo(grupo_id: str, db: Session = Depends(get_db),
                  administrador: models.User = Depends(auth.get_current_admin)):
    grupo = grupo_administravel(db, administrador, grupo_id)
    if db.query(PermissionGroup).filter_by(parent_group_id=grupo.id).first():
        raise HTTPException(409, "Remova ou reoriente os grupos filhos antes de excluir.")
    db.delete(grupo)
    db.commit()
    return None


@router.put("/permission-groups/{grupo_id}/permissions", tags=["Admin - Users"])
def salvar_permissoes_grupo(grupo_id: str, dados: list[PermissionGroupPermission],
                            db: Session = Depends(get_db),
                            administrador: models.User = Depends(auth.get_current_admin)):
    grupo = grupo_administravel(db, administrador, grupo_id)
    ids = [v.document_type_id for v in dados]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Tipo documental duplicado.")
    for vinculo in dados:
        if db.get(DocumentType, vinculo.document_type_id) is None:
            raise HTTPException(404, "Tipo documental não encontrado.")
        if not set(vinculo.permissions + vinculo.denied_permissions).issubset(ACOES):
            raise HTTPException(422, "Privilégio documental desconhecido.")
        if set(vinculo.permissions) & set(vinculo.denied_permissions):
            raise HTTPException(422, "Uma ação não pode ser permitida e negada no mesmo vínculo.")
    anteriores = db.query(PermissionGroupDocumentType).filter_by(group_id=grupo.id).all()
    for anterior in anteriores:
        db.delete(anterior)
    for vinculo in dados:
        db.add(PermissionGroupDocumentType(
            group_id=grupo.id,
            document_type_id=vinculo.document_type_id,
            permissions=sorted(set(vinculo.permissions)),
            denied_permissions=sorted(set(vinculo.denied_permissions)),
        ))
    db.commit()
    return dados


@router.get("/permission-groups/{grupo_id}/permissions", tags=["Admin - Users"])
def consultar_permissoes_grupo(grupo_id: str, db: Session = Depends(get_db),
                               administrador: models.User = Depends(auth.get_current_admin)):
    grupo = grupo_administravel(db, administrador, grupo_id)
    return db.query(PermissionGroupDocumentType).filter_by(group_id=grupo.id).all()


@router.put("/users/{usuario_id}/permission-groups/{grupo_id}", status_code=204, tags=["Admin - Users"])
def adicionar_usuario_grupo(usuario_id: str, grupo_id: str, db: Session = Depends(get_db),
                            administrador: models.User = Depends(auth.get_current_admin)):
    usuario = usuario_administravel(db, administrador, usuario_id)
    grupo = grupo_administravel(db, administrador, grupo_id)
    if usuario.institution_id != grupo.institution_id:
        raise HTTPException(422, "Usuário e grupo devem pertencer à mesma instituição.")
    if db.query(PermissionGroupMember).filter_by(group_id=grupo.id, user_id=usuario.id).first() is None:
        db.add(PermissionGroupMember(group_id=grupo.id, user_id=usuario.id))
        db.commit()
    return None


@router.delete("/users/{usuario_id}/permission-groups/{grupo_id}", status_code=204, tags=["Admin - Users"])
def remover_usuario_grupo(usuario_id: str, grupo_id: str, db: Session = Depends(get_db),
                          administrador: models.User = Depends(auth.get_current_admin)):
    usuario = usuario_administravel(db, administrador, usuario_id)
    grupo = grupo_administravel(db, administrador, grupo_id)
    membro = db.query(PermissionGroupMember).filter_by(group_id=grupo.id, user_id=usuario.id).first()
    if membro:
        db.delete(membro)
        db.commit()
    return None
