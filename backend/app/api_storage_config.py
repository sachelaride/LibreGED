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
    
    from app.main import add_audit
    add_audit(db, "storage_rule", rule.id, "created", f"Storage rule {rule.name} created", user.id)
    
    return rule

@router.put("/api/storage-rules/{rule_id}", response_model=StorageRuleResponse, tags=["Storage Config"])
def update_rule(rule_id: str, payload: StorageRuleCreate, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    rule = db.query(StorageRule).filter(StorageRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Regra de armazenamento não encontrada")
    
    dumped = payload.model_dump(exclude_unset=True)
    _ = dumped.pop("document_type_name", None)
    
    for k, v in dumped.items():
        setattr(rule, k, v)
        
    db.commit()
    db.refresh(rule)
    
    from app.main import add_audit
    add_audit(db, "storage_rule", rule.id, "updated", f"Storage rule {rule.name} updated", user.id)
    
    return rule

@router.post("/api/storage-rules/{rule_id}/duplicate", response_model=StorageRuleResponse, tags=["Storage Config"])
def duplicate_rule(rule_id: str, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    source = db.query(StorageRule).filter(StorageRule.id == rule_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Regra de armazenamento não encontrada")

    duplicate = StorageRule(
        name=f"{source.name} - Cópia",
        document_type_id=source.document_type_id,
        storage_type=source.storage_type,
        base_path=f"{source.base_path}_copia",
        max_files_per_folder=source.max_files_per_folder,
        max_gb_per_folder=source.max_gb_per_folder,
        enable_duplication=source.enable_duplication,
        secondary_storage_type=source.secondary_storage_type,
        secondary_base_path=(
            f"{source.secondary_base_path}_copia"
            if source.secondary_base_path
            else None
        ),
        network_domain=source.network_domain,
        network_user=source.network_user,
        network_password=source.network_password,
        is_active=False,
    )
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)

    from app.main import add_audit
    add_audit(
        db,
        "storage_rule",
        duplicate.id,
        "duplicated",
        f"Storage rule {source.id} duplicated as {duplicate.id}",
        user.id,
    )
    return duplicate

@router.delete("/api/storage-rules/{rule_id}", status_code=204, tags=["Storage Config"])
def delete_rule(rule_id: str, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    rule = db.query(StorageRule).filter(StorageRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Regra de armazenamento não encontrada")
    
    from app.main import add_audit
    add_audit(db, "storage_rule", rule.id, "deleted", f"Storage rule {rule.name} deleted", user.id)
    
    db.delete(rule)
    db.commit()
    return None
