from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
from datetime import timedelta
from app.config import settings
from app.observability import configure_logging, observe_request, prometheus_metrics

from app.storage import delete_file, save_file, reconcile_document_storage
from app.upload_validation import read_validated_upload
from app.database import get_db
from app import models
from app.models_academic_catalog import (
    AcademicClass,
    AcademicCreditRecognition,
    AcademicCurriculum,
    AcademicCurriculumDiscipline,
    AcademicCurriculumEquivalence,
    AcademicCurriculumPrerequisite,
    AcademicDiscipline,
    AcademicOffering,
)
from app.search import search_service
from app.retention import RetentionService
from app import auth
from app.auth import get_current_active_user, role_checker, check_institution_access
from app.filewatch import run_filewatch_cycle
from app.privacy_utils import redact_text_for_log
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
from app import models_ged_config
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
    from app.models import User, Institution, InstitutionSettings
    from app.auth import get_password_hash
    db = SessionLocal()
    
    # Garante que existe pelo menos uma instituição padrão para o sistema
    inst = db.query(Institution).first()
    if not inst:
        import uuid
        inst_id = uuid.uuid4().hex
        inst = Institution(
            id=inst_id,
            name="Instituto de Ensino Superior EduGED",
            cnpj="00.000.000/0001-91",
            legal_name="EduGED Libre Instituição de Ensino Superior LTDA"
        )
        db.add(inst)
        db.flush()
        
        # Cria configurações padrão da instituição
        settings = InstitutionSettings(
            id=uuid.uuid4().hex,
            institution_id=inst.id
        )
        db.add(settings)
        db.commit()

    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        import uuid
        new_admin = User(
            id=uuid.uuid4().hex,
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role="admin_global",
            institution_id=inst.id
        )
        db.add(new_admin)
        db.commit()
    elif not admin.institution_id and inst:
        admin.institution_id = inst.id
        db.commit()

    db.close()
    
    start_worker()
    yield
    stop_worker()

app = FastAPI(title="EduGED Libre API", version="0.1.0", openapi_tags=tags_metadata, lifespan=lifespan)
configure_logging()
app.middleware("http")(observe_request)

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
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
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
AcademicStudentRoles = Depends(role_checker(["admin_global", "admin_instituicao", "operador", "academico"]))

from app import api_admin, api_users, api_institutions, api_ged_upload, api_ecm, api_sites, api_health
from app import api_storage_config, api_ged_config, api_workflow, api_templates, api_search, api_erp_ingestion, api_digital_signature, api_academic, api_xsd, api_academic_dossier, api_validator, api_quarantine, api_integration, api_dashboard, api_representation
from app import api_ecm_dictionary, api_public
from app.api_academic_catalog import router as academic_catalog_router
from app.modules.secretaria.routes import router as secretaria_router
from app.modules.sead.routes import router as sead_router
from app.modules.ead.routes import router as ead_router
from app.modules.professores.routes import router as professores_router
from app.modules.ged.routes import router as ged_router
from app.modules.financeiro.routes import router as financeiro_router
from app.modules.coordenacao.routes import router as coordenacao_router
from app.modules.aluno.routes import router as aluno_router
from app.modules.admin.routes import router as admin_router

app.include_router(api_admin.router)
app.include_router(api_users.router, prefix="/api")
app.include_router(api_institutions.router)
app.include_router(admin_router)
app.include_router(academic_catalog_router)
app.include_router(secretaria_router)
app.include_router(sead_router)
app.include_router(ead_router)
app.include_router(professores_router)
app.include_router(ged_router)
app.include_router(financeiro_router)
app.include_router(coordenacao_router)
app.include_router(aluno_router)

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
app.include_router(api_representation.router)
from app import api_document_operations
app.include_router(api_document_operations.router)
app.include_router(api_public.router)
app.include_router(api_health.router)

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
    campus_id: str | None = None
    full_name: str = Field(..., min_length=2)
    social_name: str | None = Field(default=None, max_length=160)
    sex: str | None = Field(default=None, max_length=40)
    nationality: str | None = Field(default=None, max_length=100)
    birthplace_municipality_code: str | None = Field(default=None, max_length=10)
    birthplace_municipality_name: str | None = Field(default=None, max_length=120)
    birthplace_state: str | None = Field(default=None, min_length=2, max_length=2)
    birth_date: date
    rg_number: str | None = Field(default=None, max_length=30)
    rg_issuing_authority: str | None = Field(default=None, max_length=40)
    rg_state: str | None = Field(default=None, min_length=2, max_length=2)
    cpf: str = Field(..., min_length=11, max_length=11)
    email: str = Field(..., min_length=3)
    phone: str | None = Field(default=None, max_length=32)
    address_street: str | None = Field(default=None, max_length=160)
    address_number: str | None = Field(default=None, max_length=20)
    address_complement: str | None = Field(default=None, max_length=120)
    address_neighborhood: str | None = Field(default=None, max_length=120)
    address_city: str | None = Field(default=None, max_length=120)
    address_state: str | None = Field(default=None, min_length=2, max_length=2)
    address_postal_code: str | None = Field(default=None, max_length=12)


class Student(StudentCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)


class GuardianCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    cpf: str = Field(..., min_length=11, max_length=11)
    email: str = Field(..., min_length=3)
    relationship_type: str = Field(..., min_length=2)
    phone: str | None = Field(default=None, max_length=32)
    address_street: str | None = Field(default=None, max_length=160)
    address_number: str | None = Field(default=None, max_length=20)
    address_complement: str | None = Field(default=None, max_length=120)
    address_neighborhood: str | None = Field(default=None, max_length=120)
    address_city: str | None = Field(default=None, max_length=120)
    address_state: str | None = Field(default=None, min_length=2, max_length=2)
    address_postal_code: str | None = Field(default=None, max_length=12)


class Guardian(GuardianCreate):
    id: str
    student_id: str
    model_config = ConfigDict(from_attributes=True)


class StudentRegistrationCreate(BaseModel):
    student: StudentCreate
    guardian: GuardianCreate | None = None


class EnrollmentCreate(BaseModel):
    institution_id: str
    student_id: str
    academic_class_id: str | None = None
    course_name: str | None = Field(default=None, min_length=2)
    class_name: str | None = Field(default=None, min_length=1)
    year: int | None = Field(default=None, ge=1900)
    status: Literal["pending", "active", "inactive", "transferred", "graduated"] = "active"


class Enrollment(EnrollmentCreate):
    id: str
    status: str
    result: Literal["pending", "passed", "failed"] = "pending"
    model_config = ConfigDict(from_attributes=True)


class EnrollmentResultUpdate(BaseModel):
    result: Literal["passed", "failed"]


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


@app.get("/metrics", include_in_schema=False)
def metrics():
    return PlainTextResponse(prometheus_metrics(), media_type="text/plain; version=0.0.4")

@app.post("/api/desktop/heartbeat")
def desktop_heartbeat():
    return {"status": "alive"}

from fastapi.security import OAuth2PasswordRequestForm
from app.auth import get_password_hash, create_access_token, verify_password

@app.get("/api/modules")
def get_available_modules():
    return [
        {"code": "admin", "label": "Administração", "description": "Painel administrativo para todos os módulos e configurações do sistema."},
        {"code": "sead", "label": "SEAD", "description": "Secretaria Acadêmica Digital: matrículas, processos e vida acadêmica."},
        {"code": "ead", "label": "EAD", "description": "Educação a Distância: polos, tutores, aulas e acompanhamento virtual."},
        {"code": "secretaria", "label": "Secretaria", "description": "Atendimento acadêmico e matrículas."},
        {"code": "professores", "label": "Professores", "description": "Acompanhamento de turmas, notas e aulas."},
        {"code": "ged", "label": "GED", "description": "Documentos, versões e auditoria documental."},
        {"code": "financeiro", "label": "Financeiro", "description": "Financeiro, cobranças e manutenção acadêmica."},
        {"code": "coordenacao", "label": "Coordenação", "description": "Validação curricular e governança acadêmica."},
        {"code": "aluno", "label": "Aluno", "description": "Portal do estudante e acompanhamento acadêmico."},
        {"code": "geral", "label": "Geral", "description": "Acesso geral ao sistema sem módulo específico."},
    ]


@app.post("/api/auth/token")
def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...),
    module: str = Form("geral"),
    db: Session = Depends(get_db),
):
    normalized_module = (module or "geral").strip().lower()
    if normalized_module not in auth.AVAILABLE_MODULES:
        raise HTTPException(status_code=400, detail=f"Módulo inválido: {module}")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth.has_module_access(user.role, normalized_module):
        raise HTTPException(status_code=403, detail=f"Usuário não tem acesso ao módulo '{normalized_module}'")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "institution_id": user.institution_id,
            "campus_id": user.campus_id,
            "module": normalized_module,
        },
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer", "module": normalized_module}  # nosec B105 - OAuth bearer scheme is not a secret


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


def _resolve_student_campus(
    db: Session,
    user: models.User,
    institution_id: str,
    requested_campus_id: str | None,
) -> str | None:
    campus_id = requested_campus_id or user.campus_id
    if user.campus_id and campus_id != user.campus_id:
        raise HTTPException(status_code=403, detail="Cross-campus access forbidden")
    if campus_id and not db.query(models.Campus).filter(
        models.Campus.id == campus_id,
        models.Campus.institution_id == institution_id,
    ).first():
        raise HTTPException(status_code=404, detail="Campus not found in institution")
    return campus_id



@app.post("/api/students", response_model=Student)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), user: models.User = AcademicStudentRoles):
    check_institution_access(user, payload.institution_id)
    institution = db.query(models.Institution).filter(models.Institution.id == payload.institution_id).first()
    if institution is None:
        raise HTTPException(status_code=404, detail="institution not found")
    campus_id = _resolve_student_campus(db, user, payload.institution_id, payload.campus_id)
    if db.query(models.Student).filter(models.Student.cpf == payload.cpf).first():
        raise HTTPException(status_code=409, detail="student CPF already exists")

    student = models.Student(
        id=str(uuid4()),
        institution_id=payload.institution_id,
        full_name=payload.full_name,
        social_name=payload.social_name,
        sex=payload.sex,
        nationality=payload.nationality,
        birthplace_municipality_code=payload.birthplace_municipality_code,
        birthplace_municipality_name=payload.birthplace_municipality_name,
        birthplace_state=payload.birthplace_state,
        birth_date=payload.birth_date.isoformat(),
        rg_number=payload.rg_number,
        rg_issuing_authority=payload.rg_issuing_authority,
        rg_state=payload.rg_state,
        cpf=payload.cpf,
        email=payload.email,
        phone=payload.phone,
        address_street=payload.address_street,
        address_number=payload.address_number,
        address_complement=payload.address_complement,
        address_neighborhood=payload.address_neighborhood,
        address_city=payload.address_city,
        address_state=payload.address_state,
        address_postal_code=payload.address_postal_code,
        campus_id=campus_id,
    )
    db.add(student)
    add_audit(db, "student", student.id, "created", "Student created", user.id)
    db.commit()
    db.refresh(student)
    return student


@app.post("/api/students/{student_id}/guardians", response_model=Guardian)
def create_guardian(
    student_id: str,
    payload: GuardianCreate,
    db: Session = Depends(get_db),
    user: models.User = AcademicStudentRoles,
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    check_institution_access(user, student.institution_id)
    if user.campus_id and student.campus_id != user.campus_id:
        raise HTTPException(status_code=403, detail="Cross-campus access forbidden")
    if db.query(models.Guardian).filter(models.Guardian.cpf == payload.cpf).first():
        raise HTTPException(status_code=409, detail="guardian CPF already exists")

    guardian = models.Guardian(
        id=str(uuid4()),
        student_id=student_id,
        full_name=payload.full_name,
        cpf=payload.cpf,
        email=payload.email,
        phone=payload.phone,
        address_street=payload.address_street,
        address_number=payload.address_number,
        address_complement=payload.address_complement,
        address_neighborhood=payload.address_neighborhood,
        address_city=payload.address_city,
        address_state=payload.address_state,
        address_postal_code=payload.address_postal_code,
        relationship_type=payload.relationship_type,
    )
    db.add(guardian)
    add_audit(
        db,
        "guardian",
        guardian.id,
        "created",
        f"Guardian created for student {student_id}",
        user.id,
    )
    db.commit()
    db.refresh(guardian)
    return guardian


@app.post("/api/students/registration")
def register_student(
    payload: StudentRegistrationCreate,
    db: Session = Depends(get_db),
    user: models.User = AcademicStudentRoles,
):
    student_data = payload.student
    check_institution_access(user, student_data.institution_id)
    institution = db.query(models.Institution).filter(
        models.Institution.id == student_data.institution_id
    ).first()
    if institution is None:
        raise HTTPException(status_code=404, detail="institution not found")
    campus_id = _resolve_student_campus(
        db, user, student_data.institution_id, student_data.campus_id
    )
    if db.query(models.Student).filter(models.Student.cpf == student_data.cpf).first():
        raise HTTPException(status_code=409, detail="student CPF already exists")

    guardian_data = payload.guardian
    if guardian_data and db.query(models.Guardian).filter(
        models.Guardian.cpf == guardian_data.cpf
    ).first():
        raise HTTPException(status_code=409, detail="guardian CPF already exists")

    student = models.Student(
        id=str(uuid4()),
        institution_id=student_data.institution_id,
        full_name=student_data.full_name,
        birth_date=student_data.birth_date.isoformat(),
        cpf=student_data.cpf,
        email=student_data.email,
        phone=student_data.phone,
        address_street=student_data.address_street,
        address_number=student_data.address_number,
        address_complement=student_data.address_complement,
        address_neighborhood=student_data.address_neighborhood,
        address_city=student_data.address_city,
        address_state=student_data.address_state,
        address_postal_code=student_data.address_postal_code,
        campus_id=campus_id,
    )
    db.add(student)
    db.flush()
    add_audit(db, "student", student.id, "created", "Student registered", user.id)

    guardian = None
    if guardian_data:
        guardian = models.Guardian(
            id=str(uuid4()),
            student_id=student.id,
            full_name=guardian_data.full_name,
            cpf=guardian_data.cpf,
            email=guardian_data.email,
            phone=guardian_data.phone,
            address_street=guardian_data.address_street,
            address_number=guardian_data.address_number,
            address_complement=guardian_data.address_complement,
            address_neighborhood=guardian_data.address_neighborhood,
            address_city=guardian_data.address_city,
            address_state=guardian_data.address_state,
            address_postal_code=guardian_data.address_postal_code,
            relationship_type=guardian_data.relationship_type,
        )
        db.add(guardian)
        db.flush()
        add_audit(
            db,
            "guardian",
            guardian.id,
            "created",
            f"Guardian registered for student {student.id}",
            user.id,
        )

    db.commit()
    db.refresh(student)
    if guardian:
        db.refresh(guardian)
    return {
        "student": Student.model_validate(student).model_dump(mode="json"),
        "guardian": Guardian.model_validate(guardian).model_dump(mode="json") if guardian else None,
    }


@app.post("/api/enrollments", response_model=Enrollment)
def create_enrollment(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    user: models.User = AcademicStudentRoles,
):
    check_institution_access(user, payload.institution_id)
    institution = db.query(models.Institution).filter(models.Institution.id == payload.institution_id).first()
    if institution is None:
        raise HTTPException(status_code=404, detail="institution not found")
    student = db.query(models.Student).filter(models.Student.id == payload.student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    if student.institution_id != institution.id:
        raise HTTPException(status_code=409, detail="student does not belong to institution")
    if user.campus_id and student.campus_id != user.campus_id:
        raise HTTPException(status_code=403, detail="Cross-campus access forbidden")

    academic_class = None
    course_name = payload.course_name
    class_name = payload.class_name
    year = payload.year
    campus_id = student.campus_id
    academic_link_snapshot = None
    if payload.academic_class_id:
        academic_class = (
            db.query(AcademicClass)
            .filter(
                AcademicClass.id == payload.academic_class_id,
                AcademicClass.institution_id == institution.id,
            )
            .with_for_update()
            .first()
        )
        if academic_class is None:
            raise HTTPException(status_code=404, detail="Academic class not found")
        offering = academic_class.offering
        if student.campus_id != offering.campus_id:
            raise HTTPException(status_code=409, detail="Student and academic class campuses do not match")
        if academic_class.status != "ativa" or offering.status != "aberta":
            raise HTTPException(status_code=409, detail="Academic class is not open for enrollment")
        if (
            offering.course.status != "ativo"
            or offering.discipline.status != "ativo"
            or offering.term.status == "encerrado"
        ):
            raise HTTPException(status_code=409, detail="Course, discipline, or academic term is not available")
        if offering.term.ends_on < date.today():
            raise HTTPException(status_code=409, detail="Academic term has ended")
        curriculum_discipline = (
            db.query(AcademicCurriculumDiscipline)
            .join(
                AcademicCurriculum,
                AcademicCurriculum.id == AcademicCurriculumDiscipline.curriculum_id,
            )
            .filter(
                AcademicCurriculum.institution_id == institution.id,
                AcademicCurriculum.course_id == offering.course_id,
                AcademicCurriculum.status == "ativa",
                AcademicCurriculum.effective_from <= offering.term.starts_on,
                AcademicCurriculumDiscipline.discipline_id == offering.discipline_id,
            )
            .order_by(AcademicCurriculum.effective_from.desc())
            .first()
        )
        if curriculum_discipline is None:
            raise HTTPException(
                status_code=409,
                detail="Discipline is not included in an effective active curriculum for this course",
            )
        curriculum = curriculum_discipline.curriculum
        academic_link_snapshot = {
            "course_id": offering.course_id,
            "course_name": offering.course.name,
            "curriculum_id": curriculum.id,
            "curriculum_version": curriculum.version,
            "discipline_id": offering.discipline_id,
            "discipline_name": offering.discipline.name,
            "class_id": academic_class.id,
            "class_code": academic_class.code,
            "term_id": offering.term_id,
            "term_code": offering.term.code,
            "term_name": offering.term.name,
            "term_starts_on": offering.term.starts_on.isoformat(),
            "term_ends_on": offering.term.ends_on.isoformat(),
            "campus_id": offering.campus_id,
        }
        prerequisite_links = (
            db.query(AcademicCurriculumPrerequisite)
            .filter(
                AcademicCurriculumPrerequisite.curriculum_discipline_id
                == curriculum_discipline.id
            )
            .all()
        )
        prerequisite_link_ids = {
            prerequisite.prerequisite_curriculum_discipline_id
            for prerequisite in prerequisite_links
        }
        if prerequisite_link_ids:
            prerequisite_links = db.query(AcademicCurriculumDiscipline).filter(
                AcademicCurriculumDiscipline.id.in_(prerequisite_link_ids)
            ).all()
            prerequisite_discipline_ids = {
                link.discipline_id for link in prerequisite_links
            }
            equivalence_rows = db.query(
                AcademicCurriculumEquivalence.curriculum_discipline_id,
                AcademicCurriculumEquivalence.equivalent_discipline_id,
            ).filter(
                AcademicCurriculumEquivalence.curriculum_discipline_id.in_(
                    prerequisite_link_ids
                )
            ).all()
            equivalents_by_prerequisite = {}
            for curriculum_discipline_id, equivalent_id in equivalence_rows:
                equivalents_by_prerequisite.setdefault(curriculum_discipline_id, set()).add(
                    equivalent_id
                )
            equivalent_discipline_ids = {
                equivalent_id
                for equivalent_ids in equivalents_by_prerequisite.values()
                for equivalent_id in equivalent_ids
            }
            passed_prerequisites = {
                discipline_id
                for (discipline_id,) in (
                    db.query(AcademicOffering.discipline_id)
                    .join(AcademicClass, AcademicClass.offering_id == AcademicOffering.id)
                    .join(
                        models.Enrollment,
                        models.Enrollment.academic_class_id == AcademicClass.id,
                    )
                    .filter(
                        models.Enrollment.institution_id == institution.id,
                        models.Enrollment.student_id == student.id,
                        models.Enrollment.status == "completed",
                        models.Enrollment.result == "passed",
                        AcademicOffering.institution_id == institution.id,
                        AcademicClass.institution_id == institution.id,
                        AcademicOffering.course_id == offering.course_id,
                        AcademicOffering.discipline_id.in_(prerequisite_discipline_ids),
                    )
                    .distinct()
                    .all()
                )
            }
            passed_equivalences = {
                discipline_id
                for (discipline_id,) in (
                    db.query(AcademicOffering.discipline_id)
                    .join(AcademicClass, AcademicClass.offering_id == AcademicOffering.id)
                    .join(
                        models.Enrollment,
                        models.Enrollment.academic_class_id == AcademicClass.id,
                    )
                    .filter(
                        models.Enrollment.institution_id == institution.id,
                        models.Enrollment.student_id == student.id,
                        models.Enrollment.status == "completed",
                        models.Enrollment.result == "passed",
                        AcademicOffering.institution_id == institution.id,
                        AcademicClass.institution_id == institution.id,
                        AcademicOffering.discipline_id.in_(equivalent_discipline_ids),
                    )
                    .distinct()
                    .all()
                )
            }
            approved_credit_link_ids = {
                link_id
                for (link_id,) in db.query(
                    AcademicCreditRecognition.curriculum_discipline_id
                ).filter(
                    AcademicCreditRecognition.institution_id == institution.id,
                    AcademicCreditRecognition.student_id == student.id,
                    AcademicCreditRecognition.course_id == offering.course_id,
                    AcademicCreditRecognition.curriculum_discipline_id.in_(
                        prerequisite_link_ids
                    ),
                    AcademicCreditRecognition.status == "approved",
                ).all()
            }
            satisfied_prerequisites = {
                prerequisite.discipline_id
                for prerequisite in prerequisite_links
                if prerequisite.id in approved_credit_link_ids
                or prerequisite.discipline_id in passed_prerequisites
                or bool(
                    equivalents_by_prerequisite.get(prerequisite.id, set())
                    & passed_equivalences
                )
            }
            missing_prerequisites = prerequisite_discipline_ids - satisfied_prerequisites
            if missing_prerequisites:
                missing_names = [
                    name
                    for (name,) in db.query(AcademicDiscipline.name)
                    .filter(AcademicDiscipline.id.in_(missing_prerequisites))
                    .order_by(AcademicDiscipline.name)
                    .all()
                ]
                raise HTTPException(
                    status_code=409,
                    detail="Unmet academic prerequisites: " + ", ".join(missing_names),
                )
        if (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.student_id == student.id,
                models.Enrollment.academic_class_id == academic_class.id,
                models.Enrollment.status.in_(("active", "pending")),
            )
            .first()
        ):
            raise HTTPException(status_code=409, detail="Student is already enrolled in this class")
        active_enrollments = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.academic_class_id == academic_class.id,
                models.Enrollment.status.in_(("active", "pending")),
            )
            .count()
        )
        if active_enrollments >= academic_class.capacity:
            raise HTTPException(status_code=409, detail="Academic class has no available seats")
        course_name = offering.course.name
        class_name = academic_class.code
        year = offering.term.starts_on.year
        campus_id = offering.campus_id
    elif course_name is None or class_name is None or year is None:
        raise HTTPException(
            status_code=422,
            detail="Provide an academic class or course, class, and year",
        )

    enrollment = models.Enrollment(
        id=str(uuid4()),
        institution_id=payload.institution_id,
        student_id=payload.student_id,
        academic_class_id=academic_class.id if academic_class else None,
        course_name=course_name,
        class_name=class_name,
        year=year,
        status=payload.status,
        campus_id=campus_id,
    )
    db.add(enrollment)
    add_audit(
        db,
        "enrollment",
        enrollment.id,
        "created",
        json.dumps(
            {
                "academic_link": academic_link_snapshot or {
                    "course_name": course_name,
                    "class_name": class_name,
                    "year": year,
                    "campus_id": campus_id,
                },
                "status": enrollment.status,
                "result": enrollment.result,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        user.id,
    )
    db.commit()
    db.refresh(enrollment)
    return enrollment


@app.patch("/api/enrollments/{enrollment_id}/result", response_model=Enrollment)
def update_enrollment_result(
    enrollment_id: str,
    payload: EnrollmentResultUpdate,
    db: Session = Depends(get_db),
    user: models.User = AcademicStudentRoles,
):
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.id == enrollment_id
    ).first()
    if enrollment is None:
        raise HTTPException(status_code=404, detail="enrollment not found")
    check_institution_access(user, enrollment.institution_id)
    if user.campus_id and enrollment.campus_id != user.campus_id:
        raise HTTPException(status_code=403, detail="Cross-campus access forbidden")
    if enrollment.academic_class_id is None:
        raise HTTPException(
            status_code=409,
            detail="An academic class must be linked before recording a discipline result",
        )
    if enrollment.status != "active":
        raise HTTPException(status_code=409, detail="Enrollment cannot receive an academic result")
    academic_class = db.query(AcademicClass).filter(
        AcademicClass.id == enrollment.academic_class_id
    ).first()
    if academic_class is None:
        raise HTTPException(status_code=404, detail="Academic class not found")
    if academic_class.offering.term.ends_on >= date.today():
        raise HTTPException(
            status_code=409,
            detail="Academic result can only be recorded after the term has ended",
        )
    previous_state = {"status": enrollment.status, "result": enrollment.result}
    enrollment.result = payload.result
    enrollment.status = "completed"
    add_audit(
        db,
        "enrollment",
        enrollment.id,
        "result_recorded",
        json.dumps(
            {
                "before": previous_state,
                "after": {"status": enrollment.status, "result": enrollment.result},
            },
            sort_keys=True,
        ),
        user.id,
    )
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
            redact_text_for_log(event.details),
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
def check_retention_violations(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    """Verificar quais documentos violam a política de retenção."""
    institution_id = current_user.institution_id if current_user.role != "admin_global" else None
    violations = RetentionService.check_retention_compliance(db, institution_id=institution_id)
    return {
        "total_violations": len(violations),
        "violations": violations,
    }


@app.post("/api/documents/retention/cleanup")
def execute_retention_cleanup(payload: RetentionCleanupRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    """Executar limpeza de documentos expirados."""
    institution_id = current_user.institution_id if current_user.role != "admin_global" else None
    result = RetentionService.execute_retention_cleanup(db, dry_run=payload.dry_run, institution_id=institution_id)
    
    if not payload.dry_run:
        add_audit(
            db,
            "system",
            "retention_cleanup",
            "retention_cleanup_executed",
            f"Arquivados {result['to_archive']} documentos expirados",
            current_user.id
        )
        db.commit()
    
    return result


@app.get("/api/documents/retention/stats")
def get_retention_statistics(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    """Obter estatísticas sobre o ciclo de vida dos documentos."""
    institution_id = current_user.institution_id if current_user.role != "admin_global" else None
    stats = RetentionService.get_lifecycle_statistics(db, institution_id=institution_id)
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
    document = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
    if document is None:
        return {"detail": "document not found"}
        
    from app.auth import verify_document_ownership
    verify_document_ownership(current_user, document)
    
    document_type = db.query(models_ged_config.DocumentType).filter(
        models_ged_config.DocumentType.id == document.category_id
    ).first()
    document_type_name = document_type.name if document_type else "tipo_unknown"
    retention_years = (
        int(document_type.retention_years)
        if document_type is not None and document_type.retention_years is not None
        else 5
    )
    expiry_date = document.created_at + timedelta(days=365 * retention_years)
    days_remaining = (expiry_date - datetime.now(UTC).replace(tzinfo=None)).days
    
    action_required = "NONE"
    if document.status == GEDDocumentStatus.ARQUIVADO:
        action_required = "NONE"
    elif days_remaining < 0:
        action_required = "ARCHIVE"
    elif days_remaining < 30:
        action_required = "WARN"
    
    lifecycle = DocumentLifecycleInfo(
        document_id=document_id,
        status=document.status.value,
        document_type=document_type_name,
        created_at=document.created_at,
        expiry_date=expiry_date.isoformat(),
        days_remaining=days_remaining,
        retention_years=retention_years,
        action_required=action_required,
    )
    
    return lifecycle.model_dump()


# ==================== Helper Functions ====================
def add_audit(db: Session, entity: str, entity_id: str, action: str, details: str, user_id: str = None):
    redacted_details = redact_text_for_log(details)
    last_event = db.query(models.AuditEvent).order_by(models.AuditEvent.created_at.desc()).first()
    last_hash = last_event.hash_signature if last_event and last_event.hash_signature else "genesis"

    event_id = str(uuid4())
    payload = f"{event_id}:{entity}:{entity_id}:{action}:{redacted_details}:{user_id}:{last_hash}"
    signature = sha256(payload.encode("utf-8")).hexdigest()

    audit_event = models.AuditEvent(
        id=event_id,
        document_id=entity_id if entity == "document" else None,
        entity=entity,
        entity_id=entity_id,
        action=action,
        details=redacted_details,
        user_id=user_id,
        hash_signature=signature,
    )
    db.add(audit_event)
