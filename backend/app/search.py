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

    def search(self, db: Session, query_string: str, page: int = 1, size: int = 50) -> Dict:
        """Busca em milissegundos cruzando Título, Metadados (Índices) e Conteúdo Extraído (OCR)."""
        safe_query = f"{query_string}*" if query_string else ""
        
        if not safe_query:
            return {"items": [], "total": 0, "page": page, "size": size, "pages": 0}
            
        # Obter o total
        count_query = text("""
            SELECT COUNT(*) 
            FROM ged_documents_fts 
            WHERE ged_documents_fts MATCH :q
        """)
        total = db.execute(count_query, {"q": safe_query}).scalar() or 0
        
        # Paginação
        offset = (page - 1) * size
        
        query = text("""
            SELECT document_id, title, snippet(ged_documents_fts, 2, '<b>', '</b>', '...', 15) as snippet
            FROM ged_documents_fts 
            WHERE ged_documents_fts MATCH :q
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)
        
        results = db.execute(query, {"q": safe_query, "limit": size, "offset": offset}).fetchall()
        
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
