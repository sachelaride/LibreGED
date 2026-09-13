from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.database import get_db
from app import models, models_ged_config
from app import auth
from app.schemas_ged_config import (
    GedIndexCreate, GedIndexResponse,
    DocumentTypeCreate, DocumentTypeResponse,
    DocumentTypeIndexCreate, DocumentTypeIndexResponse,
    DocumentTypeVersionCreate, DocumentTypeVersionResponse
)
from app.schemas_pagination import PaginatedResponse
import math

router = APIRouter()

# --- INDICES ---

@router.get("/indices", response_model=PaginatedResponse[GedIndexResponse], tags=["Admin - GED Config"])
def get_indices(page: int = 1, size: int = 50, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    query = db.query(models_ged_config.GedIndex)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/indices", response_model=GedIndexResponse, tags=["Admin - GED Config"])
def create_index(index_in: GedIndexCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.role_checker(["admin_global"]))):
    from app.index_validation import validar_configuracao_indice
    validar_configuracao_indice(
        index_in.type, index_in.options, index_in.mask, index_in.auto_increment)
    new_index = models_ged_config.GedIndex(
        name=index_in.name,
        type=index_in.type,
        is_active=index_in.is_active,
        options=index_in.options,
        mask=index_in.mask,
        auto_increment=index_in.auto_increment,
    )
    new_index.id = str(uuid.uuid4())
    db.add(new_index)
    auditar(db, current_user, "indice", new_index.id, "criar", index_in.model_dump_json())
    concluir_configuracao(db)
    db.refresh(new_index)
    return new_index

# --- DOCUMENT TYPES ---

@router.get("/document-types", response_model=PaginatedResponse[DocumentTypeResponse], tags=["Admin - GED Config"])
def get_document_types(page: int = 1, size: int = 50, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    query = db.query(models_ged_config.DocumentType)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/document-types", response_model=DocumentTypeResponse, tags=["Admin - GED Config"])
def create_document_type(doc_type_in: DocumentTypeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.role_checker(["admin_global"]))):
    persisted_user_id = db.query(models.User.id).filter(models.User.id == current_user.id).scalar()
    if db.query(models_ged_config.DocumentType).filter_by(name=doc_type_in.name).first():
        raise HTTPException(409, "Tipo documental já cadastrado.")
    new_doc_type = models_ged_config.DocumentType(
        name=doc_type_in.name,
        workflow_id=doc_type_in.workflow_id,
        is_active=doc_type_in.is_active,
        group_id=doc_type_in.group_id,
        retention_years=doc_type_in.retention_years,
        legal_hold=doc_type_in.legal_hold,
        access_policy=doc_type_in.access_policy,
        signature_rule=doc_type_in.signature_rule,
        active_version=1,
        storage_area_id=doc_type_in.storage_area_id,
        storage_partition_id=doc_type_in.storage_partition_id
    )
    db.add(new_doc_type)
    db.flush()
    db.add(models_ged_config.DocumentTypeVersion(
        document_type_id=new_doc_type.id,
        version=1,
        status="ACTIVE",
        name=new_doc_type.name,
        workflow_id=new_doc_type.workflow_id,
        group_id=new_doc_type.group_id,
        retention_years=new_doc_type.retention_years,
        legal_hold=new_doc_type.legal_hold,
        access_policy=new_doc_type.access_policy,
        signature_rule=new_doc_type.signature_rule,
        created_by=persisted_user_id,
    ))
    concluir_configuracao(db)
    db.refresh(new_doc_type)
    return new_doc_type

@router.get("/document-types/{doc_type_id}/versions", response_model=List[DocumentTypeVersionResponse], tags=["Admin - GED Config"])
def get_document_type_versions(doc_type_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    return db.query(models_ged_config.DocumentTypeVersion).filter(
        models_ged_config.DocumentTypeVersion.document_type_id == doc_type_id
    ).order_by(models_ged_config.DocumentTypeVersion.version.desc()).all()

@router.post("/document-types/{doc_type_id}/versions", response_model=DocumentTypeVersionResponse, tags=["Admin - GED Config"])
def create_document_type_version(doc_type_id: str, version_in: DocumentTypeVersionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.role_checker(["admin_global"]))):
    doc_type = db.query(models_ged_config.DocumentType).filter(models_ged_config.DocumentType.id == doc_type_id).first()
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")

    persisted_user_id = db.query(models.User.id).filter(models.User.id == current_user.id).scalar()
    next_version = (db.query(models_ged_config.DocumentTypeVersion.version)
        .filter(models_ged_config.DocumentTypeVersion.document_type_id == doc_type_id)
        .order_by(models_ged_config.DocumentTypeVersion.version.desc()).first())
    version_number = (next_version[0] if next_version else 0) + 1
    version = models_ged_config.DocumentTypeVersion(
        document_type_id=doc_type_id,
        version=version_number,
        status="DRAFT",
        created_by=persisted_user_id,
        **version_in.model_dump(exclude={"is_active"})
    )
    db.add(version)
    concluir_configuracao(db)
    db.refresh(version)
    return version

@router.post("/document-types/{doc_type_id}/versions/{version}/activate", response_model=DocumentTypeVersionResponse, tags=["Admin - GED Config"])
def activate_document_type_version(doc_type_id: str, version: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.role_checker(["admin_global"]))):
    doc_type = db.query(models_ged_config.DocumentType).filter(models_ged_config.DocumentType.id == doc_type_id).first()
    selected = db.query(models_ged_config.DocumentTypeVersion).filter(
        models_ged_config.DocumentTypeVersion.document_type_id == doc_type_id,
        models_ged_config.DocumentTypeVersion.version == version,
    ).first()
    if not doc_type or not selected:
        raise HTTPException(status_code=404, detail="Document type version not found")

    for item in doc_type.versions:
        if item.status == "ACTIVE":
            item.status = "SUPERSEDED"
            item.effective_until = selected.effective_from

    selected.status = "ACTIVE"
    doc_type.active_version = selected.version
    doc_type.name = selected.name
    doc_type.workflow_id = selected.workflow_id
    doc_type.group_id = selected.group_id
    doc_type.retention_years = selected.retention_years
    doc_type.legal_hold = selected.legal_hold
    doc_type.access_policy = selected.access_policy
    doc_type.signature_rule = selected.signature_rule
    concluir_configuracao(db)
    db.refresh(selected)
    return selected

@router.post("/document-types/{doc_type_id}/indices", response_model=DocumentTypeIndexResponse, tags=["Admin - GED Config"])
def add_index_to_document_type(doc_type_id: str, mapping_in: DocumentTypeIndexCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.role_checker(["admin_global"]))):
    obter_registro(db, models_ged_config.DocumentType, doc_type_id)
    obter_registro(db, models_ged_config.GedIndex, mapping_in.index_id)
    if db.query(models_ged_config.DocumentTypeIndex).filter_by(document_type_id=doc_type_id, index_id=mapping_in.index_id).first():
        raise HTTPException(409, "Índice já vinculado ao tipo documental.")
    mapping = models_ged_config.DocumentTypeIndex(
        document_type_id=doc_type_id,
        index_id=mapping_in.index_id,
        is_required=mapping_in.is_required,
        is_unique=mapping_in.is_unique
    )
    db.add(mapping)
    auditar(db, current_user, "tipo_documental", doc_type_id, "vincular_indice", mapping_in.model_dump_json())
    concluir_configuracao(db)
    db.refresh(mapping)
    return mapping


from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from app.document_permissions import auditar
from app.models_ged import GEDDocument, GEDDocumentIndexValue


class EdicaoIndice(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    options: List[str] = Field(default_factory=list)
    mask: Optional[str] = Field(default=None, max_length=200)
    auto_increment: bool = False
    is_active: bool = True


class EdicaoTipo(DocumentTypeCreate):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def concluir_configuracao(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Registro duplicado ou vinculado a outros cadastros.")


def obter_registro(db, modelo, identificador):
    registro = db.query(modelo).filter_by(id=identificador).with_for_update().first()
    if registro is None:
        raise HTTPException(404, "Registro não encontrado.")
    return registro


@router.put("/indices/{indice_id}", response_model=GedIndexResponse, tags=["Admin - GED Config"])
def editar_indice(indice_id: str, dados: EdicaoIndice, db: Session = Depends(get_db),
                  usuario: models.User = Depends(auth.role_checker(["admin_global"]))):
    from app.index_validation import validar_configuracao_indice
    validar_configuracao_indice(dados.type, dados.options, dados.mask, dados.auto_increment)
    indice = obter_registro(db, models_ged_config.GedIndex, indice_id)
    if indice.type != dados.type and db.query(GEDDocumentIndexValue).filter_by(index_id=indice_id).first():
        raise HTTPException(409, "O tipo de dado não pode mudar após receber valores documentais.")
    for campo, valor in dados.model_dump().items():
        setattr(indice, campo, valor)
    auditar(db, usuario, "indice", indice_id, "editar", dados.model_dump_json())
    concluir_configuracao(db)
    return indice


@router.delete("/indices/{indice_id}", status_code=204, tags=["Admin - GED Config"])
def excluir_indice(indice_id: str, db: Session = Depends(get_db),
                   usuario: models.User = Depends(auth.role_checker(["admin_global"]))):
    indice = obter_registro(db, models_ged_config.GedIndex, indice_id)
    if (db.query(models_ged_config.DocumentTypeIndex).filter_by(index_id=indice_id).first()
            or db.query(GEDDocumentIndexValue).filter_by(index_id=indice_id).first()):
        raise HTTPException(409, "Índice em uso. Desative-o ou remova seus vínculos antes de excluir.")
    auditar(db, usuario, "indice", indice_id, "excluir", indice.name)
    db.delete(indice)
    concluir_configuracao(db)


@router.put("/document-types/{tipo_id}", response_model=DocumentTypeResponse, tags=["Admin - GED Config"])
def editar_tipo(tipo_id: str, dados: EdicaoTipo, db: Session = Depends(get_db),
                usuario: models.User = Depends(auth.role_checker(["admin_global"]))):
    tipo = obter_registro(db, models_ged_config.DocumentType, tipo_id)
    if db.query(models_ged_config.DocumentType).filter(
            models_ged_config.DocumentType.name == dados.name,
            models_ged_config.DocumentType.id != tipo_id).first():
        raise HTTPException(409, "Já existe outro tipo documental com esse nome.")
    numero = max((v.version for v in tipo.versions), default=0) + 1
    agora = models.utc_now()
    for versao in tipo.versions:
        if versao.status == "ACTIVE":
            versao.status = "SUPERSEDED"
            versao.effective_until = agora
    tipo.name = dados.name
    tipo.workflow_id = dados.workflow_id
    tipo.is_active = dados.is_active
    tipo.group_id = dados.group_id
    tipo.retention_years = dados.retention_years
    tipo.legal_hold = dados.legal_hold
    tipo.access_policy = dados.access_policy
    tipo.signature_rule = dados.signature_rule
    tipo.storage_area_id = dados.storage_area_id
    tipo.storage_partition_id = dados.storage_partition_id
    tipo.active_version = numero
    autor = db.get(models.User, usuario.id)
    db.add(models_ged_config.DocumentTypeVersion(
        document_type_id=tipo_id, version=numero, status="ACTIVE", name=tipo.name,
        workflow_id=tipo.workflow_id, group_id=tipo.group_id, retention_years=tipo.retention_years,
        legal_hold=tipo.legal_hold, access_policy=tipo.access_policy, signature_rule=tipo.signature_rule,
        effective_from=agora, created_by=autor.id if autor else None))
    auditar(db, usuario, "tipo_documental", tipo_id, "editar", dados.model_dump_json())
    concluir_configuracao(db)
    return tipo


@router.delete("/document-types/{tipo_id}", status_code=204, tags=["Admin - GED Config"])
def excluir_tipo(tipo_id: str, db: Session = Depends(get_db),
                 usuario: models.User = Depends(auth.role_checker(["admin_global"]))):
    tipo = obter_registro(db, models_ged_config.DocumentType, tipo_id)
    if (db.query(GEDDocument).filter_by(category_id=tipo_id).first()
            or db.query(models_ged_config.UserDocumentType).filter_by(document_type_id=tipo_id).first()):
        raise HTTPException(409, "Tipo documental em uso. Desative-o para preservar os vínculos.")
    auditar(db, usuario, "tipo_documental", tipo_id, "excluir", tipo.name)
    db.delete(tipo)
    concluir_configuracao(db)


@router.get("/document-types/{tipo_id}/indices", response_model=List[DocumentTypeIndexResponse], tags=["Admin - GED Config"])
def consultar_indices_tipo(tipo_id: str, db: Session = Depends(get_db),
                           usuario: models.User = Depends(auth.get_current_admin)):
    obter_registro(db, models_ged_config.DocumentType, tipo_id)
    return db.query(models_ged_config.DocumentTypeIndex).filter_by(document_type_id=tipo_id).all()


@router.put("/document-types/{tipo_id}/indices/{vinculo_id}", response_model=DocumentTypeIndexResponse, tags=["Admin - GED Config"])
def editar_vinculo_indice(tipo_id: str, vinculo_id: str, dados: DocumentTypeIndexCreate,
                          db: Session = Depends(get_db), usuario: models.User = Depends(auth.role_checker(["admin_global"]))):
    vinculo = obter_registro(db, models_ged_config.DocumentTypeIndex, vinculo_id)
    if vinculo.document_type_id != tipo_id:
        raise HTTPException(404, "Vínculo não encontrado neste tipo documental.")
    if vinculo.index_id != dados.index_id:
        raise HTTPException(422, "Para trocar o Índice, remova o vínculo e adicione outro.")
    vinculo.is_required, vinculo.is_unique = dados.is_required, dados.is_unique
    auditar(db, usuario, "tipo_documental", tipo_id, "editar_indice", dados.model_dump_json())
    concluir_configuracao(db)
    return vinculo


@router.delete("/document-types/{tipo_id}/indices/{vinculo_id}", status_code=204, tags=["Admin - GED Config"])
def remover_vinculo_indice(tipo_id: str, vinculo_id: str, db: Session = Depends(get_db),
                           usuario: models.User = Depends(auth.role_checker(["admin_global"]))):
    vinculo = obter_registro(db, models_ged_config.DocumentTypeIndex, vinculo_id)
    if vinculo.document_type_id != tipo_id:
        raise HTTPException(404, "Vínculo não encontrado neste tipo documental.")
    if db.query(GEDDocumentIndexValue).join(GEDDocument, GEDDocument.id == GEDDocumentIndexValue.document_id).filter(
            GEDDocument.category_id == tipo_id, GEDDocumentIndexValue.index_id == vinculo.index_id).first():
        raise HTTPException(409, "O vínculo possui valores em documentos e deve ser preservado.")
    auditar(db, usuario, "tipo_documental", tipo_id, "remover_indice", vinculo.index_id)
    db.delete(vinculo)
    concluir_configuracao(db)
