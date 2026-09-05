import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models import Base, utc_now

class StorageArea(Base):
    __tablename__ = "ged_storage_areas"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    
    partitions = relationship("StoragePartition", back_populates="area", cascade="all, delete-orphan")

class StoragePartition(Base):
    __tablename__ = "ged_storage_partitions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    area_id = Column(String, ForeignKey("ged_storage_areas.id"), nullable=False)
    name = Column(String, nullable=False)
    
    max_files = Column(Integer, nullable=False)
    max_size_gb = Column(Float, nullable=False)
    base_path = Column(String, nullable=False)
    
    network_domain = Column(String, nullable=True)
    network_user = Column(String, nullable=True)
    network_password = Column(String, nullable=True)
    
    current_file_count = Column(Integer, default=0)
    current_size_bytes = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    
    area = relationship("StorageArea", back_populates="partitions")
