from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, models_workflow
from app import auth
from app.schemas_workflow import (
    WorkflowCreate, WorkflowResponse,
    WorkflowStateCreate, WorkflowStateResponse,
    WorkflowTransitionCreate, WorkflowTransitionResponse,
    DocumentWorkflowInstanceCreate, DocumentWorkflowInstanceResponse,
    WorkflowTaskResponse, TaskCompletionRequest
)
from app.schemas_pagination import PaginatedResponse
import math
from datetime import datetime

router = APIRouter()

# --- WORKFLOWS ---
@router.get("/workflows", response_model=PaginatedResponse[WorkflowResponse], tags=["Admin - Workflows"])
def get_workflows(page: int = 1, size: int = 50, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    query = db.query(models_workflow.Workflow)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/workflows", response_model=WorkflowResponse, tags=["Admin - Workflows"])
def create_workflow(wkf_in: WorkflowCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    wkf = models_workflow.Workflow(
        name=wkf_in.name,
        internal_name=wkf_in.internal_name,
        is_active=wkf_in.is_active
    )
    db.add(wkf)
    db.commit()
    db.refresh(wkf)
    return wkf

# --- STATES ---
@router.post("/workflows/{workflow_id}/states", response_model=WorkflowStateResponse, tags=["Admin - Workflows"])
def create_state(workflow_id: str, state_in: WorkflowStateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    state = models_workflow.WorkflowState(
        workflow_id=workflow_id,
        label=state_in.label,
        is_initial=state_in.is_initial,
        is_completion=state_in.is_completion
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state

# --- TRANSITIONS ---
@router.post("/workflows/{workflow_id}/transitions", response_model=WorkflowTransitionResponse, tags=["Admin - Workflows"])
def create_transition(workflow_id: str, transition_in: WorkflowTransitionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    transition = models_workflow.WorkflowTransition(
        workflow_id=workflow_id,
        origin_state_id=transition_in.origin_state_id,
        destination_state_id=transition_in.destination_state_id,
        label=transition_in.label,
        allowed_roles=transition_in.allowed_roles
    )
    db.add(transition)
    db.commit()
    db.refresh(transition)
    return transition

# --- EXECUTION & TASKS ---
@router.post("/workflows/instances", response_model=DocumentWorkflowInstanceResponse, tags=["Workflows - Execution"])
def start_workflow_instance(
    payload: DocumentWorkflowInstanceCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_active_user)
):
    # Fetch workflow to get the initial state
    workflow = db.query(models_workflow.Workflow).filter_by(id=payload.workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    initial_state = db.query(models_workflow.WorkflowState).filter_by(
        workflow_id=workflow.id, is_initial=True
    ).first()
    
    if not initial_state:
        raise HTTPException(status_code=400, detail="Workflow has no initial state defined")
        
    instance = models_workflow.DocumentWorkflowInstance(
        document_id=payload.document_id,
        workflow_id=workflow.id,
        current_state_id=initial_state.id
    )
    db.add(instance)
    db.flush() # flush to get instance.id
    
    # We create an initial task assigned to the user who started it just to trigger the chain
    # Or in a real scenario, we determine the next assignee based on workflow rules.
    # For simplicity, we assign it to the initiator so they can do the first step, or we can just let it sit.
    task = models_workflow.WorkflowTask(
        instance_id=instance.id,
        name=f"Started Workflow: {workflow.name}",
        description="Initial state of the workflow",
        assignee_id=user.id,
        status="PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(instance)
    
    return instance

@router.get("/workflows/tasks/my-tasks", response_model=List[WorkflowTaskResponse], tags=["Workflows - Execution"])
def get_my_tasks(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_active_user)
):
    tasks = db.query(models_workflow.WorkflowTask).filter_by(
        assignee_id=user.id,
        status="PENDING"
    ).all()
    return tasks

@router.put("/workflows/tasks/{task_id}/complete", tags=["Workflows - Execution"])
def complete_task(
    task_id: str,
    payload: TaskCompletionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_active_user)
):
    task = db.query(models_workflow.WorkflowTask).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.assignee_id != user.id and user.role != "admin_global":
        raise HTTPException(status_code=403, detail="You can only complete your own tasks")
        
    if task.status != "PENDING":
        raise HTTPException(status_code=400, detail="Task is already completed or cancelled")
        
    task.status = "COMPLETED"
    task.completed_at = datetime.utcnow()
    
    # In a real workflow engine, we would parse `payload.action` (e.g. APPROVE)
    # and find the WorkflowTransition matching it to advance the instance.current_state_id.
    # For now, we will simply close the task.
    
    
    db.commit()
    return {"message": "Task completed successfully"}

@router.post("/workflows/instances/{instance_id}/transition/{transition_id}", response_model=DocumentWorkflowInstanceResponse, tags=["Workflows - Execution"])
def execute_transition(
    instance_id: str,
    transition_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_active_user)
):
    instance = db.query(models_workflow.DocumentWorkflowInstance).filter_by(id=instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
        
    transition = db.query(models_workflow.WorkflowTransition).filter_by(id=transition_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transition not found")
        
    if transition.workflow_id != instance.workflow_id:
        raise HTTPException(status_code=400, detail="Transition does not belong to this workflow")
        
    if transition.origin_state_id != instance.current_state_id:
        raise HTTPException(status_code=400, detail="Transition origin does not match current state")
        
    # Check Segregation of Duties (Roles)
    if transition.allowed_roles:
        roles = [r.strip() for r in transition.allowed_roles.split(",") if r.strip()]
        if user.role not in roles and user.role != "admin_global":
            raise HTTPException(status_code=403, detail="Acesso negado. Seu papel não tem permissão para realizar esta transição.")
            
    # Advance state
    instance.current_state_id = transition.destination_state_id
    
    # Check if new state is completion state
    new_state = db.query(models_workflow.WorkflowState).filter_by(id=transition.destination_state_id).first()
    
    # Audit Transition History on Document
    from app.models_ged import GEDDocument, DocumentTransitionHistory, GEDDocumentStatus
    doc = db.query(GEDDocument).filter_by(id=instance.document_id).first()
    
    old_status = doc.status if doc else None
    
    if doc and new_state and new_state.is_completion:
        doc.status = GEDDocumentStatus.VALIDO
        
    if doc:
        hist = DocumentTransitionHistory(
            document_id=doc.id,
            from_status=old_status,
            to_status=doc.status,
            changed_by_user_id=user.id,
            comments=f"Transição de Workflow executada: {transition.label} -> {new_state.label}"
        )
        db.add(hist)
        
    db.commit()
    db.refresh(instance)
    return instance
