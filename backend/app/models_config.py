from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import uuid

from app.models import Base, utc_now

class ConfigProposal(Base):
    __tablename__ = "config_proposals"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    proposed_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="PENDING")  # PENDING, APPROVED, REJECTED, REVERTED
    
    # JSON strings
    payload_json = Column(Text, nullable=False)
    previous_payload_json = Column(Text, nullable=True)
    
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    approved_at = Column(DateTime, nullable=True)

    institution = relationship("Institution")
    proposed_by = relationship("User", foreign_keys=[proposed_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
