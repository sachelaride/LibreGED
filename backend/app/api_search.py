from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.search import SearchService

from typing import Any, Dict
from app.schemas_pagination import PaginatedResponse

from app.auth import get_current_active_user
from app.models import User
from app.models_ged_config import UserDocumentType

router = APIRouter()
search_service = SearchService()

@router.get("/api/documents/search", tags=["GED - Busca Full-Text"], response_model=PaginatedResponse[Dict[str, Any]])
def search_documents(
    q: str, 
    page: int = 1, 
    size: int = 50, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Busca rápida em PostgreSQL cruzando título e metadados extraídos.
    Restrita por campus e tipos documentais permitidos para o usuário atual.
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
        size=size
    )
