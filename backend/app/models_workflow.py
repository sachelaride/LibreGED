import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models import Base, utc_now

class Workflow(Base):
    __tablename__ = "ged_workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    internal_name = Column(String, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    
    states = relationship("WorkflowState", back_populates="workflow", cascade="all, delete-orphan")
    transitions = relationship("WorkflowTransition", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowState(Base):
    __tablename__ = "ged_workflow_states"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("ged_workflows.id"), nullable=False)
    label = Column(String, nullable=False)
    is_initial = Column(Boolean, default=False)
    is_completion = Column(Boolean, default=False)
    node_type = Column(String, default="task")
    
    # Visual positioning
    ui_pos_x = Column(Integer, nullable=True)
    ui_pos_y = Column(Integer, nullable=True)
    
    workflow = relationship("Workflow", back_populates="states")

class WorkflowTransition(Base):
    __tablename__ = "ged_workflow_transitions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_id", "origin_state_id", "destination_state_id",
            name="uq_workflow_transition_route",
        ),
    )
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("ged_workflows.id"), nullable=False)
    origin_state_id = Column(String, ForeignKey("ged_workflow_states.id"), nullable=False)
    destination_state_id = Column(String, ForeignKey("ged_workflow_states.id"), nullable=False)
    label = Column(String, nullable=False)
    action_code = Column(String, nullable=True)
    condition_key = Column(String, nullable=True)
    condition_value = Column(String, nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    is_default = Column(Boolean, nullable=False, default=False)
    allowed_roles = Column(String, nullable=True) # CSV format, e.g., "gestor_clinica,admin_global"
    
    workflow = relationship("Workflow", back_populates="transitions")
    origin_state = relationship("WorkflowState", foreign_keys=[origin_state_id])
    destination_state = relationship("WorkflowState", foreign_keys=[destination_state_id])

class DocumentWorkflowInstance(Base):
    __tablename__ = "ged_document_workflow_instances"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, nullable=False, index=True)
    workflow_id = Column(String, ForeignKey("ged_workflows.id"), nullable=False)
    current_state_id = Column(String, ForeignKey("ged_workflow_states.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    workflow = relationship("Workflow")
    current_state = relationship("WorkflowState")

class WorkflowTask(Base):
    __tablename__ = "ged_workflow_tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    instance_id = Column(String, ForeignKey("ged_document_workflow_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="PENDING", index=True) # PENDING, COMPLETED, CANCELLED
    assignee_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)
    
    instance = relationship("DocumentWorkflowInstance")
    assignee = relationship("User")
