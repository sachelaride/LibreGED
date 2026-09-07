from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class StorageAreaBase(BaseModel):
    name: str
    is_active: bool = True

class StorageAreaCreate(StorageAreaBase):
    pass

class StorageAreaResponse(StorageAreaBase):
    id: str
    created_at: datetime
    class Config:
        from_attributes = True

class StoragePartitionBase(BaseModel):
    name: str
    area_id: str
    max_files: int
    max_size_gb: float
    base_path: str
    network_domain: Optional[str] = None
    network_user: Optional[str] = None
    network_password: Optional[str] = None

class StoragePartitionCreate(StoragePartitionBase):
    pass

class StoragePartitionResponse(StoragePartitionBase):
    id: str
    current_file_count: int
    current_size_bytes: int
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True
