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
    DocumentTypeIndexCreate, DocumentTypeIndexResponse
)

router = APIRouter()

# --- INDICES ---

@router.get("/indices", response_model=List[GedIndexResponse], tags=["Admin - GED Config"])
def get_indices(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    return db.query(models_ged_config.GedIndex).all()

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

@router.get("/document-types", response_model=List[DocumentTypeResponse], tags=["Admin - GED Config"])
def get_document_types(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    return db.query(models_ged_config.DocumentType).all()

@router.post("/document-types", response_model=DocumentTypeResponse, tags=["Admin - GED Config"])
def create_document_type(doc_type_in: DocumentTypeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    new_doc_type = models_ged_config.DocumentType(
        name=doc_type_in.name,
        storage_area_id=doc_type_in.storage_area_id,
        storage_partition_id=doc_type_in.storage_partition_id,
        is_active=doc_type_in.is_active
    )
    db.add(new_doc_type)
    db.commit()
    db.refresh(new_doc_type)
    return new_doc_type

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
