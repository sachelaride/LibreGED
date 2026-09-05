from pydantic import BaseModel
from typing import Optional, List
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
    storage_area_id: str
    storage_partition_id: str
    is_active: bool = True

class DocumentTypeCreate(DocumentTypeBase):
    pass

class DocumentTypeResponse(DocumentTypeBase):
    id: str
    created_at: datetime.datetime
    indices: List[DocumentTypeIndexResponse] = []
    
    class Config:
        from_attributes = True
