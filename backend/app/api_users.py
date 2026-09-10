from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app import models
from app import auth
from app.schemas_users import UserCreate, UserResponse
from app.schemas_pagination import PaginatedResponse
import math

router = APIRouter()

@router.get("/users", response_model=PaginatedResponse[UserResponse], tags=["Admin - Users"])
def get_users(
    page: int = 1, 
    size: int = 50, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.role_checker(["admin_global", "admin_instituicao"]))
):
    query = db.query(models.User)
    
    if current_user.role != "admin_global":
        query = query.filter(models.User.institution_id == current_user.institution_id)
        
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/users", response_model=UserResponse, tags=["Admin - Users"])
def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.role_checker(["admin_global", "admin_instituicao"]))
):
    existing = db.query(models.User).filter_by(username=user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuário já existe")
    
    institution_id = current_user.institution_id
    if current_user.role == "admin_global":
        institution_id = user.institution_id

    if current_user.role != "admin_global" and user.role == "admin_global":
        raise HTTPException(status_code=403, detail="Apenas admin global pode criar outro admin global")
    
    new_user = models.User(
        id=str(uuid.uuid4()),
        username=user.username,
        role=user.role,
        institution_id=institution_id,
        hashed_password=auth.get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
