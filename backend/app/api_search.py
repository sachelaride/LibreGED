from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.search import SearchService

import json
from typing import Any, Dict, Literal, Optional
from app.schemas_pagination import PaginatedResponse

from app.auth import get_current_active_user
from app.models import User
from app.models_ged import GEDDocument, GEDDocumentIndexValue
from app.models_ged_config import (
    GedIndex,
    DocumentType,
    DocumentTypeIndex,
    DocumentClassification,
)

router = APIRouter()
search_service = SearchService()


def tipos_com_permissao_consulta(db: Session, usuario: User) -> list[str]:
    if usuario.role == "admin_global":
        return [tipo_id for tipo_id, in db.query(DocumentType.id).all()]
    if not usuario.institution_id:
        return []
    from app.document_permissions import tem_permissao
    return [
        tipo.id for tipo in db.query(DocumentType).filter(DocumentType.is_active.is_(True)).all()
        if tem_permissao(db, usuario, tipo.id, "consultar")
    ]


@router.get("/api/documents/search/types", tags=["GED - Busca Full-Text"])
def search_document_types(
    permission: Literal["consultar", "cadastrar"] = Query("consultar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retorna os tipos e índices permitidos para consulta ou cadastro."""
    query = db.query(DocumentType).filter(DocumentType.is_active.is_(True))
    if current_user.role != "admin_global":
        if not current_user.institution_id:
            return []
    from app.document_permissions import tem_permissao
    types = [
        item for item in query.order_by(DocumentType.name.asc()).all()
        if tem_permissao(db, current_user, item.id, permission)
    ]
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
        index_data = {
            "id": index.id,
            "name": index.name,
            "type": index.type,
            "options": index.options or [],
            "mask": index.mask,
            "default_value": index.default_value,
            "is_searchable": index.is_searchable,
            "auto_increment": index.auto_increment,
        }
        indices_by_type.setdefault(link.document_type_id, []).append({
            **index_data,
            "index": index_data,
            "is_required": link.is_required,
        })

    return [
        {
            "id": item.id,
            "name": item.name,
            "group_id": item.group_id,
            "indices": indices_by_type.get(item.id, []),
            "classifications": [
                {"id": classification.id, "name": classification.name}
                for classification in db.query(DocumentClassification).filter_by(
                    document_type_id=item.id, is_active=True
                ).order_by(DocumentClassification.name.asc()).all()
            ],
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
    classification_id: Optional[str] = None,
    index_id: Optional[str] = None,
    index_value: Optional[str] = None,
    index_filters: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Busca rápida em PostgreSQL cruzando título, OCR e metadados.

    Suporta filtros por aluno, grupo e tipo documental.
    """
    allowed_types = None if current_user.role == "admin_global" else tipos_com_permissao_consulta(db, current_user)
    if document_type_id and allowed_types is not None and document_type_id not in allowed_types:
        raise HTTPException(403, "Sem permissão para consultar este tipo documental.")
    if classification_id:
        classification_query = db.query(DocumentClassification).filter(
            DocumentClassification.id == classification_id,
            DocumentClassification.is_active.is_(True),
        )
        if document_type_id:
            classification_query = classification_query.filter(
                DocumentClassification.document_type_id == document_type_id
            )
        elif allowed_types is not None:
            classification_query = classification_query.filter(
                DocumentClassification.document_type_id.in_(allowed_types)
            )
        if classification_query.first() is None:
            raise HTTPException(422, "Classificação inválida ou não autorizada.")

    try:
        filters = json.loads(index_filters) if index_filters else []
    except json.JSONDecodeError as erro:
        raise HTTPException(422, "index_filters deve conter JSON válido.") from erro
    if not isinstance(filters, list):
        raise HTTPException(422, "index_filters deve ser uma lista.")
    if index_id or index_value:
        if not index_id or not index_value:
            raise HTTPException(422, "Informe o índice e o valor para pesquisar.")
        filters.append({"index_id": index_id, "value": index_value})
    if any(
        not isinstance(filtro, dict)
        or set(filtro) != {"index_id", "value"}
        or not isinstance(filtro["index_id"], str)
        or not isinstance(filtro["value"], str)
        or not filtro["value"].strip()
        for filtro in filters
    ):
        raise HTTPException(422, "Cada filtro deve conter um index_id e um value não vazio.")
    if len({filtro["index_id"] for filtro in filters}) != len(filters):
        raise HTTPException(422, "Não repita índices na pesquisa.")

    if filters:
        permitted_type_ids = (
            [document_type_id] if document_type_id else
            allowed_types if allowed_types is not None else
            [tipo_id for tipo_id, in db.query(DocumentType.id).all()]
        )
        valid_index_ids = {
            index_id
            for index_id, in db.query(DocumentTypeIndex.index_id)
            .join(GedIndex, GedIndex.id == DocumentTypeIndex.index_id)
            .filter(
                DocumentTypeIndex.document_type_id.in_(permitted_type_ids),
                GedIndex.is_searchable.is_(True),
                GedIndex.is_active.is_(True),
            ).all()
        } if permitted_type_ids else set()
        if any(filtro["index_id"] not in valid_index_ids for filtro in filters):
            raise HTTPException(422, "Índice inexistente, não pesquisável ou não vinculado ao tipo autorizado.")

    resultado = search_service.search(
        db=db,
        query_string=q,
        user=current_user,
        allowed_document_type_ids=allowed_types,
        page=page,
        size=size,
        student_id=student_id,
        group_id=group_id,
        document_type_id=document_type_id,
        classification_id=classification_id,
        index_id=index_id,
        index_value=index_value,
        index_filters=filters,
    )
    from app.document_permissions import tem_permissao
    for item in resultado["items"]:
        tipo_id = item.get("document_type", {}).get("id") if item.get("document_type") else None
        item["can_download"] = bool(
            tipo_id and (
                current_user.role == "admin_global"
                or tem_permissao(db, current_user, tipo_id, "download")
            )
        )
    return resultado

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
    allowed_types = None if current_user.role == "admin_global" else tipos_com_permissao_consulta(db, current_user)
    rows = db.query(GEDDocument).filter(GEDDocument.student_id == student_id)
    if current_user.role != "admin_global":
        if current_user.institution_id:
            rows = rows.filter(GEDDocument.institution_id == current_user.institution_id)
        if current_user.campus_id:
            rows = rows.filter(GEDDocument.campus_id == current_user.campus_id)
        if allowed_types is not None:
            rows = rows.filter(GEDDocument.category_id.in_(allowed_types))
        if not current_user.institution_id or not allowed_types:
            rows = rows.filter(False)
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
        allowed_types = tipos_com_permissao_consulta(db, current_user)
        if current_user.institution_id:
            rows = rows.filter(GEDDocument.institution_id == current_user.institution_id)
        if current_user.campus_id:
            rows = rows.filter(GEDDocument.campus_id == current_user.campus_id)
        if allowed_types:
            rows = rows.filter(GEDDocument.category_id.in_(allowed_types))
        else:
            rows = rows.filter(False)
    rows = rows.order_by(GEDDocument.created_at.desc()).offset((page - 1) * size).limit(size)
    return [{
        "document_id": item.id,
        "title": item.title,
        "student_id": item.student_id,
        "status": item.status.value if hasattr(item.status, "value") else item.status,
        "created_at": item.created_at,
    } for item in rows.all()]
