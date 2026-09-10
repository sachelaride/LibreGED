import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models import Base, utc_now

class GedIndex(Base):
    __tablename__ = "ged_indices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    type = Column(String, nullable=False) # e.g., Caractere, Data, Lista, Booleano
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

class DocumentType(Base):
    __tablename__ = "ged_document_types"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    workflow_id = Column(String, ForeignKey("ged_workflows.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    group_id = Column(String, nullable=True)
    retention_years = Column(Integer, default=5)
    legal_hold = Column(Boolean, default=False)
    access_policy = Column(JSONB, default=dict, nullable=False)
    signature_rule = Column(JSONB, default=dict, nullable=False)
    active_version = Column(Integer, default=1, nullable=False)
    storage_area_id = Column(String, nullable=True)
    storage_partition_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    
    indices = relationship("DocumentTypeIndex", back_populates="document_type", cascade="all, delete-orphan")
    versions = relationship("DocumentTypeVersion", back_populates="document_type", cascade="all, delete-orphan")


class DocumentTypeVersion(Base):
    __tablename__ = "ged_document_type_versions"
    __table_args__ = (UniqueConstraint("document_type_id", "version", name="uq_document_type_version"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_type_id = Column(String, ForeignKey("ged_document_types.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="DRAFT")
    name = Column(String, nullable=False)
    workflow_id = Column(String, nullable=True)
    group_id = Column(String, nullable=True)
    retention_years = Column(Integer, nullable=False, default=5)
    legal_hold = Column(Boolean, nullable=False, default=False)
    access_policy = Column(JSONB, nullable=False, default=dict)
    signature_rule = Column(JSONB, nullable=False, default=dict)
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    created_by = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    document_type = relationship("DocumentType", back_populates="versions")

class DocumentTypeIndex(Base):
    __tablename__ = "ged_document_type_indices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_type_id = Column(String, ForeignKey("ged_document_types.id"), nullable=False)
    index_id = Column(String, ForeignKey("ged_indices.id"), nullable=False)
    is_required = Column(Boolean, default=False)
    is_unique = Column(Boolean, default=False)
    
    document_type = relationship("DocumentType", back_populates="indices")
    index = relationship("GedIndex")


class UserDocumentType(Base):
    __tablename__ = "ged_user_document_types"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    document_type_id = Column(String, ForeignKey("ged_document_types.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    
    # We can add relationships here if needed, but normally we just query this table
    # or add a relationship on User (via models.py string ref) or DocumentType.
