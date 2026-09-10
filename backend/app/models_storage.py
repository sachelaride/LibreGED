import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models import Base, utc_now

class StorageRule(Base):
    __tablename__ = "ged_storage_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    document_type_id = Column(String, nullable=True) # Optional link to a document type
    
    storage_type = Column(String, default="Local")
    base_path = Column(String, nullable=False)
    
    max_files_per_folder = Column(Integer, default=10000)
    max_gb_per_folder = Column(Float, default=100.0)
    
    enable_duplication = Column(Boolean, default=False)
    secondary_storage_type = Column(String, nullable=True)
    secondary_base_path = Column(String, nullable=True)
    
    network_domain = Column(String, nullable=True)
    network_user = Column(String, nullable=True)
    network_password = Column(String, nullable=True)
    
    current_file_count = Column(Integer, default=0)
    current_size_bytes = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=utc_now)
