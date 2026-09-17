import json
import math
from typing import Dict, List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models_ged import GEDDocument


class SearchService:
    """Busca documental compatível com PostgreSQL e sem tabelas virtuais locais."""

    def index_document(self, db: Session, document_id: str, title: str, content: str, indices_data: str):
        """Mantém compatibilidade com o fluxo de upload.

        Os dados pesquisáveis vivem no próprio documento; o conteúdo extraído
        pode ser persistido em ``extracted_metadata`` pelo pipeline de OCR.
        """
        document = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
        if not document:
            return False

        structured = {}
        if document.extracted_metadata:
            try:
                structured = json.loads(document.extracted_metadata)
            except Exception:
                structured = {"raw_text": document.extracted_metadata}

        if isinstance(structured, dict):
            structured.update({
                "ocr_text": content,
                "indices": json.loads(indices_data) if indices_data else structured.get("indices", []),
            })
            document.extracted_metadata = json.dumps(structured, ensure_ascii=False)
        else:
            document.extracted_metadata = f"{content}\n{indices_data}".strip()
        db.commit()
        return True

    def search(
        self,
        db: Session,
        query_string: str,
        user=None,
        allowed_document_type_ids: List[str] = None,
        page: int = 1,
        size: int = 50,
        student_id: str = None,
        group_id: str = None,
        document_type_id: str = None,
    ) -> Dict:
        if page < 1 or size < 1:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}

        normalized_query = (query_string or "").strip()
        if user and user.role != "admin_global" and allowed_document_type_ids == []:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}
        if not normalized_query and not student_id and not group_id and not document_type_id:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}

        query = db.query(GEDDocument).filter(
            GEDDocument.status.notin_(("SUSPENSO", "REVOGADO", "ANULADO"))
        )

        if normalized_query:
            pattern = f"%{normalized_query}%"
            query = query.filter(
                or_(
                    GEDDocument.title.ilike(pattern),
                    GEDDocument.extracted_metadata.ilike(pattern),
                )
            )

        if student_id:
            query = query.filter(
                or_(
                    GEDDocument.student_id == student_id,
                    GEDDocument.extracted_metadata.ilike(f'%"student_id":"{student_id}"%'),
                    GEDDocument.extracted_metadata.ilike(f'%{student_id}%')
                )
            )

        if group_id:
            query = query.filter(
                or_(
                    GEDDocument.extracted_metadata.ilike(f'%{group_id}%'),
                    GEDDocument.title.ilike(f'%{group_id}%')
                )
            )

        if document_type_id:
            query = query.filter(GEDDocument.category_id == document_type_id)

        if user and user.role != "admin_global":
            if user.institution_id:
                query = query.filter(GEDDocument.institution_id == user.institution_id)
            if user.campus_id:
                query = query.filter(GEDDocument.campus_id == user.campus_id)
            if allowed_document_type_ids is not None:
                query = query.filter(GEDDocument.category_id.in_(allowed_document_type_ids))

        total = query.count()
        documents = (
            query.order_by(GEDDocument.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        hits = []
        for document in documents:
            metadata = {}
            if document.extracted_metadata:
                try:
                    parsed_metadata = json.loads(document.extracted_metadata)
                    if isinstance(parsed_metadata, dict):
                        metadata = parsed_metadata
                except json.JSONDecodeError:
                    metadata = {}
            searchable_text = metadata.get("ocr_text") or document.title
            hits.append({
                "document_id": document.id,
                "title": document.title,
                "document_purpose": document.document_purpose,
                "is_official": document.is_official,
                "student_id": document.student_id,
                "group_id": metadata.get("group_id"),
                "status": document.status.value if hasattr(document.status, "value") else document.status,
                "snippet": searchable_text[:180],
                "ocr_engine": metadata.get("ocr_engine", "none"),
                "ocr_status": metadata.get("ocr_status", "skipped"),
            })

        return {
            "items": hits,
            "total": total,
            "page": page,
            "size": size,
            "pages": math.ceil(total / size) if total else 0,
        }


search_service = SearchService()
