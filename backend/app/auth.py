from datetime import datetime, timedelta, UTC
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app import models
from pydantic import BaseModel

import bcrypt
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

class TokenData(BaseModel):
    username: str | None = None
    role: str | None = None
    institution_id: str | None = None
    campus_id: str | None = None

# We are using bcrypt directly because passlib has a known bug with bcrypt >= 4.0.0
def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(
            username=username,
            role=payload.get("role"),
            institution_id=payload.get("institution_id"),
            campus_id=payload.get("campus_id")
        )
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    # If we had a disabled user flag, we would check it here
    return current_user

def role_checker(allowed_roles: list[str]):
    def check_roles(user: models.User = Depends(get_current_active_user)):
        if user.role == "admin_global":
            return user
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return user
    return check_roles

def check_institution_access(user: models.User, target_institution_id: str):
    if user.role == "admin_global":
        return
    if user.institution_id != target_institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution access forbidden")

def check_campus_access(user: models.User, target_campus_id: str):
    if user.role == "admin_global":
        return
    # If the user has no specific campus_id, they have institution-level access
    if user.campus_id is None:
        return
    if user.campus_id != target_campus_id:
        raise HTTPException(status_code=403, detail="Cross-campus access forbidden")

def verify_document_ownership(user: models.User, db_doc):
    """
    Verifies if the current user has access to the given document.
    Works for both GEDDocument and Document models.
    """
    if user.role == "admin_global":
        return
        
    if getattr(db_doc, "institution_id", None) and db_doc.institution_id != user.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution access forbidden")
        
    # Validar restrição de campus se o usuário for limitado a um campus
    if user.campus_id is None:
        return
        
    doc_campus_id = getattr(db_doc, "campus_id", None)
    if doc_campus_id and doc_campus_id != user.campus_id:
        raise HTTPException(status_code=403, detail="Cross-campus access forbidden")

def check_document_type_access(db: Session, user: models.User, document_type_id: str):
    if user.role == "admin_global":
        return
    
    from app.models_ged_config import UserDocumentType
    
    access = db.query(UserDocumentType).filter(
        UserDocumentType.user_id == user.id,
        UserDocumentType.document_type_id == document_type_id
    ).first()
    
    if not access:
        raise HTTPException(status_code=403, detail="Document type access forbidden")
