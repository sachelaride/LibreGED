from pydantic import BaseModel
from typing import Dict

class IngestionStats(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int
    quarantine: int
    total: int

class WorkflowStats(BaseModel):
    active_instances: int
    completed_instances: int

class HealthStats(BaseModel):
    database: str
    integrations_count: int

class DashboardStatsResponse(BaseModel):
    ingestion: IngestionStats
    workflow: WorkflowStats
    health: HealthStats
    quarantine_documents: int
