import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict

class SearchService:
    """Motor de Busca NATIVO usando SQLite FTS5 (Sem dependência de Elasticsearch/Docker)."""

    def index_document(self, db: Session, document_id: str, title: str, content: str, indices_data: str):
        """Indexa o documento na tabela virtual FTS5."""
        # Primeiro verificar se já existe para fazer update ou insert
        query_check = text("SELECT document_id FROM ged_documents_fts WHERE document_id = :doc_id")
        result = db.execute(query_check, {"doc_id": document_id}).fetchone()
        
        if result:
            query = text("""
                UPDATE ged_documents_fts 
                SET title = :title, content = :content, indices_data = :indices_data
                WHERE document_id = :doc_id
            """)
        else:
            query = text("""
                INSERT INTO ged_documents_fts (document_id, title, content, indices_data)
                VALUES (:doc_id, :title, :content, :indices_data)
            """)
            
        db.execute(query, {
            "doc_id": document_id,
            "title": title,
            "content": content,
            "indices_data": indices_data
        })
        db.commit()
        return True

    def search(self, db: Session, query_string: str, user=None, allowed_document_type_ids: List[str] = None, page: int = 1, size: int = 50) -> Dict:
        """Busca em milissegundos cruzando Título, Metadados (Índices) e Conteúdo Extraído (OCR)."""
        safe_query = f"{query_string}*" if query_string else ""
        
        if not safe_query:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}
            
        # Condições RBAC
        rbac_joins = ""
        rbac_where = ""
        params = {"q": safe_query}
        
        if user and user.role != "admin_global":
            rbac_joins = "JOIN documents doc ON doc.id = ged_documents_fts.document_id"
            
            # Filtro por Campus e Instituição
            if user.campus_id:
                rbac_where += " AND doc.campus_id = :campus_id"
                params["campus_id"] = user.campus_id
            elif user.institution_id:
                # Gestor global da instituição
                rbac_where += " AND doc.institution_id = :inst_id"
                params["inst_id"] = user.institution_id
                
            # Filtro por Document Types permitidos
            if allowed_document_type_ids is not None:
                if not allowed_document_type_ids:
                    # Se a lista estiver vazia e não for admin global, não acha nada (fail-closed)
                    return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}
                
                placeholders = ", ".join([f":dt_{i}" for i in range(len(allowed_document_type_ids))])
                rbac_where += f" AND doc.document_type IN ({placeholders})"
                for i, dt_id in enumerate(allowed_document_type_ids):
                    params[f"dt_{i}"] = dt_id
            
        # Obter o total
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM ged_documents_fts 
            {rbac_joins}
            WHERE ged_documents_fts MATCH :q {rbac_where}
        """)
        total = db.execute(count_query, params).scalar() or 0
        
        # Paginação
        offset = (page - 1) * size
        params["limit"] = size
        params["offset"] = offset
        
        query = text(f"""
            SELECT ged_documents_fts.document_id, ged_documents_fts.title, snippet(ged_documents_fts, 2, '<b>', '</b>', '...', 15) as snippet
            FROM ged_documents_fts 
            {rbac_joins}
            WHERE ged_documents_fts MATCH :q {rbac_where}
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)
        
        results = db.execute(query, params).fetchall()
        
        hits = []
        for r in results:
            hits.append({
                "document_id": r.document_id,
                "title": r.title,
                "snippet": r.snippet
            })
            
        import math
        pages = math.ceil(total / size) if size > 0 else 0
            
        return {
            "items": hits,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }

search_service = SearchService()
