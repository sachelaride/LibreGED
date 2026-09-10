from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
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
def create_index(index_in: GedIndexCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    new_index = models_ged_config.GedIndex(
        name=index_in.name,
        type=index_in.type,
        is_active=index_in.is_active
    )
    db.add(new_index)
    db.commit()
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
def create_document_type(doc_type_in: DocumentTypeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    persisted_user_id = db.query(models.User.id).filter(models.User.id == current_user.id).scalar()
    new_doc_type = models_ged_config.DocumentType(
        name=doc_type_in.name,
        workflow_id=doc_type_in.workflow_id,
        is_active=doc_type_in.is_active,
        group_id=doc_type_in.group_id,
        retention_years=doc_type_in.retention_years,
        legal_hold=doc_type_in.legal_hold,
        access_policy=doc_type_in.access_policy,
        signature_rule=doc_type_in.signature_rule,
        active_version=1
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
    db.commit()
    db.refresh(new_doc_type)
    return new_doc_type

@router.get("/document-types/{doc_type_id}/versions", response_model=List[DocumentTypeVersionResponse], tags=["Admin - GED Config"])
def get_document_type_versions(doc_type_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    return db.query(models_ged_config.DocumentTypeVersion).filter(
        models_ged_config.DocumentTypeVersion.document_type_id == doc_type_id
    ).order_by(models_ged_config.DocumentTypeVersion.version.desc()).all()

@router.post("/document-types/{doc_type_id}/versions", response_model=DocumentTypeVersionResponse, tags=["Admin - GED Config"])
def create_document_type_version(doc_type_id: str, version_in: DocumentTypeVersionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
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
    db.commit()
    db.refresh(version)
    return version

@router.post("/document-types/{doc_type_id}/versions/{version}/activate", response_model=DocumentTypeVersionResponse, tags=["Admin - GED Config"])
def activate_document_type_version(doc_type_id: str, version: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
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
    db.commit()
    db.refresh(selected)
    return selected

@router.post("/document-types/{doc_type_id}/indices", response_model=DocumentTypeIndexResponse, tags=["Admin - GED Config"])
def add_index_to_document_type(doc_type_id: str, mapping_in: DocumentTypeIndexCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    mapping = models_ged_config.DocumentTypeIndex(
        document_type_id=doc_type_id,
        index_id=mapping_in.index_id,
        is_required=mapping_in.is_required,
        is_unique=mapping_in.is_unique
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping
