from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
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
    documents = relationship("Document", back_populates="institution", cascade="all, delete-orphan")
    users = relationship("User", back_populates="institution", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin_global, gestor_clinica, recepcao, academico, orientador
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    institution = relationship("Institution", back_populates="users")


class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    full_name = Column(String, nullable=False, index=True)
    birth_date = Column(String, nullable=False)  # Stored as ISO string
    cpf = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    institution = relationship("Institution", back_populates="students")
    guardians = relationship("Guardian", back_populates="student", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="student", cascade="all, delete-orphan")


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
    created_at = Column(DateTime, default=utc_now)

    institution = relationship("Institution", back_populates="enrollments")
    student = relationship("Student", back_populates="enrollments")
    documents = relationship("Document", back_populates="enrollment", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    enrollment_id = Column(String, ForeignKey("enrollments.id"), nullable=False, index=True)
    document_type = Column(String, nullable=False, index=True)  # historico, contrato, diploma, etc
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)  # draft, pending, validated, signed, archived, rejected
    created_at = Column(DateTime, default=utc_now, index=True)

    institution = relationship("Institution", back_populates="documents")
    student = relationship("Student", back_populates="documents")
    enrollment = relationship("Enrollment", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="document", cascade="all, delete-orphan")


class SchemaVersion(Base):
    __tablename__ = "schema_versions"

    id = Column(String, primary_key=True, index=True)
    code = Column(String, nullable=False, unique=True, index=True)
    document_type = Column(String, nullable=False, index=True)
    namespace = Column(String, nullable=False)
    xsd_hash = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)  # proposed, approved, retired
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    environment = Column(String, nullable=False, index=True)  # homologation, production
    created_at = Column(DateTime, default=utc_now, index=True)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_version",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=utc_now, index=True)
    checksum = Column(String, nullable=False)

    document = relationship("Document", back_populates="versions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True, index=True)
    entity = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    details = Column(String)
    created_at = Column(DateTime, default=utc_now, index=True)
    hash_signature = Column(String, nullable=True)

    document = relationship("Document", back_populates="audit_events")
