import enum
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.models import Base, utc_now

class GEDDocumentStatus(str, enum.Enum):
    RASCUNHO = "RASCUNHO"
    PENDENTE_VALIDACAO = "PENDENTE_VALIDACAO"
    REJEITADO = "REJEITADO"
    VALIDO = "VALIDO"
    ASSINADO = "ASSINADO"
    ARQUIVADO = "ARQUIVADO"

class GEDAcademicPhase(str, enum.Enum):
    MATRICULA = "MATRICULA"
    CURSO = "CURSO"
    FORMATURA = "FORMATURA"
    DIPLOMACAO = "DIPLOMACAO"

class DocumentCategory(Base):
    __tablename__ = "ged_document_categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    index_code = Column(String, nullable=True, unique=True, index=True) # e.g., "0001", "0002"
    name = Column(String, nullable=False, index=True) # e.g., "Documentos Pessoais"
    description = Column(String, nullable=True)
    is_active = Column(Integer, default=1)
    
    documents = relationship("GEDDocument", back_populates="category")


class GEDDocument(Base):
    __tablename__ = "ged_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False) # e.g., "RG - Joao", "Comprovante Residencia"
    file_path = Column(String, nullable=False)
    
    status = Column(Enum(GEDDocumentStatus), default=GEDDocumentStatus.RASCUNHO, nullable=False)
    academic_phase = Column(Enum(GEDAcademicPhase), nullable=True) # Which phase does this belong to
    
    extracted_metadata = Column(Text, nullable=True) # Stores the JSON blob from OCR/AI
    
    # Relationships
    category_id = Column(String, ForeignKey("ged_document_categories.id"), nullable=False)
    student_id = Column(String, index=True, nullable=True) # Could be CPF or a foreign key to a Student table in the future
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    category = relationship("DocumentCategory", back_populates="documents")
    transitions = relationship("DocumentTransitionHistory", back_populates="document", cascade="all, delete-orphan")


class DocumentTransitionHistory(Base):
    __tablename__ = "ged_document_transitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("ged_documents.id"), nullable=False)
    
    from_status = Column(Enum(GEDDocumentStatus), nullable=True)
    to_status = Column(Enum(GEDDocumentStatus), nullable=False)
    
    changed_by_user_id = Column(String, nullable=True) # User ID who made the change
    comments = Column(Text, nullable=True) # E.g. reason for REJEITADO
    
    timestamp = Column(DateTime, default=utc_now)
    
    document = relationship("GEDDocument", back_populates="transitions")
