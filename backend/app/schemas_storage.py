from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StorageRuleBase(BaseModel):
    name: str
    document_type_id: Optional[str] = None
    document_type_name: Optional[str] = None # Used for auto-creation
    storage_type: str = "Local"
    base_path: str
    max_files_per_folder: int = 10000
    max_gb_per_folder: float = 100.0
    enable_duplication: bool = False
    secondary_storage_type: Optional[str] = None
    secondary_base_path: Optional[str] = None
    network_domain: Optional[str] = None
    network_user: Optional[str] = None
    network_password: Optional[str] = None
    is_active: bool = True

class StorageRuleCreate(StorageRuleBase):
    pass

class StorageRuleResponse(StorageRuleBase):
    id: str
    current_file_count: int
    current_size_bytes: int
    created_at: datetime
    class Config:
        from_attributes = True
