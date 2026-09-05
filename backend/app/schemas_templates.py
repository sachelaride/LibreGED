from pydantic import BaseModel
import datetime

class GEDTemplateBase(BaseModel):
    name: str
    html_content: str
    is_active: bool = True

class GEDTemplateCreate(GEDTemplateBase):
    pass

class GEDTemplateUpdate(BaseModel):
    name: str | None = None
    html_content: str | None = None
    is_active: bool | None = None

class GEDTemplateResponse(GEDTemplateBase):
    id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    class Config:
        from_attributes = True
