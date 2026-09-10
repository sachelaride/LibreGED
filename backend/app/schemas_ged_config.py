from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import datetime

# --- Indices ---
class GedIndexBase(BaseModel):
    name: str
    type: str
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
    name: str
    workflow_id: Optional[str] = None
    is_active: bool = True
    group_id: Optional[str] = None
    retention_years: int = 5
    legal_hold: bool = False
    access_policy: Dict[str, Any] = {}
    signature_rule: Dict[str, Any] = {}

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
    pass

class DocumentTypeResponse(DocumentTypeBase):
    id: str
    created_at: datetime.datetime
    indices: List[DocumentTypeIndexResponse] = []
    active_version: int = 1
    
    class Config:
        from_attributes = True
