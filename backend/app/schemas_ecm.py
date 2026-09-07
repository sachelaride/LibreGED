from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class NodeAspectBase(BaseModel):
    aspect_name: str

class NodeBase(BaseModel):
    node_type: str
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    parent_id: Optional[str] = None

class NodeCreate(NodeBase):
    pass

class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: str
    class Config:
        from_attributes = True

class NodeTagBase(BaseModel):
    tag: TagResponse
    class Config:
        from_attributes = True

class PropertiesUpdate(BaseModel):
    properties: Dict[str, Any]

class NodeResponse(NodeBase):
    id: str
    major_version: int
    minor_version: int
    institution_id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    aspects: List[NodeAspectBase] = []
    # Using Any or dict for tags just to reflect the shape for now
    tags: List[Any] = []

    class Config:
        from_attributes = True

class AspectAdd(BaseModel):
    aspect_name: str

class SiteBase(BaseModel):
    name: str
    title: str
    description: Optional[str] = None
    visibility: str = "PUBLIC"

class SiteCreate(SiteBase):
    pass

class SiteResponse(SiteBase):
    id: str
    institution_id: str
    created_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class SiteMemberCreate(BaseModel):
    user_id: str
    role: str

class SiteMemberResponse(SiteMemberCreate):
    site_id: str
    
    class Config:
        from_attributes = True

class DashboardConfigBase(BaseModel):
    layout_json: Dict[str, Any]

class DashboardConfigUpdate(DashboardConfigBase):
    pass

class DashboardConfigResponse(DashboardConfigBase):
    id: str
    owner_type: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
