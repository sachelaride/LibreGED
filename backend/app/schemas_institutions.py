from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InstitutionBase(BaseModel):
    name: str = Field(..., description="Nome fantasia da instituição")
    cnpj: str = Field(..., description="CNPJ da instituição")
    legal_name: str = Field(..., description="Razão social")

class InstitutionCreate(InstitutionBase):
    pass

class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None

class InstitutionResponse(InstitutionBase):
    id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
