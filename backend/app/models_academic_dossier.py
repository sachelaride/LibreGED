import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from app.models import Base, utc_now

class AcademicDossier(Base):
    __tablename__ = "academic_dossiers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    enrollment_id = Column(String, ForeignKey("enrollments.id"), nullable=False, index=True)
    dossier_type = Column(String, nullable=False, default="diploma") # diploma, transfer, etc.
    group_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="open") # open, in_validation, approved, signed, canceled
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    student = relationship("Student")
    enrollment = relationship("Enrollment")
    documents = relationship("DossierDocument", back_populates="dossier", cascade="all, delete-orphan")
    validations = relationship("AcademicValidation", back_populates="dossier", cascade="all, delete-orphan")


class DossierDocument(Base):
    __tablename__ = "dossier_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id = Column(String, ForeignKey("academic_dossiers.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("ged_documents.id"), nullable=False)
    document_type_code = Column(String, nullable=False) # e.g. RG, CPF, HISTORICO

    # Frozen snapshot data
    file_hash = Column(String, nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    added_at = Column(DateTime, default=utc_now)

    dossier = relationship("AcademicDossier", back_populates="documents")
    document = relationship("GEDDocument")


class AcademicValidation(Base):
    __tablename__ = "academic_validations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dossier_id = Column(String, ForeignKey("academic_dossiers.id"), nullable=False, index=True)
    rule_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending") # pending, passed, failed
    message = Column(String, nullable=True)
    evaluated_at = Column(DateTime, default=utc_now)

    dossier = relationship("AcademicDossier", back_populates="validations")
