from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
import datetime

# --- Indices ---
class GedIndexBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    options: List[str] = Field(default_factory=list)
    mask: Optional[str] = Field(default=None, max_length=200)
    auto_increment: bool = False
    is_active: bool = True

class GedIndexCreate(GedIndexBase):
    pass

class GedIndexResponse(GedIndexBase):
    id: str
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True

# --- Document Type Indices ---
class DocumentTypeIndexBase(BaseModel):
    index_id: str
    is_required: bool = False
    is_unique: bool = False

class DocumentTypeIndexCreate(DocumentTypeIndexBase):
    pass

class DocumentTypeIndexResponse(DocumentTypeIndexBase):
    id: str
    index: GedIndexResponse
    
    class Config:
        from_attributes = True

# --- Document Types ---
class DocumentTypeBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    workflow_id: Optional[str] = None
    is_active: bool = True
    group_id: Optional[str] = None
    retention_years: int = Field(default=5, ge=0, le=1000)
    legal_hold: bool = False
    access_policy: Dict[str, Any] = Field(default_factory=dict)
    signature_rule: Dict[str, Any] = Field(default_factory=dict)

class DocumentTypeVersionCreate(DocumentTypeBase):
    effective_from: Optional[datetime.datetime] = None

class DocumentTypeVersionResponse(DocumentTypeVersionCreate):
    id: str
    document_type_id: str
    version: int
    status: str
    effective_until: Optional[datetime.datetime] = None
    created_by: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class DocumentTypeCreate(DocumentTypeBase):
    storage_area_id: Optional[str] = None
    storage_partition_id: Optional[str] = None

class DocumentTypeResponse(DocumentTypeBase):
    storage_area_id: Optional[str] = None
    storage_partition_id: Optional[str] = None
    id: str
    created_at: datetime.datetime
    indices: List[DocumentTypeIndexResponse] = Field(default_factory=list)
    active_version: int = 1
    
    class Config:
        from_attributes = True
