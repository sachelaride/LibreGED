from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.search import SearchService

from typing import Any, Dict
from app.schemas_pagination import PaginatedResponse

router = APIRouter()
search_service = SearchService()

@router.get("/api/documents/search", tags=["GED - Busca Full-Text"], response_model=PaginatedResponse[Dict[str, Any]])
def search_documents(q: str, page: int = 1, size: int = 50, db: Session = Depends(get_db)):
    """
    Busca rápida (FTS5) em milhões de documentos cruzando Título, Metadados e OCR.
    """
    return search_service.search(db=db, query_string=q, page=page, size=size)
