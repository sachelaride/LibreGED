import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text
from app.models import Base, utc_now

class GEDTemplate(Base):
    __tablename__ = "ged_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    html_content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
