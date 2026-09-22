from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.search import SearchService

from typing import Any, Dict, Optional
from app.schemas_pagination import PaginatedResponse

from app.auth import get_current_active_user
from app.models import User
from app.models_ged import GEDDocument, GEDDocumentIndexValue
from app.models_ged_config import (
    UserDocumentType,
    GedIndex,
    DocumentType,
    DocumentTypeIndex,
)

router = APIRouter()
search_service = SearchService()

@router.get("/api/documents/search/types", tags=["GED - Busca Full-Text"])
def search_document_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retorna os tipos e índices que o usuário pode consultar."""
    query = db.query(DocumentType).filter(DocumentType.is_active.is_(True))
    if current_user.role != "admin_global":
        if not current_user.institution_id:
            return []
        allowed_type_ids = [
            record.document_type_id
            for record in db.query(UserDocumentType).filter(
                UserDocumentType.user_id == current_user.id
            ).all()
            if "consultar" in (record.permissions or [])
        ]
        if not allowed_type_ids:
            return []
        query = query.filter(DocumentType.id.in_(allowed_type_ids))

    types = query.order_by(DocumentType.name.asc()).all()
    type_ids = [item.id for item in types]
    links = (
        db.query(DocumentTypeIndex, GedIndex)
        .join(GedIndex, GedIndex.id == DocumentTypeIndex.index_id)
        .filter(
            DocumentTypeIndex.document_type_id.in_(type_ids),
            GedIndex.is_active.is_(True),
        )
        .all()
        if type_ids else []
    )
    indices_by_type = {}
    for link, index in links:
        indices_by_type.setdefault(link.document_type_id, []).append({
            "id": index.id,
            "name": index.name,
            "type": index.type,
            "options": index.options or [],
            "mask": index.mask,
        })

    return [
        {
            "id": item.id,
            "name": item.name,
            "group_id": item.group_id,
            "indices": indices_by_type.get(item.id, []),
        }
        for item in types
    ]

@router.get("/api/documents/search", tags=["GED - Busca Full-Text"], response_model=PaginatedResponse[Dict[str, Any]])
def search_documents(
    q: Optional[str] = Query(""),
    page: int = 1,
    size: int = 50,
    student_id: Optional[str] = None,
    group_id: Optional[str] = None,
    document_type_id: Optional[str] = None,
    index_id: Optional[str] = None,
    index_value: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Busca rápida em PostgreSQL cruzando título, OCR e metadados.

    Suporta filtros por aluno, grupo e tipo documental.
    """
    allowed_types = None
    if current_user.role != "admin_global":
        allowed_records = db.query(UserDocumentType).filter(UserDocumentType.user_id == current_user.id).all()
        allowed_types = [r.document_type_id for r in allowed_records if "consultar" in (r.permissions or [])]
        if not current_user.institution_id:
            allowed_types = []

    return search_service.search(
        db=db,
        query_string=q,
        user=current_user,
        allowed_document_type_ids=allowed_types,
        page=page,
        size=size,
        student_id=student_id,
        group_id=group_id,
        document_type_id=document_type_id,
        index_id=index_id,
        index_value=index_value,
    )

@router.get("/api/documents/student/{student_id}", tags=["GED - Busca Full-Text"])
def list_documents_by_student(
    student_id: str,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not student_id:
        raise HTTPException(400, detail="student_id obrigatório")
    allowed_types = None
    if current_user.role != "admin_global":
        allowed_records = db.query(UserDocumentType).filter(UserDocumentType.user_id == current_user.id).all()
        allowed_types = [r.document_type_id for r in allowed_records if "consultar" in (r.permissions or [])]
    rows = db.query(GEDDocument).filter(GEDDocument.student_id == student_id)
    if current_user.role != "admin_global":
        if current_user.institution_id:
            rows = rows.filter(GEDDocument.institution_id == current_user.institution_id)
        if allowed_types is not None:
            rows = rows.filter(GEDDocument.category_id.in_(allowed_types))
    rows = rows.order_by(GEDDocument.created_at.desc()).offset((page - 1) * size).limit(size)
    return [{
        "document_id": item.id,
        "title": item.title,
        "student_id": item.student_id,
        "status": item.status.value if hasattr(item.status, "value") else item.status,
        "created_at": item.created_at,
        "document_purpose": item.document_purpose,
    } for item in rows.all()]

@router.get("/api/documents/group/{group_id}", tags=["GED - Busca Full-Text"])
def list_documents_by_group(
    group_id: str,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not group_id:
        raise HTTPException(400, detail="group_id obrigatório")
    rows = db.query(GEDDocument).filter(
        GEDDocument.extracted_metadata.ilike(f'%"group_id":"{group_id}"%')
    )
    if current_user.role != "admin_global":
        if current_user.institution_id:
            rows = rows.filter(GEDDocument.institution_id == current_user.institution_id)
    rows = rows.order_by(GEDDocument.created_at.desc()).offset((page - 1) * size).limit(size)
    return [{
        "document_id": item.id,
        "title": item.title,
        "student_id": item.student_id,
        "status": item.status.value if hasattr(item.status, "value") else item.status,
        "created_at": item.created_at,
    } for item in rows.all()]
