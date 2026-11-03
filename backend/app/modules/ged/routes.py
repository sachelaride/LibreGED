from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, models_ged
from app.auth import require_module_access
from app.database import get_db
from app.modules.data_store import documents

router = APIRouter(prefix="/ged", tags=["GED"])


def _db_scope_query(db: Session, user: Any):
    query = db.query(models_ged.GEDDocument)
    institution_id = getattr(user, "institution_id", None)
    if institution_id:
        query = query.filter(models_ged.GEDDocument.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        query = query.filter(models_ged.GEDDocument.campus_id == campus_id)
    return query


def _status_mapping(raw_status: str | None):
    normalized = (raw_status or "recebido").lower()
    mapping = {
        "recebido": models_ged.GEDDocumentStatus.PENDENTE_VALIDACAO,
        "pendente": models_ged.GEDDocumentStatus.PENDENTE_VALIDACAO,
        "validado": models_ged.GEDDocumentStatus.VALIDO,
        "aprovado": models_ged.GEDDocumentStatus.VALIDO,
        "rejeitado": models_ged.GEDDocumentStatus.REJEITADO,
        "arquivado": models_ged.GEDDocumentStatus.ARQUIVADO,
        "rascunho": models_ged.GEDDocumentStatus.RASCUNHO,
    }
    return mapping.get(normalized, models_ged.GEDDocumentStatus.PENDENTE_VALIDACAO)


def _serialize_document(doc: models_ged.GEDDocument) -> dict[str, Any]:
    return {
        "document_id": doc.id,
        "title": doc.title,
        "file_name": doc.file_path.split("/")[-1] if doc.file_path else "documento.pdf",
        "document_type": doc.category.name if doc.category else "Acadêmico",
        "owner": doc.uploaded_by_user_id or "Secretaria Acadêmica",
        "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        "version": "v1",
        "category": doc.category.name if doc.category else "Acadêmico",
        "retention": "5 anos",
    }


class DocumentUpload(BaseModel):
    title: str
    file_name: str
    document_type: str
    owner: str | None = None
    status: str | None = None
    version: str | None = None
    category: str | None = None
    retention: str | None = None
    student_id: str | None = None


@router.get("/dashboard")
def ged_dashboard(user: Any = Depends(require_module_access("ged")), db: Session = Depends(get_db)):
    records = _db_scope_query(db, user).all()
    if not records:
        records = list(documents.values())
        return {
            "module": "ged",
            "title": "Dashboard do GED",
            "stats": {
                "documentos": len(records),
                "validados": sum(1 for d in records if d.get("status") == "validado"),
                "pendentes": sum(1 for d in records if d.get("status") != "validado"),
                "versoes_ativas": sum(1 for d in records if d.get("version") == "v2"),
                "classe_documental": "Acadêmico",
            },
            "features": [
                "Upload e versionamento",
                "Validação documental",
                "Assinatura e auditoria",
                "Retenção e organização",
                "Controle de ciclo de vida",
            ],
            "user": getattr(user, "username", None),
        }

    return {
        "module": "ged",
        "title": "Dashboard do GED",
        "stats": {
            "documentos": len(records),
            "validados": sum(1 for d in records if getattr(d, "status", None) == models_ged.GEDDocumentStatus.VALIDO),
            "pendentes": sum(1 for d in records if getattr(d, "status", None) != models_ged.GEDDocumentStatus.VALIDO),
            "versoes_ativas": 0,
            "classe_documental": "Acadêmico",
        },
        "features": [
            "Upload e versionamento",
            "Validação documental",
            "Assinatura e auditoria",
            "Retenção e organização",
            "Controle de ciclo de vida",
        ],
        "user": getattr(user, "username", None),
    }


@router.get("/documentos")
def list_documents(user: Any = Depends(require_module_access("ged")), db: Session = Depends(get_db)):
    records = _db_scope_query(db, user).all()
    if records:
        return {"module": "ged", "items": [_serialize_document(doc) for doc in records]}
    return {"module": "ged", "items": list(documents.values())}


@router.get("/documentos/{document_id}")
def get_document(document_id: str, user: Any = Depends(require_module_access("ged")), db: Session = Depends(get_db)):
    doc = _db_scope_query(db, user).filter(models_ged.GEDDocument.id == document_id).first()
    if not doc:
        legacy = documents.get(document_id)
        if not legacy:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        return {"module": "ged", "document": legacy}
    return {"module": "ged", "document": _serialize_document(doc)}


@router.post("/documentos/upload")
def upload_document(payload: DocumentUpload, user: Any = Depends(require_module_access("ged")), db: Session = Depends(get_db)):
    institution_id = getattr(user, "institution_id", None)
    campus_id = getattr(user, "campus_id", None)
    category_name = payload.category or payload.document_type or "Acadêmico"
    category = db.query(models_ged.DocumentCategory).filter(models_ged.DocumentCategory.name == category_name).first()
    if not category:
        category = models_ged.DocumentCategory(
            id=str(uuid4()),
            index_code=f"CAT-{len(db.query(models_ged.DocumentCategory).all()) + 1:03d}",
            name=category_name,
            description="Categoria criada automaticamente pelo fluxo GED.",
            is_active=1,
        )
        db.add(category)
        db.commit()
        db.refresh(category)

    document_id = str(uuid4())
    doc = models_ged.GEDDocument(
        id=document_id,
        title=payload.title,
        file_path=f"/uploads/{payload.file_name}",
        file_hash=None,
        status=_status_mapping(payload.status),
        category_id=category.id,
        student_id=payload.student_id,
        institution_id=institution_id,
        campus_id=campus_id,
        uploaded_by_user_id=getattr(user, "id", None),
        document_purpose="official",
        is_official=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    serialized = _serialize_document(doc)
    return {"message": "Documento registrado no GED", "module": "ged", "document": serialized}
