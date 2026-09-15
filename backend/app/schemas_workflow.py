from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

# --- States ---
class WorkflowStateBase(BaseModel):
    label: str
    is_initial: bool = False
    is_completion: bool = False
    ui_pos_x: Optional[int] = None
    ui_pos_y: Optional[int] = None
    node_type: Optional[str] = "task"

class WorkflowStateCreate(WorkflowStateBase):
    pass

class WorkflowStateUpdate(BaseModel):
    label: Optional[str] = None
    is_initial: Optional[bool] = None
    is_completion: Optional[bool] = None
    ui_pos_x: Optional[int] = None
    ui_pos_y: Optional[int] = None
    node_type: Optional[str] = None

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
    action_code: Optional[str] = None
    condition_key: Optional[str] = None
    condition_value: Optional[str] = None
    priority: int = 0
    is_default: bool = False
    allowed_roles: Optional[str] = None

class WorkflowTransitionCreate(WorkflowTransitionBase):
    pass

class WorkflowTransitionUpdate(BaseModel):
    origin_state_id: Optional[str] = None
    destination_state_id: Optional[str] = None
    label: Optional[str] = None
    action_code: Optional[str] = None
    condition_key: Optional[str] = None
    condition_value: Optional[str] = None
    priority: Optional[int] = None
    is_default: Optional[bool] = None
    allowed_roles: Optional[str] = None

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

# --- Tasks ---
class WorkflowTaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    assignee_id: str
    due_date: Optional[datetime.datetime] = None

class WorkflowTaskCreate(WorkflowTaskBase):
    instance_id: str

class WorkflowTaskResponse(WorkflowTaskBase):
    id: str
    instance_id: str
    status: str
    created_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    
    class Config:
        from_attributes = True

class TaskCompletionRequest(BaseModel):
    action: str  # ex: "APPROVE", "REJECT", "COMPLETE"
    comment: Optional[str] = None
    variables: dict[str, object] = Field(default_factory=dict)
