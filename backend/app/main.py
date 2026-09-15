from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4
from xml.sax.saxutils import escape, quoteattr

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
from datetime import timedelta
from app.config import settings

from app.storage import delete_file, save_file, reconcile_document_storage
from app.upload_validation import read_validated_upload
from app.database import get_db
from app import models
from app.search import search_service
from app.retention import RetentionService
from app.auth import get_current_active_user, role_checker, check_institution_access
from app.filewatch import run_filewatch_cycle
from fastapi_utils.tasks import repeat_every

from app.schemas_historico import Model as HistoricoPayload
from app.historico_generator import generate_historico_xml
from app.schemas_diploma import Model as DiplomaPayload
from app.diploma_generator import generate_diploma_xml, generate_academica_xml
from app.schemas_curriculo import Model as CurriculoPayload
from app.curriculo_generator import generate_curriculo_xml
from app.academic_validator import ValidationRequest, validate_documents
from app.schemas_ged import GEDDocumentCreate, GEDDocumentResponse, DocumentStatusUpdate, DocumentTransitionResponse, DocumentCategoryCreate, DocumentCategoryResponse
from app.models_ged import GEDDocument, DocumentCategory, DocumentTransitionHistory, GEDDocumentStatus
from app.ocr_engine import DocumentAnalyzer

tags_metadata = [
    {
        "name": "GED - Documentação Jurídica (IES)",
        "description": "Fase 1: Gerenciamento dos dados e documentos legais da Instituição de Ensino Superior.",
    },
    {
        "name": "GED - Vida Acadêmica (Matrícula)",
        "description": "Fase 2: Ingresso do aluno, documentação pessoal (RG, CPF) e contratos.",
    },
    {
        "name": "GED - Vida Acadêmica (Curso)",
        "description": "Fase 3: Acompanhamento durante o curso. Histórico Escolar e Currículo Escolar.",
    },
    {
        "name": "GED - Vida Acadêmica (Diplomação)",
        "description": "Fase 4: Conclusão. Emissão do Diploma Digital e Documentação Acadêmica de Registro.",
    },
    {
        "name": "GED - Validações",
        "description": "Auditoria, motor de consistência acadêmica inter-documentos e checagens anti-fraude.",
    },
    {
        "name": "Sistema - Segurança e Acessos",
        "description": "Autenticação, controle de usuários (Admin, Recepcionista, Acadêmico) e permissões por campus/unidade.",
    }
]

from contextlib import asynccontextmanager
from app.worker_fila import start_worker, stop_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import SessionLocal
    from app.models import User
    from app.auth import get_password_hash
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        import uuid
        new_admin = User(
            id=uuid.uuid4().hex,
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role="admin_global"
        )
        db.add(new_admin)
        db.commit()
    db.close()
    
    start_worker()
    yield
    stop_worker()

app = FastAPI(title="EduGED Libre API", version="0.1.0", openapi_tags=tags_metadata, lifespan=lifespan)

@app.on_event("startup")
@repeat_every(seconds=10)
async def filewatch_task():
    try:
        await run_filewatch_cycle()
    except Exception as e:
        print(f"Erro no ciclo FileWatch: {e}")


@app.on_event("startup")
@repeat_every(seconds=3600, wait_first=True)
async def storage_reconciliation_task():
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        report = reconcile_document_storage(db)
        if not report["consistent"]:
            add_audit(
                db,
                "storage",
                "reconciliation",
                "storage_reconciliation_mismatch",
                json.dumps(report, ensure_ascii=False),
            )
            db.commit()
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Para desenvolvimento local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(IntegrityError)
async def sqlalchemy_integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Não é possível excluir ou modificar este registro pois ele possui dependências ou histórico vinculado (Proteção de Dados ativada)."},
    )

# Role definitions for dependency injection
AdminOnly = Depends(role_checker(["admin_global"]))
InstitutionRoles = Depends(role_checker(["admin_global", "admin_instituicao", "operador", "leitor", "auditor"]))

from app import api_admin, api_users, api_institutions, api_ged_upload, api_ecm, api_sites
from app import api_storage_config, api_ged_config, api_workflow, api_templates, api_search, api_erp_ingestion, api_digital_signature, api_academic, api_xsd, api_academic_dossier, api_validator, api_quarantine, api_integration, api_dashboard
from app import api_ecm_dictionary

app.include_router(api_admin.router)
app.include_router(api_users.router, prefix="/api")
app.include_router(api_institutions.router, prefix="/api")

app.include_router(api_ged_upload.router)
app.include_router(api_ecm.router)
app.include_router(api_ecm_dictionary.router)
app.include_router(api_sites.router, prefix="/api/ecm/sites")
app.include_router(api_storage_config.router)
app.include_router(api_ged_config.router, prefix="/api")
app.include_router(api_workflow.router, prefix="/api")
app.include_router(api_templates.router, prefix="/api")
app.include_router(api_search.router)
app.include_router(api_erp_ingestion.router)
app.include_router(api_digital_signature.router)
app.include_router(api_academic.router)
app.include_router(api_xsd.router, prefix="/api")
app.include_router(api_academic_dossier.router)
app.include_router(api_validator.router)
app.include_router(api_quarantine.router)
app.include_router(api_integration.router)
app.include_router(api_dashboard.router)
from app import api_document_operations
app.include_router(api_document_operations.router)

@app.post("/api/documents/validate", tags=["GED - Validações"])
def validate_academic_documents(payload: ValidationRequest):
    errors = validate_documents(payload)
    return {"valid": not errors, "errors": errors}

class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=2)
    cnpj: str = Field(..., min_length=11)
    legal_name: str = Field(..., min_length=2)


class Institution(InstitutionCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)


class StudentCreate(BaseModel):
    institution_id: str
    full_name: str = Field(..., min_length=2)
    birth_date: date
    cpf: str = Field(..., min_length=11, max_length=11)
    email: str = Field(..., min_length=3)


class Student(StudentCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)


class GuardianCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    cpf: str = Field(..., min_length=11, max_length=11)
    email: str = Field(..., min_length=3)
    relationship_type: str = Field(..., min_length=2)


class Guardian(GuardianCreate):
    id: str
    student_id: str
    model_config = ConfigDict(from_attributes=True)


class EnrollmentCreate(BaseModel):
    institution_id: str
    student_id: str
    course_name: str = Field(..., min_length=2)
    class_name: str = Field(..., min_length=1)
    year: int = Field(..., ge=1900)
    status: Literal["active", "inactive", "transferred", "graduated"] = "active"


class Enrollment(EnrollmentCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    institution_id: str
    student_id: str
    enrollment_id: str
    document_type: str = Field(..., min_length=2)
    title: str = Field(..., min_length=2)
    status: Literal["draft", "pending", "validated", "signed", "archived", "rejected"] = "pending"


class Document(DocumentCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)


class DocumentVersion(BaseModel):
    id: str
    document_id: str
    version_number: int
    file_name: str
    stored_path: str
    uploaded_at: datetime
    checksum: str

    model_config = ConfigDict(from_attributes=True)


class AuditEvent(BaseModel):
    id: str
    entity: str
    entity_id: str
    action: str
    details: str
    created_at: datetime
    hash_signature: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentRepresentation(BaseModel):
    document_id: str
    student_name: str
    course_name: str
    visual_type: str
    summary: str


class RetentionPolicy(BaseModel):
    document_id: str
    retention_years: int
    status: str
    expires_at: str | None = None


class XmlGenerationRequest(BaseModel):
    student_name: str
    course_name: str
    status: str
    document_type: str
    schema_version: str | None = None
    namespace: str | None = None
    environment: Literal["homologation", "production"] = "homologation"


class SchemaVersionCreate(BaseModel):
    code: str = Field(..., min_length=1)
    document_type: str = Field(..., min_length=2)
    namespace: str = Field(..., min_length=1)
    xsd_hash: str = Field(..., min_length=8)
    status: Literal["proposed", "approved", "retired"]
    valid_from: datetime
    valid_until: datetime | None = None
    environment: Literal["homologation", "production"]


class SchemaVersion(SchemaVersionCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class AdvancedSearchRequest(BaseModel):
    query: str = ""
    student_name: str | None = None
    document_type: str | None = None
    status: str | None = None
    institution_id: str | None = None
    limit: int = 100
    skip: int = 0


class RetentionCleanupRequest(BaseModel):
    dry_run: bool = True  # Se False, realmente arquiva os documentos


class DocumentLifecycleInfo(BaseModel):
    document_id: str
    status: str
    document_type: str
    created_at: datetime
    expiry_date: str
    days_remaining: int
    retention_years: int
    action_required: str  # "NONE", "WARN", "ARCHIVE"


# ==================== Endpoints ====================
@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/desktop/heartbeat")
def desktop_heartbeat():
    return {"status": "alive"}

from fastapi.security import OAuth2PasswordRequestForm
from app.auth import get_password_hash, create_access_token, verify_password

@app.post("/api/auth/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "institution_id": user.institution_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/institutions", response_model=Institution)
def create_institution(payload: InstitutionCreate, db: Session = Depends(get_db), user: models.User = AdminOnly):
    if db.query(models.Institution).filter(models.Institution.cnpj == payload.cnpj).first():
        raise HTTPException(status_code=409, detail="institution CNPJ already exists")

    institution = models.Institution(
        id=str(uuid4()),
        name=payload.name,
        cnpj=payload.cnpj,
        legal_name=payload.legal_name,
    )
    db.add(institution)
    add_audit(db, "institution", institution.id, "created", "Institution created")
    db.commit()
    db.refresh(institution)
    return institution

@app.get("/api/institutions", response_model=List[Institution])
def list_institutions(db: Session = Depends(get_db), user: models.User = AdminOnly):
    institutions = db.query(models.Institution).all()
    return institutions



@app.post("/api/students", response_model=Student)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), user: models.User = InstitutionRoles):
    check_institution_access(user, payload.institution_id)
    institution = db.query(models.Institution).filter(models.Institution.id == payload.institution_id).first()
    if institution is None:
        raise HTTPException(status_code=404, detail="institution not found")
    if db.query(models.Student).filter(models.Student.cpf == payload.cpf).first():
        raise HTTPException(status_code=409, detail="student CPF already exists")

    student = models.Student(
        id=str(uuid4()),
        institution_id=payload.institution_id,
        full_name=payload.full_name,
        birth_date=payload.birth_date.isoformat(),
        cpf=payload.cpf,
        email=payload.email,
    )
    db.add(student)
    add_audit(db, "student", student.id, "created", "Student created")
    db.commit()
    db.refresh(student)
    return student


@app.post("/api/students/{student_id}/guardians", response_model=Guardian)
def create_guardian(student_id: str, payload: GuardianCreate, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    if db.query(models.Guardian).filter(models.Guardian.cpf == payload.cpf).first():
        raise HTTPException(status_code=409, detail="guardian CPF already exists")

    guardian = models.Guardian(
        id=str(uuid4()),
        student_id=student_id,
        full_name=payload.full_name,
        cpf=payload.cpf,
        email=payload.email,
        relationship_type=payload.relationship_type,
    )
    db.add(guardian)
    add_audit(db, "guardian", guardian.id, "created", f"Guardian created for student {student_id}")
    db.commit()
    db.refresh(guardian)
    return guardian


@app.post("/api/enrollments", response_model=Enrollment)
def create_enrollment(payload: EnrollmentCreate, db: Session = Depends(get_db)):
    institution = db.query(models.Institution).filter(models.Institution.id == payload.institution_id).first()
    if institution is None:
        raise HTTPException(status_code=404, detail="institution not found")
    student = db.query(models.Student).filter(models.Student.id == payload.student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    if student.institution_id != institution.id:
        raise HTTPException(status_code=409, detail="student does not belong to institution")

    enrollment = models.Enrollment(
        id=str(uuid4()),
        institution_id=payload.institution_id,
        student_id=payload.student_id,
        course_name=payload.course_name,
        class_name=payload.class_name,
        year=payload.year,
        status=payload.status,
    )
    db.add(enrollment)
    add_audit(db, "enrollment", enrollment.id, "created", f"Enrollment created for student {payload.student_id}")
    db.commit()
    db.refresh(enrollment)
    return enrollment






# --- GED Lifecycle and State Machine Endpoints ---

# Include Upload Router
from app.xsd_validator import validate_xml_against_xsd
from pydantic import BaseModel

class XSDValidationRequest(BaseModel):
    document_id: str
    xsd_filename: str = "mock_diploma.xsd"

from app.rvdd_generator import generate_rvdd_html
from fastapi.responses import HTMLResponse


@app.get("/api/documents/{document_id}/retention")
def get_document_retention_policy(
    document_id: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        return {"detail": "document not found"}
        
    from app.auth import verify_document_ownership
    verify_document_ownership(current_user, document)

    retention_years = 5 if document.status in {"validated", "signed", "archived"} else 3
    retention = RetentionPolicy(
        document_id=document_id,
        retention_years=retention_years,
        status="active",
        expires_at=f"{datetime.now(UTC).year + retention_years}-12-31",
    )
    add_audit(db, "document", document_id, "retention_checked", "Retention policy verified", current_user.id)
    db.commit()
    return retention.model_dump()


@app.get("/api/audit")
def list_audit_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = InstitutionRoles):
    query = db.query(models.AuditEvent)
    if current_user.role != "admin_global":
        # Filtra os eventos de auditoria para apenas exibir aqueles causados por usuários da mesma instituição
        query = query.join(models.User, models.AuditEvent.user_id == models.User.id).filter(models.User.institution_id == current_user.institution_id)
        
    return query.order_by(models.AuditEvent.created_at.desc()).offset(skip).limit(limit).all()

from fastapi.responses import StreamingResponse
import io
import csv

@app.get("/api/audit/export/csv")
def export_audit_events_csv(db: Session = Depends(get_db), current_user: models.User = InstitutionRoles):
    query = db.query(models.AuditEvent)
    if current_user.role != "admin_global":
        query = query.join(models.User, models.AuditEvent.user_id == models.User.id).filter(models.User.institution_id == current_user.institution_id)
        
    events = query.order_by(models.AuditEvent.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "DataHora", "UsuarioID", "Entidade", "EntidadeID", "Acao", "Detalhes", "HashSignature"])
    
    for event in events:
        writer.writerow([
            event.id,
            event.created_at.isoformat(),
            event.user_id or "Sistema",
            event.entity,
            event.entity_id,
            event.action,
            event.details,
            event.hash_signature
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=auditoria.csv"}
    )


@app.get("/api/audit/verify")
def verify_audit_chain(db: Session = Depends(get_db), current_user: models.User = AdminOnly):
    """Verifica a integridade criptográfica da cadeia de eventos de auditoria."""
    from hashlib import sha256
    events = db.query(models.AuditEvent).order_by(models.AuditEvent.created_at.asc()).all()
    last_hash = "genesis"
    
    for event in events:
        payload = f"{event.id}:{event.entity}:{event.entity_id}:{event.action}:{event.details}:{event.user_id}:{last_hash}"
        expected_signature = sha256(payload.encode("utf-8")).hexdigest()
        
        if event.hash_signature != expected_signature:
            return {"valid": False, "tampered_event_id": event.id, "message": "Audit chain validation failed"}
            
        last_hash = expected_signature
        
    return {"valid": True, "message": "Audit chain is intact and valid", "events_checked": len(events)}


# ==================== Retention Management ====================
@app.get("/api/documents/retention/check")
def check_retention_violations(db: Session = Depends(get_db)):
    """Verificar quais documentos violam a polÃƒÂ­tica de retenÃƒÂ§ÃƒÂ£o."""
    violations = RetentionService.check_retention_compliance(db)
    return {
        "total_violations": len(violations),
        "violations": violations,
    }


@app.post("/api/documents/retention/cleanup")
def execute_retention_cleanup(payload: RetentionCleanupRequest, db: Session = Depends(get_db)):
    """Executar limpeza de documentos expirados."""
    result = RetentionService.execute_retention_cleanup(db, dry_run=payload.dry_run)
    
    if not payload.dry_run:
        add_audit(
            db,
            "system",
            "retention_cleanup",
            "retention_cleanup_executed",
            f"Arquivados {result['to_archive']} documentos expirados"
        )
        db.commit()
    
    return result


@app.get("/api/documents/retention/stats")
def get_retention_statistics(db: Session = Depends(get_db)):
    """Obter estatÃƒÂ­sticas sobre o ciclo de vida dos documentos."""
    stats = RetentionService.get_lifecycle_statistics(db)
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "statistics": stats,
    }


@app.get("/api/documents/{document_id}/lifecycle")
def get_document_lifecycle(
    document_id: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Obter informaÃƒÂ§ÃƒÂµes de ciclo de vida de um documento especÃƒÂ­fico."""
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        return {"detail": "document not found"}
        
    from app.auth import verify_document_ownership
    verify_document_ownership(current_user, document)
    
    retention_years = RetentionService.get_retention_period(document.document_type)
    expiry_date = RetentionService.calculate_expiry_date(document.created_at, document.document_type)
    days_remaining = (expiry_date - datetime.now(UTC).replace(tzinfo=None)).days
    
    action_required = "NONE"
    if document.status == "archived":
        action_required = "NONE"
    elif days_remaining < 0:
        action_required = "ARCHIVE"
    elif days_remaining < 30:
        action_required = "WARN"
    
    lifecycle = DocumentLifecycleInfo(
        document_id=document_id,
        status=document.status,
        document_type=document.document_type,
        created_at=document.created_at,
        expiry_date=expiry_date.isoformat(),
        days_remaining=days_remaining,
        retention_years=retention_years,
        action_required=action_required,
    )
    
    return lifecycle.model_dump()


# ==================== Helper Functions ====================
def add_audit(db: Session, entity: str, entity_id: str, action: str, details: str, user_id: str = None):
    last_event = db.query(models.AuditEvent).order_by(models.AuditEvent.created_at.desc()).first()
    last_hash = last_event.hash_signature if last_event and last_event.hash_signature else "genesis"
    
    event_id = str(uuid4())
    payload = f"{event_id}:{entity}:{entity_id}:{action}:{details}:{user_id}:{last_hash}"
    signature = sha256(payload.encode("utf-8")).hexdigest()

    audit_event = models.AuditEvent(
        id=event_id,
        document_id=entity_id if entity == "document" else None,
        entity=entity,
        entity_id=entity_id,
        action=action,
        details=details,
        user_id=user_id,
        hash_signature=signature,
    )
    db.add(audit_event)




