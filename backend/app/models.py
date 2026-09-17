from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    """Return naive UTC for compatibility with existing database columns."""
    return datetime.now(UTC).replace(tzinfo=None)


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    cnpj = Column(String, nullable=False, unique=True, index=True)
    legal_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    students = relationship("Student", back_populates="institution", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="institution", cascade="all, delete-orphan")
    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    campuses = relationship("Campus", back_populates="institution", cascade="all, delete-orphan")
    settings = relationship("InstitutionSettings", back_populates="institution", uselist=False, cascade="all, delete-orphan")


class InstitutionSettings(Base):
    __tablename__ = "institution_settings"

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, unique=True, index=True)
    max_upload_size_mb = Column(Integer, default=10)
    allowed_mime_types = Column(String, default="application/pdf,image/jpeg,image/png")
    antimalware_enabled = Column(Boolean, default=True)
    quarantine_enabled = Column(Boolean, default=True)
    quarantine_policy = Column(String, default="manual")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution", back_populates="settings")


class Campus(Base):
    __tablename__ = "campuses"

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    institution = relationship("Institution", back_populates="campuses")
    users = relationship("User", back_populates="campus")
    students = relationship("Student", back_populates="campus")
    enrollments = relationship("Enrollment", back_populates="campus")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin_global, admin_instituicao, operador, leitor, auditor
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=True, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    institution = relationship("Institution", back_populates="users")
    campus = relationship("Campus", back_populates="users")


class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    full_name = Column(String, nullable=False, index=True)
    birth_date = Column(String, nullable=False)  # Stored as ISO string
    cpf = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    institution = relationship("Institution", back_populates="students")
    campus = relationship("Campus", back_populates="students")
    guardians = relationship("Guardian", back_populates="student", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")


class Guardian(Base):
    __tablename__ = "guardians"

    id = Column(String, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    full_name = Column(String, nullable=False, index=True)
    cpf = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, index=True)
    relationship_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    student = relationship("Student", back_populates="guardians")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    course_name = Column(String, nullable=False, index=True)
    class_name = Column(String, nullable=False)
    year = Column(Integer, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)  # active, inactive, transferred, graduated
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    institution = relationship("Institution", back_populates="enrollments")
    campus = relationship("Campus", back_populates="enrollments")
    student = relationship("Student", back_populates="enrollments")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String, primary_key=True, index=True)
    ingestion_id = Column(String, nullable=True, unique=True, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    document_id = Column(String, ForeignKey("ged_documents.id"), nullable=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)  # PENDING, PROCESSING, QUARANTINE, COMPLETED, FAILED, INDEX_PENDING
    file_path = Column(String, nullable=False)
    manifest_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    retries = Column(Integer, default=0, nullable=False)
    next_attempt_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime, nullable=True)

    institution = relationship("Institution")

# Import ECM models so they are registered with Base metadata
from app import models_ecm

# Import Academic Dossier models
from app import models_academic_dossier

# Import Integration models
from app import models_integration

# Import Config models
class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, nullable=True, index=True)
    entity = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    hash_signature = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now, index=True)

from app import models_config

# Import visual representation models so they are registered with Base metadata.
from app import models_representation
