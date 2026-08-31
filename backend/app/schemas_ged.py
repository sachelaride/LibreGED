from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models_ged import GEDDocumentStatus, GEDAcademicPhase

class DocumentCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class DocumentCategoryCreate(DocumentCategoryBase):
    pass

class DocumentCategoryResponse(DocumentCategoryBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class GEDDocumentBase(BaseModel):
    title: str
    category_id: str
    student_id: Optional[str] = None
    academic_phase: Optional[GEDAcademicPhase] = None

class GEDDocumentCreate(GEDDocumentBase):
    pass # file_path will be handled by upload endpoint

class GEDDocumentResponse(GEDDocumentBase):
    id: str
    file_path: str
    status: GEDDocumentStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentStatusUpdate(BaseModel):
    status: GEDDocumentStatus
    comments: Optional[str] = None


class DocumentTransitionResponse(BaseModel):
    id: str
    document_id: str
    from_status: Optional[GEDDocumentStatus]
    to_status: GEDDocumentStatus
    changed_by_user_id: Optional[str]
    comments: Optional[str]
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
