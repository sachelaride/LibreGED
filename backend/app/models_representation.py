import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models import Base, utc_now


class RepresentationService(Base):
    __tablename__ = "representation_services"
    __table_args__ = (UniqueConstraint("code", name="uq_representation_service_code"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    document_type = Column(String, nullable=False, index=True)
    workflow_id = Column(String, ForeignKey("ged_workflows.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    workflow = relationship("Workflow")
    versions = relationship(
        "RepresentationServiceVersion",
        back_populates="service",
        cascade="all, delete-orphan",
        order_by="RepresentationServiceVersion.revision.desc()",
    )
    executions = relationship("RepresentationExecution", back_populates="service")


class RepresentationServiceVersion(Base):
    __tablename__ = "representation_service_versions"
    __table_args__ = (
        UniqueConstraint("service_id", "revision", name="uq_representation_service_revision"),
        UniqueConstraint("service_id", "version_label", name="uq_representation_service_version_label"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    service_id = Column(String, ForeignKey("representation_services.id", ondelete="CASCADE"), nullable=False, index=True)
    revision = Column(Integer, nullable=False)
    version_label = Column(String, nullable=False)
    status = Column(String, nullable=False, default="DRAFT")  # DRAFT, PUBLISHED, ARCHIVED
    xslt_content = Column(Text, nullable=False)
    content_hash = Column(String, nullable=False, index=True)
    created_by_user_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    published_at = Column(DateTime, nullable=True)

    service = relationship("RepresentationService", back_populates="versions")
    created_by = relationship("User")
    executions = relationship("RepresentationExecution", back_populates="service_version")


class RepresentationExecution(Base):
    __tablename__ = "representation_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    service_id = Column(String, ForeignKey("representation_services.id", ondelete="RESTRICT"), nullable=False, index=True)
    service_version_id = Column(String, ForeignKey("representation_service_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("ged_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    input_xml_hash = Column(String, nullable=False)
    output_hash = Column(String, nullable=True)
    status = Column(String, nullable=False, default="PENDING", index=True)  # PENDING, SUCCEEDED, FAILED
    error_message = Column(Text, nullable=True)
    requested_by_user_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    service = relationship("RepresentationService", back_populates="executions")
    service_version = relationship("RepresentationServiceVersion", back_populates="executions")
    document = relationship("GEDDocument")
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
