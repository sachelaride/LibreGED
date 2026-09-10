from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_active_user, role_checker
from app.models import User
from app.models_storage import StorageRule
from app.schemas_storage import StorageRuleCreate, StorageRuleResponse
from app.schemas_pagination import PaginatedResponse
import math

router = APIRouter()

@router.get("/api/storage-rules", response_model=PaginatedResponse[StorageRuleResponse], tags=["Storage Config"])
def list_rules(page: int = 1, size: int = 50, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    query = db.query(StorageRule)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

from app.models_ged_config import DocumentType

@router.post("/api/storage-rules", response_model=StorageRuleResponse, tags=["Storage Config"])
def create_rule(payload: StorageRuleCreate, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    dumped = payload.model_dump()
    dt_name = dumped.pop("document_type_name", None)
    
    if dt_name and not dumped.get("document_type_id"):
        # Auto create document type
        existing_dt = db.query(DocumentType).filter(DocumentType.name == dt_name).first()
        if not existing_dt:
            new_dt = DocumentType(name=dt_name)
            db.add(new_dt)
            db.commit()
            db.refresh(new_dt)
            dumped["document_type_id"] = new_dt.id
        else:
            dumped["document_type_id"] = existing_dt.id

    rule = StorageRule(**dumped)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
