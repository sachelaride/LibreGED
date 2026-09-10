from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class IntegrationConfigBase(BaseModel):
    name: str
    integration_type: str
    base_url: Optional[str] = None
    is_active: bool = True

class IntegrationConfigCreate(IntegrationConfigBase):
    secret: Optional[str] = None

class IntegrationConfigUpdate(IntegrationConfigBase):
    secret: Optional[str] = None

class IntegrationConfigResponse(IntegrationConfigBase):
    id: str
    institution_id: str
    has_secret: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
