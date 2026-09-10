from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.database import get_db
from app import models
from app.auth import role_checker
from app.schemas_dashboard import DashboardStatsResponse, IngestionStats, WorkflowStats, HealthStats
from app.models_ged import GEDDocument, GEDDocumentStatus
from app.models_workflow import DocumentWorkflowInstance, WorkflowState
from app.models_integration import IntegrationConfig

router = APIRouter(tags=["Administração - Dashboard"])

AdminRoles = Depends(role_checker(["admin_global", "admin_instituicao"]))

@router.get("/api/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = AdminRoles
):
    # 1. Ingestion Stats
    query_ingest = db.query(models.IngestionJob.status, func.count(models.IngestionJob.id))
    if current_user.role != "admin_global":
        query_ingest = query_ingest.filter(models.IngestionJob.institution_id == current_user.institution_id)
    ingestion_counts = dict(query_ingest.group_by(models.IngestionJob.status).all())
    
    ingestion = IngestionStats(
        pending=ingestion_counts.get("PENDING", 0),
        processing=ingestion_counts.get("PROCESSING", 0),
        completed=ingestion_counts.get("COMPLETED", 0),
        failed=ingestion_counts.get("FAILED", 0),
        quarantine=ingestion_counts.get("QUARENTENA", 0),
        total=sum(ingestion_counts.values())
    )
    
    # 2. Quarantine Documents
    query_quarantine = db.query(func.count(GEDDocument.id)).filter(GEDDocument.status == GEDDocumentStatus.QUARENTENA)
    if current_user.role != "admin_global":
        query_quarantine = query_quarantine.filter(GEDDocument.institution_id == current_user.institution_id)
    quarantine_docs = query_quarantine.scalar() or 0
    
    # 3. Workflow Stats
    # We join with workflow state to see if it's completed
    query_wf = db.query(WorkflowState.is_completion, func.count(DocumentWorkflowInstance.id)).join(
        WorkflowState, DocumentWorkflowInstance.current_state_id == WorkflowState.id
    )
    if current_user.role != "admin_global":
        # Need to join document to filter by institution
        query_wf = query_wf.join(GEDDocument, DocumentWorkflowInstance.document_id == GEDDocument.id)\
                           .filter(GEDDocument.institution_id == current_user.institution_id)
                           
    wf_counts = dict(query_wf.group_by(WorkflowState.is_completion).all())
    workflow = WorkflowStats(
        active_instances=wf_counts.get(False, 0),
        completed_instances=wf_counts.get(True, 0)
    )
    
    # 4. Health Stats
    db_status = "Online"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "Offline"
        
    query_int = db.query(func.count(IntegrationConfig.id)).filter(IntegrationConfig.is_active == True)
    if current_user.role != "admin_global":
        query_int = query_int.filter(IntegrationConfig.institution_id == current_user.institution_id)
    integrations_count = query_int.scalar() or 0
    
    health = HealthStats(
        database=db_status,
        integrations_count=integrations_count
    )
    
    return DashboardStatsResponse(
        ingestion=ingestion,
        workflow=workflow,
        health=health,
        quarantine_documents=quarantine_docs
    )
