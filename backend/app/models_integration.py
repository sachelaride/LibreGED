import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from app.models import Base, utc_now

class IntegrationConfig(Base):
    __tablename__ = "integration_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    integration_type = Column(String, nullable=False) # e.g. "WEBHOOK", "API"
    base_url = Column(String, nullable=True)
    encrypted_secret = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
