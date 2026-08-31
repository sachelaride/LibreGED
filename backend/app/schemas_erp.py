from pydantic import BaseModel
from typing import Optional

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
