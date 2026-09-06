from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_active_user, role_checker
from app.models import User
from app.models_storage import StorageArea, StoragePartition
from app.schemas_storage import (
    StorageAreaCreate, StorageAreaResponse, 
    StoragePartitionCreate, StoragePartitionResponse
)
from app.schemas_pagination import PaginatedResponse
import math

router = APIRouter()

@router.get("/api/storage/areas", response_model=PaginatedResponse[StorageAreaResponse], tags=["Storage Config"])
def list_areas(page: int = 1, size: int = 50, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    query = db.query(StorageArea)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/api/storage/areas", response_model=StorageAreaResponse, tags=["Storage Config"])
def create_area(payload: StorageAreaCreate, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    area = StorageArea(**payload.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area

@router.get("/api/storage/partitions", response_model=PaginatedResponse[StoragePartitionResponse], tags=["Storage Config"])
def list_partitions(area_id: str = None, page: int = 1, size: int = 50, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    query = db.query(StoragePartition)
    if area_id:
        query = query.filter(StoragePartition.area_id == area_id)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/api/storage/partitions", response_model=StoragePartitionResponse, tags=["Storage Config"])
def create_partition(payload: StoragePartitionCreate, db: Session = Depends(get_db), user: User = Depends(role_checker(["admin_global"]))):
    # Verify area exists
    area = db.query(StorageArea).filter(StorageArea.id == payload.area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Storage Area not found")
        
    partition = StoragePartition(**payload.model_dump())
    db.add(partition)
    db.commit()
    db.refresh(partition)
    return partition
