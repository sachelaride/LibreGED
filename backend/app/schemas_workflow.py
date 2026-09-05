from pydantic import BaseModel
from typing import List, Optional
import datetime

# --- States ---
class WorkflowStateBase(BaseModel):
    label: str
    is_initial: bool = False
    is_completion: bool = False

class WorkflowStateCreate(WorkflowStateBase):
    pass

class WorkflowStateResponse(WorkflowStateBase):
    id: str
    workflow_id: str
    
    class Config:
        from_attributes = True

# --- Transitions ---
class WorkflowTransitionBase(BaseModel):
    origin_state_id: str
    destination_state_id: str
    label: str

class WorkflowTransitionCreate(WorkflowTransitionBase):
    pass

class WorkflowTransitionResponse(WorkflowTransitionBase):
    id: str
    workflow_id: str
    
    class Config:
        from_attributes = True

# --- Workflows ---
class WorkflowBase(BaseModel):
    name: str
    internal_name: str
    is_active: bool = True

class WorkflowCreate(WorkflowBase):
    pass

class WorkflowResponse(WorkflowBase):
    id: str
    created_at: datetime.datetime
    states: List[WorkflowStateResponse] = []
    transitions: List[WorkflowTransitionResponse] = []
    
    class Config:
        from_attributes = True

# --- Instances ---
class DocumentWorkflowInstanceBase(BaseModel):
    document_id: str
    workflow_id: str
    current_state_id: str

class DocumentWorkflowInstanceCreate(DocumentWorkflowInstanceBase):
    pass

class DocumentWorkflowInstanceResponse(DocumentWorkflowInstanceBase):
    id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    class Config:
        from_attributes = True
