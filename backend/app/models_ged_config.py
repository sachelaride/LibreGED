import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
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
    storage_area_id = Column(String, ForeignKey("ged_storage_areas.id"), nullable=False)
    storage_partition_id = Column(String, ForeignKey("ged_storage_partitions.id"), nullable=False)
    workflow_id = Column(String, ForeignKey("ged_workflows.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    
    indices = relationship("DocumentTypeIndex", back_populates="document_type", cascade="all, delete-orphan")
    area = relationship("StorageArea")
    partition = relationship("StoragePartition")

class DocumentTypeIndex(Base):
    __tablename__ = "ged_document_type_indices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_type_id = Column(String, ForeignKey("ged_document_types.id"), nullable=False)
    index_id = Column(String, ForeignKey("ged_indices.id"), nullable=False)
    is_required = Column(Boolean, default=False)
    is_unique = Column(Boolean, default=False)
    
    document_type = relationship("DocumentType", back_populates="indices")
    index = relationship("GedIndex")


