from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ConnectorStatus(str, Enum):
    RECEIVED = "RECEIVED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class CourseERPDto(BaseModel):
    codigo_mec: str
    nome: str
    carga_horaria: int
    modalidade: str


class StudentERPDto(BaseModel):
    nome: str
    cpf: str
    matricula: str
    curso: CourseERPDto


class IngestionPayload(BaseModel):
    """
    O Payload que o ERP vai postar.
    Deve conter todos os dados do aluno necessários para a geração do Diploma.
    """

    aluno: StudentERPDto
    data_conclusao: str
    institution_id: str
    callback_url: Optional[str] = None


class IngestionResponse(BaseModel):
    message: str
    document_id: str
    status: str
    idempotency_key: str
    audit_id: str


class ConnectorStatusContract(BaseModel):
    """Formal contract for the external connector to report ERP ingestion status."""

    status: ConnectorStatus
    message: str
    idempotency_key: Optional[str] = None
    document_id: Optional[str] = None
    correlation_id: Optional[str] = None
    source_system: Optional[str] = None
    last_updated_at: Optional[str] = None


class ConnectorStatusUpdate(BaseModel):
    """Contract used by the external ERP connector to push lifecycle updates."""

    status: ConnectorStatus
    message: str
    idempotency_key: Optional[str] = None
    document_id: Optional[str] = None
    correlation_id: Optional[str] = None
    source_system: Optional[str] = None
    last_updated_at: Optional[str] = None
