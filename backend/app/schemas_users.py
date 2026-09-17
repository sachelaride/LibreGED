from pydantic import BaseModel
from typing import Optional
import datetime

class UserBase(BaseModel):
    username: str
    role: str
    institution_id: Optional[str] = None
    campus_id: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    campus_id: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    password: str

class PermissionGroupCreate(BaseModel):
    name: str
    institution_id: str
    parent_group_id: Optional[str] = None

class PermissionGroupUpdate(BaseModel):
    name: Optional[str] = None
    parent_group_id: Optional[str] = None

class PermissionGroupPermission(BaseModel):
    document_type_id: str
    permissions: list[str] = []
    denied_permissions: list[str] = []

class UserResponse(UserBase):
    id: str
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True
