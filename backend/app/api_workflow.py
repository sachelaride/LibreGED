from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, models_workflow
from app import auth
from app.schemas_workflow import (
    WorkflowCreate, WorkflowResponse,
    WorkflowStateCreate, WorkflowStateResponse,
    WorkflowTransitionCreate, WorkflowTransitionResponse
)
from app.schemas_pagination import PaginatedResponse
import math

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
        label=transition_in.label
    )
    db.add(transition)
    db.commit()
    db.refresh(transition)
    return transition
