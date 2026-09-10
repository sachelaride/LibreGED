from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime

class DossierDocumentBase(BaseModel):
    document_id: str
    document_type_code: str
    file_hash: str
    version_number: int

class DossierDocumentCreate(DossierDocumentBase):
    pass

class DossierDocumentResponse(DossierDocumentBase):
    id: str
    added_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AcademicValidationResponse(BaseModel):
    id: str
    rule_name: str
    status: str
    message: Optional[str] = None
    evaluated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AcademicDossierBase(BaseModel):
    student_id: str
    enrollment_id: str
    dossier_type: str
    status: str = "open"

class AcademicDossierCreate(BaseModel):
    student_id: str
    enrollment_id: str
    dossier_type: str

class AcademicDossierResponse(AcademicDossierBase):
    id: str
    created_at: datetime
    updated_at: datetime
    documents: List[DossierDocumentResponse] = []
    validations: List[AcademicValidationResponse] = []
    model_config = ConfigDict(from_attributes=True)
