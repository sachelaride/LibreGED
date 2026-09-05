from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app import models
from app import auth
from app.schemas_users import UserCreate, UserResponse

router = APIRouter()

@router.get("/users", response_model=List[UserResponse], tags=["Admin - Users"])
def get_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    users = db.query(models.User).all()
    return users

@router.post("/users", response_model=UserResponse, tags=["Admin - Users"])
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    existing = db.query(models.User).filter_by(username=user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuário já existe")
    
    new_user = models.User(
        id=str(uuid.uuid4()),
        username=user.username,
        role=user.role,
        hashed_password=auth.get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
