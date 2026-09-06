from pydantic import BaseModel
from typing import Optional
import datetime

class UserBase(BaseModel):
    username: str
    role: str
    institution_id: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True
