from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app.database import get_db
from app import models, models_workflow
from app import auth
from app.schemas_workflow import (
    WorkflowCreate, WorkflowResponse,
    WorkflowStateCreate, WorkflowStateUpdate, WorkflowStateResponse,
    WorkflowTransitionCreate, WorkflowTransitionUpdate, WorkflowTransitionResponse,
    DocumentWorkflowInstanceCreate, DocumentWorkflowInstanceResponse,
    WorkflowTaskResponse, TaskCompletionRequest
    , WorkflowVersionResponse
)
from app.schemas_pagination import PaginatedResponse
import math
from datetime import datetime

router = APIRouter()


def _is_service_task(node_type: str | None) -> bool:
    """Accept the current frontend name and the legacy backend name."""
    return node_type in {"task_service", "service_task"}


def _workflow_snapshot(workflow):
    return {
        "name": workflow.name,
        "internal_name": workflow.internal_name,
        "is_active": workflow.is_active,
        "states": [
            {
                "id": state.id,
                "label": state.label,
                "is_initial": state.is_initial,
                "is_completion": state.is_completion,
                "node_type": state.node_type,
                "ui_pos_x": state.ui_pos_x,
                "ui_pos_y": state.ui_pos_y,
                "config": state.config,
            }
            for state in workflow.states
        ],
        "transitions": [
            {
                "origin_state_id": transition.origin_state_id,
                "destination_state_id": transition.destination_state_id,
                "label": transition.label,
                "action_code": transition.action_code,
                "condition_key": transition.condition_key,
                "condition_value": transition.condition_value,
                "priority": transition.priority,
                "is_default": transition.is_default,
                "allowed_roles": transition.allowed_roles,
            }
            for transition in workflow.transitions
        ],
    }


@router.get("/workflows/{workflow_id}/export", tags=["Admin - Workflows"])
def export_workflow(workflow_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    workflow = db.get(models_workflow.Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow não encontrado")
    snapshot = _workflow_snapshot(workflow)
    snapshot["format"] = "libreged-workflow"
    snapshot["format_version"] = 1
    return JSONResponse(content=snapshot, headers={"Content-Disposition": f'attachment; filename="{workflow.internal_name}.json"'})


@router.get("/workflows/{workflow_id}/versions", response_model=List[WorkflowVersionResponse], tags=["Admin - Workflows"])
def list_workflow_versions(workflow_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    if not db.get(models_workflow.Workflow, workflow_id):
        raise HTTPException(status_code=404, detail="Workflow não encontrado")
    return db.query(models_workflow.WorkflowVersion).filter_by(workflow_id=workflow_id).order_by(
        models_workflow.WorkflowVersion.version_number.desc()
    ).all()


@router.post("/workflows/{workflow_id}/versions/publish", response_model=WorkflowVersionResponse, tags=["Admin - Workflows"])
def publish_workflow_version(workflow_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    workflow = db.get(models_workflow.Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow não encontrado")
    number = (db.query(models_workflow.WorkflowVersion).filter_by(workflow_id=workflow_id).count() or 0) + 1
    db.query(models_workflow.WorkflowVersion).filter_by(workflow_id=workflow_id, status="PUBLISHED").update({"status": "ARCHIVED"})
    version = models_workflow.WorkflowVersion(
        workflow_id=workflow_id,
        version_number=number,
        status="PUBLISHED",
        snapshot_json=json.dumps(_workflow_snapshot(workflow), ensure_ascii=False),
        created_by_user_id=current_user.id,
        published_at=datetime.utcnow(),
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.post("/workflows/{workflow_id}/versions/{version_number}/restore", response_model=WorkflowVersionResponse, tags=["Admin - Workflows"])
def restore_workflow_version(
    workflow_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin),
):
    workflow = db.get(models_workflow.Workflow, workflow_id)
    version = db.query(models_workflow.WorkflowVersion).filter_by(
        workflow_id=workflow_id, version_number=version_number
    ).first()
    if workflow is None or version is None:
        raise HTTPException(status_code=404, detail="Workflow ou versão não encontrados")
    snapshot = json.loads(version.snapshot_json)
    db.query(models_workflow.WorkflowTransition).filter_by(workflow_id=workflow_id).delete()
    db.query(models_workflow.WorkflowState).filter_by(workflow_id=workflow_id).delete()
    db.flush()
    id_map = {}
    for item in snapshot.get("states", []):
        state = models_workflow.WorkflowState(
            workflow_id=workflow_id,
            label=item["label"],
            is_initial=bool(item.get("is_initial", False)),
            is_completion=bool(item.get("is_completion", False)),
            node_type=item.get("node_type") or "task",
            ui_pos_x=item.get("ui_pos_x"),
            ui_pos_y=item.get("ui_pos_y"),
            config_json=json.dumps(item.get("config") or {}, ensure_ascii=False),
        )
        db.add(state)
        id_map[item.get("id")] = state
    db.flush()
    for item in snapshot.get("transitions", []):
        origin = id_map.get(item.get("origin_state_id"))
        destination = id_map.get(item.get("destination_state_id"))
        if origin and destination:
            db.add(models_workflow.WorkflowTransition(
                workflow_id=workflow_id,
                origin_state_id=origin.id,
                destination_state_id=destination.id,
                label=item["label"],
                action_code=item.get("action_code"),
                condition_key=item.get("condition_key"),
                condition_value=item.get("condition_value"),
                priority=item.get("priority", 0),
                is_default=bool(item.get("is_default", False)),
                allowed_roles=item.get("allowed_roles"),
            ))
    db.query(models_workflow.WorkflowVersion).filter_by(workflow_id=workflow_id, status="PUBLISHED").update({"status": "ARCHIVED"})
    new_number = db.query(models_workflow.WorkflowVersion).filter_by(workflow_id=workflow_id).count() + 1
    restored = models_workflow.WorkflowVersion(
        workflow_id=workflow_id,
        version_number=new_number,
        status="PUBLISHED",
        snapshot_json=json.dumps(_workflow_snapshot(workflow), ensure_ascii=False),
        created_by_user_id=current_user.id,
        published_at=datetime.utcnow(),
    )
    db.add(restored)
    db.commit()
    db.refresh(restored)
    return restored


@router.post("/workflows/import", response_model=WorkflowResponse, tags=["Admin - Workflows"])
async def import_workflow(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin),
):
    try:
        payload = json.loads((await file.read()).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Arquivo de workflow JSON inválido") from exc
    if payload.get("format") not in (None, "libreged-workflow"):
        raise HTTPException(status_code=422, detail="Formato de workflow não reconhecido")
    name = payload.get("name")
    internal_name = payload.get("internal_name")
    if not name or not internal_name:
        raise HTTPException(status_code=422, detail="Nome e nome interno são obrigatórios")
    if db.query(models_workflow.Workflow).filter(
        (models_workflow.Workflow.name == name) | (models_workflow.Workflow.internal_name == internal_name)
    ).first():
        raise HTTPException(status_code=409, detail="Já existe workflow com este nome")
    workflow = models_workflow.Workflow(name=name, internal_name=internal_name, is_active=bool(payload.get("is_active", True)))
    db.add(workflow)
    db.flush()
    id_map = {}
    for item in payload.get("states", []):
        state = models_workflow.WorkflowState(
            workflow_id=workflow.id,
            label=item["label"],
            is_initial=bool(item.get("is_initial", False)),
            is_completion=bool(item.get("is_completion", False)),
            node_type=item.get("node_type") or "task",
            ui_pos_x=item.get("ui_pos_x"),
            ui_pos_y=item.get("ui_pos_y"),
            config_json=json.dumps(item.get("config") or {}, ensure_ascii=False),
        )
        db.add(state)
        id_map[item.get("id")] = state
    db.flush()
    for item in payload.get("transitions", []):
        origin = id_map.get(item.get("origin_state_id"))
        destination = id_map.get(item.get("destination_state_id"))
        if not origin or not destination:
            continue
        db.add(models_workflow.WorkflowTransition(
            workflow_id=workflow.id,
            origin_state_id=origin.id,
            destination_state_id=destination.id,
            label=item["label"],
            action_code=item.get("action_code"),
            condition_key=item.get("condition_key"),
            condition_value=item.get("condition_value"),
            priority=item.get("priority", 0),
            is_default=bool(item.get("is_default", False)),
            allowed_roles=item.get("allowed_roles"),
        ))
    db.commit()
    db.refresh(workflow)
    return workflow


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
    duplicate_name = db.query(models_workflow.Workflow).filter(
        models_workflow.Workflow.name == wkf_in.name
    ).first()
    if duplicate_name:
        raise HTTPException(
            status_code=409,
            detail="Já existe um workflow com este nome.",
        )

    duplicate_internal_name = db.query(models_workflow.Workflow).filter(
        models_workflow.Workflow.internal_name == wkf_in.internal_name
    ).first()
    if duplicate_internal_name:
        raise HTTPException(
            status_code=409,
            detail="Já existe um workflow com este nome interno.",
        )

    wkf = models_workflow.Workflow(
        name=wkf_in.name,
        internal_name=wkf_in.internal_name,
        is_active=wkf_in.is_active
    )
    db.add(wkf)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe um workflow com este nome ou nome interno.",
        ) from exc
    db.refresh(wkf)
    
    from app.main import add_audit
    add_audit(db, "workflow", wkf.id, "created", f"Workflow {wkf.name} created", current_user.id)
    
    return wkf

@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse, tags=["Admin - Workflows"])
def update_workflow(workflow_id: str, wkf_in: WorkflowCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    wkf = db.query(models_workflow.Workflow).filter_by(id=workflow_id).first()
    if not wkf:
        raise HTTPException(status_code=404, detail="Workflow não encontrado")

    duplicate = db.query(models_workflow.Workflow).filter(
        models_workflow.Workflow.id != workflow_id,
        (models_workflow.Workflow.name == wkf_in.name)
        | (models_workflow.Workflow.internal_name == wkf_in.internal_name),
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Já existe outro workflow com este nome ou nome interno.",
        )
    
    wkf.name = wkf_in.name
    wkf.internal_name = wkf_in.internal_name
    wkf.is_active = wkf_in.is_active
    
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe outro workflow com este nome ou nome interno.",
        ) from exc
    db.refresh(wkf)
    
    from app.main import add_audit
    add_audit(db, "workflow", wkf.id, "updated", f"Workflow {wkf.name} updated", current_user.id)
    
    return wkf

@router.delete("/workflows/{workflow_id}", status_code=204, tags=["Admin - Workflows"])
def delete_workflow(workflow_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    wkf = db.query(models_workflow.Workflow).filter_by(id=workflow_id).first()
    if not wkf:
        raise HTTPException(status_code=404, detail="Workflow não encontrado")
    
    # Optional: block deletion if it has instances
    has_instances = db.query(models_workflow.DocumentWorkflowInstance).filter_by(workflow_id=workflow_id).first()
    if has_instances:
        raise HTTPException(status_code=409, detail="Não é possível excluir um workflow que possui instâncias em execução. Desative-o em vez disso.")
    
    from app.main import add_audit
    add_audit(db, "workflow", wkf.id, "deleted", f"Workflow {wkf.name} deleted", current_user.id)
    
    db.delete(wkf)
    db.commit()
    return None

# --- STATES ---
@router.post("/workflows/{workflow_id}/states", response_model=WorkflowStateResponse, tags=["Admin - Workflows"])
def create_state(workflow_id: str, state_in: WorkflowStateCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    workflow = db.get(models_workflow.Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow não encontrado")
    if state_in.is_initial and db.query(models_workflow.WorkflowState).filter_by(
        workflow_id=workflow_id, is_initial=True
    ).first():
        raise HTTPException(status_code=409, detail="O workflow já possui um estado inicial.")
    state = models_workflow.WorkflowState(
        workflow_id=workflow_id,
        label=state_in.label,
        is_initial=state_in.is_initial,
        is_completion=state_in.is_completion,
        ui_pos_x=state_in.ui_pos_x,
        ui_pos_y=state_in.ui_pos_y,
        node_type=state_in.node_type,
        config_json=json.dumps(state_in.config or {}, ensure_ascii=False),
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state

@router.put("/workflows/{workflow_id}/states/{state_id}", response_model=WorkflowStateResponse, tags=["Admin - Workflows"])
def update_state(workflow_id: str, state_id: str, state_in: WorkflowStateUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    state = db.query(models_workflow.WorkflowState).filter_by(id=state_id, workflow_id=workflow_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="Estado não encontrado")
    if state_in.is_initial:
        another_initial = db.query(models_workflow.WorkflowState).filter(
            models_workflow.WorkflowState.workflow_id == workflow_id,
            models_workflow.WorkflowState.is_initial.is_(True),
            models_workflow.WorkflowState.id != state_id,
        ).first()
        if another_initial:
            raise HTTPException(status_code=409, detail="O workflow já possui um estado inicial.")
    if state_in.label is not None: state.label = state_in.label
    if state_in.is_initial is not None: state.is_initial = state_in.is_initial
    if state_in.is_completion is not None: state.is_completion = state_in.is_completion
    if state_in.ui_pos_x is not None: state.ui_pos_x = state_in.ui_pos_x
    if state_in.ui_pos_y is not None: state.ui_pos_y = state_in.ui_pos_y
    if state_in.node_type is not None: state.node_type = state_in.node_type
    if state_in.config is not None:
        state.config_json = json.dumps(state_in.config, ensure_ascii=False)
    db.commit()
    db.refresh(state)
    return state

@router.delete("/workflows/{workflow_id}/states/{state_id}", status_code=204, tags=["Admin - Workflows"])
def delete_state(workflow_id: str, state_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    state = db.query(models_workflow.WorkflowState).filter_by(id=state_id, workflow_id=workflow_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="Estado não encontrado")
    if db.query(models_workflow.WorkflowTransition).filter(
        (models_workflow.WorkflowTransition.origin_state_id == state_id)
        | (models_workflow.WorkflowTransition.destination_state_id == state_id)
    ).first() or db.query(models_workflow.DocumentWorkflowInstance).filter_by(
        current_state_id=state_id
    ).first():
        raise HTTPException(status_code=409, detail="Estado em uso; remova vínculos antes de excluir.")
    db.delete(state)
    db.commit()
    return None

# --- TRANSITIONS ---
@router.post("/workflows/{workflow_id}/transitions", response_model=WorkflowTransitionResponse, tags=["Admin - Workflows"])
def create_transition(workflow_id: str, transition_in: WorkflowTransitionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    if (transition_in.condition_key is None) != (transition_in.condition_value is None):
        raise HTTPException(status_code=422, detail="condition_key e condition_value devem ser informados juntos.")
    workflow = db.get(models_workflow.Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow não encontrado")
    states = db.query(models_workflow.WorkflowState).filter(
        models_workflow.WorkflowState.workflow_id == workflow_id,
        models_workflow.WorkflowState.id.in_(
            [transition_in.origin_state_id, transition_in.destination_state_id]
        ),
    ).all()
    if len(states) != 2 or transition_in.origin_state_id == transition_in.destination_state_id:
        raise HTTPException(status_code=422, detail="Origem e destino devem ser estados distintos do workflow.")
    duplicate = db.query(models_workflow.WorkflowTransition).filter_by(
        workflow_id=workflow_id,
        origin_state_id=transition_in.origin_state_id,
        destination_state_id=transition_in.destination_state_id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A transição entre estes estados já existe.")
    if transition_in.is_default and db.query(models_workflow.WorkflowTransition).filter_by(
        workflow_id=workflow_id,
        origin_state_id=transition_in.origin_state_id,
        is_default=True,
    ).first():
        raise HTTPException(status_code=409, detail="O estado já possui uma transição padrão.")
    transition = models_workflow.WorkflowTransition(
        workflow_id=workflow_id,
        origin_state_id=transition_in.origin_state_id,
        destination_state_id=transition_in.destination_state_id,
        label=transition_in.label,
        action_code=transition_in.action_code,
        condition_key=transition_in.condition_key,
        condition_value=transition_in.condition_value,
        priority=transition_in.priority,
        is_default=transition_in.is_default,
        allowed_roles=transition_in.allowed_roles
    )
    db.add(transition)
    db.commit()
    db.refresh(transition)
    return transition

@router.put("/workflows/{workflow_id}/transitions/{transition_id}", response_model=WorkflowTransitionResponse, tags=["Admin - Workflows"])
def update_transition(workflow_id: str, transition_id: str, transition_in: WorkflowTransitionUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    transition = db.query(models_workflow.WorkflowTransition).filter_by(id=transition_id, workflow_id=workflow_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transição não encontrada")

    if transition_in.condition_key is None and transition_in.condition_value is not None:
        raise HTTPException(status_code=422, detail="condition_key e condition_value devem ser informados juntos.")
    if transition_in.condition_key is not None and transition_in.condition_value is None:
        raise HTTPException(status_code=422, detail="condition_key e condition_value devem ser informados juntos.")

    origin_state_id = transition_in.origin_state_id or transition.origin_state_id
    destination_state_id = transition_in.destination_state_id or transition.destination_state_id
    if origin_state_id == destination_state_id:
        raise HTTPException(status_code=422, detail="Origem e destino devem ser estados distintos do workflow.")

    if transition_in.origin_state_id is not None or transition_in.destination_state_id is not None:
        states = db.query(models_workflow.WorkflowState).filter(
            models_workflow.WorkflowState.workflow_id == workflow_id,
            models_workflow.WorkflowState.id.in_([origin_state_id, destination_state_id]),
        ).all()
        if len(states) != 2:
            raise HTTPException(status_code=422, detail="Origem e destino devem pertencer ao workflow informado.")

    duplicate = db.query(models_workflow.WorkflowTransition).filter(
        models_workflow.WorkflowTransition.workflow_id == workflow_id,
        models_workflow.WorkflowTransition.origin_state_id == origin_state_id,
        models_workflow.WorkflowTransition.destination_state_id == destination_state_id,
        models_workflow.WorkflowTransition.id != transition_id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A transição entre estes estados já existe.")

    if transition_in.is_default and db.query(models_workflow.WorkflowTransition).filter(
        models_workflow.WorkflowTransition.workflow_id == workflow_id,
        models_workflow.WorkflowTransition.origin_state_id == origin_state_id,
        models_workflow.WorkflowTransition.is_default.is_(True),
        models_workflow.WorkflowTransition.id != transition_id,
    ).first():
        raise HTTPException(status_code=409, detail="O estado já possui uma transição padrão.")

    if transition_in.label is not None:
        transition.label = transition_in.label
    if transition_in.origin_state_id is not None:
        transition.origin_state_id = transition_in.origin_state_id
    if transition_in.destination_state_id is not None:
        transition.destination_state_id = transition_in.destination_state_id
    if transition_in.action_code is not None:
        transition.action_code = transition_in.action_code
    if transition_in.condition_key is not None:
        transition.condition_key = transition_in.condition_key
    if transition_in.condition_value is not None:
        transition.condition_value = transition_in.condition_value
    if transition_in.priority is not None:
        transition.priority = transition_in.priority
    if transition_in.is_default is not None:
        transition.is_default = transition_in.is_default
    if transition_in.allowed_roles is not None:
        transition.allowed_roles = transition_in.allowed_roles

    db.commit()
    db.refresh(transition)
    return transition

@router.delete("/workflows/{workflow_id}/transitions/{transition_id}", status_code=204, tags=["Admin - Workflows"])
def delete_transition(workflow_id: str, transition_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    transition = db.query(models_workflow.WorkflowTransition).filter_by(id=transition_id, workflow_id=workflow_id).first()
    if not transition:
        raise HTTPException(status_code=404, detail="Transição não encontrada")
    db.delete(transition)
    db.commit()
    return None

# --- EXECUTION & TASKS ---
@router.post("/workflows/instances", response_model=DocumentWorkflowInstanceResponse, tags=["Workflows - Execution"])
def start_workflow_instance(
    payload: DocumentWorkflowInstanceCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_active_user)
):
    from app.api_document_operations import obter_documento
    obter_documento(db, user, payload.document_id, "iniciar_fluxo")
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
    from sqlalchemy import or_
    from app.models_workflow import WorkflowTask, DocumentWorkflowInstance
    from app.models_ged import GEDDocument
    
    query = db.query(WorkflowTask).join(
        DocumentWorkflowInstance, DocumentWorkflowInstance.id == WorkflowTask.instance_id
    ).join(
        GEDDocument, GEDDocument.id == DocumentWorkflowInstance.document_id
    ).filter(
        WorkflowTask.status == "PENDING",
        or_(
            WorkflowTask.assignee_id == user.id,
            WorkflowTask.assignee_role == user.role
        )
    )
    
    if user.role != "admin_global":
        query = query.filter(GEDDocument.institution_id == user.institution_id)
        
    tasks = query.all()
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
        
    if task.assignee_id != user.id and task.assignee_role != user.role and user.role != "admin_global":
        raise HTTPException(status_code=403, detail="You can only complete your own tasks")
        
    if task.status != "PENDING":
        raise HTTPException(status_code=400, detail="Task is already completed or cancelled")
        
    from app.api_document_operations import obter_documento
    documento_autorizado = obter_documento(db, user, task.instance.document_id, "executar_fluxo")
    instance = task.instance
    transitions = db.query(models_workflow.WorkflowTransition).filter_by(
        workflow_id=instance.workflow_id,
        origin_state_id=instance.current_state_id,
    ).all()
    action = payload.action.strip().casefold()
    candidates = [
        item for item in transitions
        if action in {
            (item.action_code or "").strip().casefold(),
            item.label.strip().casefold(),
        }
    ]
    matching = [
        item for item in candidates
        if item.condition_key is None
        or str(payload.variables.get(item.condition_key)) == item.condition_value
    ]
    conditional_matching = [item for item in matching if item.condition_key is not None]
    if conditional_matching:
        matching = conditional_matching
    transition = next(
        iter(sorted(
            matching,
            key=lambda item: (item.is_default, item.priority),
            reverse=True,
        )),
        None,
    )
    if transition is None:
        raise HTTPException(
            status_code=422,
            detail="A ação informada não possui transição disponível no estado atual.",
        )
    if transition.allowed_roles:
        roles = {role.strip() for role in transition.allowed_roles.split(",") if role.strip()}
        if user.role not in roles and user.role != "admin_global":
            raise HTTPException(status_code=403, detail="Seu papel não pode executar esta transição.")
    new_state = db.get(models_workflow.WorkflowState, transition.destination_state_id)
    if new_state is None:
        raise HTTPException(status_code=409, detail="Estado de destino da transição não existe.")
    task.status = "COMPLETED"
    task.completed_at = datetime.now()
    instance.current_state_id = new_state.id
    
    # Criar nova tarefa se o estado não for final
    if not new_state.is_completion:
        if _is_service_task(new_state.node_type):
            # Auto-executa a service task
            print(f"Executando Service Task: {new_state.label} para o doc {instance.document_id}")
            st_task = models_workflow.WorkflowTask(
                instance_id=instance.id,
                name=new_state.label,
                description="Execução automatizada (Service Task)",
                status="COMPLETED",
                completed_at=datetime.now()
            )
            db.add(st_task)
            
            # TODO: Auto-avançar o fluxo após service task seria ideal, 
            # mas simplificamos logando a ação por agora.
        else:
            # Tarefa manual normal
            next_task = models_workflow.WorkflowTask(
                instance_id=instance.id,
                name=new_state.label,
                description="Aguardando ação do usuário",
                assignee_role=transition.allowed_roles.split(",")[0].strip() if transition.allowed_roles else None,
                status="PENDING"
            )
            db.add(next_task)
    previous_status = documento_autorizado.status
    if new_state.is_completion:
        documento_autorizado.status = GEDDocumentStatus.VALIDO
    from app.models_ged import DocumentTransitionHistory
    db.add(DocumentTransitionHistory(
        document_id=documento_autorizado.id,
        from_status=previous_status,
        to_status=documento_autorizado.status,
        changed_by_user_id=user.id,
        comments=f"Tarefa concluída: {payload.action}; transição: {transition.label}",
    ))
    db.commit()
    return {"message": "Task completed successfully", "transition_id": transition.id, "state_id": new_state.id}

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
            
    from app.api_document_operations import obter_documento
    documento_autorizado = obter_documento(db, user, instance.document_id, "executar_fluxo")
    from app.models_ged import GEDDocumentStatus
    if documento_autorizado.status in (GEDDocumentStatus.ASSINADO, GEDDocumentStatus.ARQUIVADO):
        raise HTTPException(409, "Documento assinado ou arquivado não permite alteração pelo fluxo.")
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
        
    if not new_state.is_completion:
        if _is_service_task(new_state.node_type):
            print(f"Executando Service Task: {new_state.label} para o doc {instance.document_id}")
            st_task = models_workflow.WorkflowTask(
                instance_id=instance.id,
                name=new_state.label,
                description="Execução automatizada (Service Task)",
                status="COMPLETED",
                completed_at=datetime.now()
            )
            db.add(st_task)
        else:
            next_task = models_workflow.WorkflowTask(
                instance_id=instance.id,
                name=new_state.label,
                description="Aguardando ação do usuário",
                assignee_role=transition.allowed_roles.split(",")[0].strip() if transition.allowed_roles else None,
                status="PENDING"
            )
            db.add(next_task)
        
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
