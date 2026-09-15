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
    ) -> Dict:
        if not query_string or page < 1 or size < 1:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}

        normalized_query = query_string.strip()
        if not normalized_query:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}

        if user and user.role != "admin_global" and allowed_document_type_ids == []:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}

        pattern = f"%{normalized_query}%"
        query = db.query(GEDDocument).filter(
            or_(
                GEDDocument.title.ilike(pattern),
                GEDDocument.extracted_metadata.ilike(pattern),
            )
        )

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
            searchable_text = document.extracted_metadata or document.title
            hits.append({
                "document_id": document.id,
                "title": document.title,
                "snippet": searchable_text[:180],
            })

        return {
            "items": hits,
            "total": total,
            "page": page,
            "size": size,
            "pages": math.ceil(total / size) if total else 0,
        }


search_service = SearchService()
