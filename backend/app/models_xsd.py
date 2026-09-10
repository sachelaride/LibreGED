import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models import Base, utc_now

class SchemaVersion(Base):
    __tablename__ = "ged_schema_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_type_id = Column(String, ForeignKey("ged_document_types.id"), nullable=False)
    code = Column(String, nullable=False) # e.g. v1.0
    namespace = Column(String, nullable=False)
    xsd_hash = Column(String, nullable=False)
    status = Column(String, default="proposed") # proposed, approved, retired
    valid_from = Column(DateTime, nullable=False, default=utc_now)
    valid_until = Column(DateTime, nullable=True)
    environment = Column(String, default="homologation")
    created_at = Column(DateTime, default=utc_now)
    
    document_type = relationship("DocumentType")
