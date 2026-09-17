from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


REPRESENTATION_DOCUMENT_TYPES = {"diploma", "historico_final", "historico_parcial", "curriculo"}


class RepresentationServiceCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    document_type: str
    workflow_id: Optional[str] = None
    is_active: bool = True


class RepresentationServiceResponse(RepresentationServiceCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RepresentationVersionCreate(BaseModel):
    version_label: str = Field(min_length=1, max_length=40)
    xslt_content: str = Field(min_length=1)


class RepresentationVersionResponse(BaseModel):
    id: str
    service_id: str
    revision: int
    version_label: str
    status: str
    content_hash: str
    created_by_user_id: Optional[str] = None
    created_at: datetime
    published_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class RepresentationExecutionRequest(BaseModel):
    service_id: str
    version_id: Optional[str] = None
    xml_content: str = Field(min_length=1)
    document_id: Optional[str] = None


class RepresentationExecutionResponse(BaseModel):
    id: str
    service_id: str
    service_version_id: str
    document_id: Optional[str]
    input_xml_hash: str
    output_hash: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    html_content: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
