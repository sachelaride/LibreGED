from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ConfigProposalCreate(BaseModel):
    payload_json: str

class ConfigProposalResponse(BaseModel):
    id: str
    institution_id: str
    proposed_by_id: str
    status: str
    payload_json: str
    previous_payload_json: Optional[str] = None
    approved_by_id: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
