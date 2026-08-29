from datetime import date, datetime
from typing import Literal
from xml.sax.saxutils import escape, quoteattr

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.storage import save_file
from app.database import engine, get_db
from app import models
from app.search import search_service
from app.retention import RetentionService

# Create all tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="LibreGED API", version="0.1.0")


# ==================== Pydantic Models ====================
class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=2)
    cnpj: str = Field(..., min_length=11)
    legal_name: str = Field(..., min_length=2)


class Institution(InstitutionCreate):
    id: str

    class Config:
        from_attributes = True


class StudentCreate(BaseModel):
    institution_id: str
    full_name: str = Field(..., min_length=2)
    birth_date: date
    cpf: str = Field(..., min_length=11, max_length=11)
    email: str = Field(..., min_length=3)


class Student(StudentCreate):
    id: str

    class Config:
        from_attributes = True


class GuardianCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    cpf: str = Field(..., min_length=11, max_length=11)
    email: str = Field(..., min_length=3)
    relationship_type: str = Field(..., min_length=2)


class Guardian(GuardianCreate):
    id: str
    student_id: str

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    institution_id: str
    student_id: str
    course_name: str = Field(..., min_length=2)
    class_name: str = Field(..., min_length=1)
    year: int = Field(..., ge=1900)
    status: Literal["active", "inactive", "transferred", "graduated"] = "active"


class Enrollment(EnrollmentCreate):
    id: str

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    institution_id: str
    student_id: str
    enrollment_id: str
    document_type: str = Field(..., min_length=2)
    title: str = Field(..., min_length=2)
    status: Literal["draft", "pending", "validated", "signed", "archived", "rejected"] = "pending"


class Document(DocumentCreate):
    id: str

    class Config:
        from_attributes = True


class DocumentVersion(BaseModel):
    id: str
    document_id: str
    version_number: int
    file_name: str
    stored_path: str
    uploaded_at: datetime
    checksum: str

    class Config:
        from_attributes = True


class AuditEvent(BaseModel):
    id: str
    entity: str
    entity_id: str
    action: str
    details: str
    created_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class AdvancedSearchRequest(BaseModel):
    query: str = ""
    student_name: str | None = None
    document_type: str | None = None
    status: str | None = None
    institution_id: str | None = None
    limit: int = 100


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


@app.post("/api/institutions", response_model=Institution)
def create_institution(payload: InstitutionCreate, db: Session = Depends(get_db)):
    institution = models.Institution(
        id=str(len(db.query(models.Institution).all()) + 1),
        name=payload.name,
        cnpj=payload.cnpj,
        legal_name=payload.legal_name,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    add_audit(db, "institution", institution.id, "created", "Institution created")
    return institution


@app.post("/api/students", response_model=Student)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    student = models.Student(
        id=str(len(db.query(models.Student).all()) + 1),
        institution_id=payload.institution_id,
        full_name=payload.full_name,
        birth_date=payload.birth_date.isoformat(),
        cpf=payload.cpf,
        email=payload.email,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    add_audit(db, "student", student.id, "created", "Student created")
    return student


@app.post("/api/students/{student_id}/guardians", response_model=Guardian)
def create_guardian(student_id: str, payload: GuardianCreate, db: Session = Depends(get_db)):
    guardian = models.Guardian(
        id=str(len(db.query(models.Guardian).all()) + 1),
        student_id=student_id,
        full_name=payload.full_name,
        cpf=payload.cpf,
        email=payload.email,
        relationship_type=payload.relationship_type,
    )
    db.add(guardian)
    db.commit()
    db.refresh(guardian)
    add_audit(db, "guardian", guardian.id, "created", f"Guardian created for student {student_id}")
    return guardian


@app.post("/api/enrollments", response_model=Enrollment)
def create_enrollment(payload: EnrollmentCreate, db: Session = Depends(get_db)):
    enrollment = models.Enrollment(
        id=str(len(db.query(models.Enrollment).all()) + 1),
        institution_id=payload.institution_id,
        student_id=payload.student_id,
        course_name=payload.course_name,
        class_name=payload.class_name,
        year=payload.year,
        status=payload.status,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    add_audit(db, "enrollment", enrollment.id, "created", f"Enrollment created for student {payload.student_id}")
    return enrollment


@app.post("/api/documents", response_model=Document)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    document = models.Document(
        id=str(len(db.query(models.Document).all()) + 1),
        institution_id=payload.institution_id,
        student_id=payload.student_id,
        enrollment_id=payload.enrollment_id,
        document_type=payload.document_type,
        title=payload.title,
        status=payload.status,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Indexar para busca avançada
    student = db.query(models.Student).filter(models.Student.id == payload.student_id).first()
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == payload.enrollment_id).first()
    search_service.index_document(
        doc_id=document.id,
        document_data={
            "id": document.id,
            "student_name": student.full_name if student else "",
            "student_cpf": student.cpf if student else "",
            "course_name": enrollment.course_name if enrollment else "",
            "document_type": document.document_type,
            "title": document.title,
            "status": document.status,
            "institution_id": document.institution_id,
            "created_at": document.created_at.isoformat() if document.created_at else "",
        },
    )
    
    add_audit(db, "document", document.id, "created", f"Document created: {payload.title}")
    return document


@app.post("/api/documents/{document_id}/upload")
def upload_document(document_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        return {"detail": "document not found"}

    stored_path = save_file(f"{document_id}-{file.filename}", file.file.read())
    checksum = str(hash(stored_path))
    version_count = len(db.query(models.DocumentVersion).filter(models.DocumentVersion.document_id == document_id).all())
    
    version = models.DocumentVersion(
        id=str(len(db.query(models.DocumentVersion).all()) + 1),
        document_id=document_id,
        version_number=version_count + 1,
        file_name=file.filename,
        stored_path=stored_path,
        checksum=checksum,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    add_audit(db, "document", document_id, "uploaded", f"File uploaded: {file.filename}")
    return {"document_id": document_id, "version": DocumentVersion.from_orm(version).model_dump()}


@app.post("/api/documents/{document_id}/xml")
def generate_document_xml(document_id: str, payload: XmlGenerationRequest, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    def block(reason: str):
        document.status = "rejected"
        add_audit(db, "document", document_id, "xml_generation_blocked", reason)
        raise HTTPException(status_code=409, detail=reason)

    if not payload.schema_version:
        block("schema version is required; version inference is forbidden")
    if not payload.namespace:
        block("schema namespace is required")
    if payload.document_type != document.document_type:
        block("requested document type does not match the document")

    schema = db.query(models.SchemaVersion).filter(models.SchemaVersion.code == payload.schema_version).first()
    if schema is None:
        block("schema version is not registered")
    if schema.status != "approved":
        block("schema version is not approved for use")
    if schema.document_type != document.document_type:
        block("schema version is incompatible with the document type")
    if schema.namespace != payload.namespace:
        block("schema namespace does not match the registered schema")
    if schema.environment != payload.environment:
        block("schema version is not approved for this environment")

    now = datetime.now(schema.valid_from.tzinfo) if schema.valid_from.tzinfo else datetime.utcnow()
    if schema.valid_from > now or (schema.valid_until is not None and schema.valid_until < now):
        block("schema version is outside its validity period")

    xml = (
        f"<documento xmlns={quoteattr(payload.namespace)} schemaVersion={quoteattr(schema.code)} xsdHash={quoteattr(schema.xsd_hash)}>"
        f"<tipo>{escape(payload.document_type)}</tipo>"
        f"<titulo>{escape(document.title)}</titulo>"
        f"<aluno>{escape(payload.student_name)}</aluno>"
        f"<curso>{escape(payload.course_name)}</curso>"
        f"<status>{escape(payload.status)}</status>"
        "</documento>"
    )
    add_audit(db, "document", document_id, "xml_generated", f"XML generated with schema {schema.code}")
    return {"document_id": document_id, "schema_version": schema.code, "xml": xml}


@app.post("/api/schema-versions", response_model=SchemaVersion, status_code=201)
def create_schema_version(payload: SchemaVersionCreate, db: Session = Depends(get_db)):
    if payload.valid_until is not None and payload.valid_until <= payload.valid_from:
        raise HTTPException(status_code=422, detail="valid_until must be after valid_from")
    if db.query(models.SchemaVersion).filter(models.SchemaVersion.code == payload.code).first():
        raise HTTPException(status_code=409, detail="schema version code already exists")
    schema = models.SchemaVersion(
        id=str(len(db.query(models.SchemaVersion).all()) + 1),
        **payload.model_dump(),
    )
    db.add(schema)
    db.commit()
    db.refresh(schema)
    add_audit(db, "schema_version", schema.id, "created", f"Schema version registered: {schema.code}")
    return schema


@app.get("/api/documents")
def list_documents(student_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Document)
    if student_id:
        query = query.filter(models.Document.student_id == student_id)
    return query.all()


@app.post("/api/documents/advanced-search")
def advanced_search_documents(payload: AdvancedSearchRequest, db: Session = Depends(get_db)):
    """Buscar documentos com filtros avançados usando Elasticsearch (ou fallback em memória)."""
    results = search_service.search(
        query=payload.query,
        student_name=payload.student_name,
        document_type=payload.document_type,
        status=payload.status,
        institution_id=payload.institution_id,
        limit=payload.limit,
    )
    # Retornar os documentos indexados (com metadados de busca)
    return results


@app.get("/api/documents/search")
def search_documents(
    student_id: str | None = None,
    document_type: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Document)
    if student_id:
        query = query.filter(models.Document.student_id == student_id)
    if document_type:
        query = query.filter(models.Document.document_type == document_type)
    return query.all()


@app.post("/api/documents/{document_id}/representation")
def generate_document_representation(document_id: str, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        return {"detail": "document not found"}

    student = db.query(models.Student).filter(models.Student.id == document.student_id).first()
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.student_id == document.student_id).first()
    student_name = student.full_name if student else "Aluno não identificado"
    course_name = enrollment.course_name if enrollment else "Curso não informado"

    summary = (
        f"{document.title} - {student_name} - {course_name} - "
        f"{document.document_type} - {document.status}"
    )
    representation = DocumentRepresentation(
        document_id=document_id,
        student_name=student_name,
        course_name=course_name,
        visual_type="academic-card",
        summary=summary,
    )
    add_audit(db, "document", document_id, "representation_generated", "Academic visual representation generated")
    return representation.model_dump()


@app.get("/api/documents/{document_id}/retention")
def get_document_retention_policy(document_id: str, db: Session = Depends(get_db)):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        return {"detail": "document not found"}

    retention_years = 5 if document.status in {"validated", "signed", "archived"} else 3
    retention = RetentionPolicy(
        document_id=document_id,
        retention_years=retention_years,
        status="active",
        expires_at=f"{datetime.utcnow().year + retention_years}-12-31",
    )
    add_audit(db, "document", document_id, "retention_checked", "Retention policy verified")
    return retention.model_dump()


@app.get("/api/audit")
def list_audit_events(db: Session = Depends(get_db)):
    return db.query(models.AuditEvent).all()


# ==================== Retention Management ====================
@app.get("/api/documents/retention/check")
def check_retention_violations(db: Session = Depends(get_db)):
    """Verificar quais documentos violam a política de retenção."""
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
    
    return result


@app.get("/api/documents/retention/stats")
def get_retention_statistics(db: Session = Depends(get_db)):
    """Obter estatísticas sobre o ciclo de vida dos documentos."""
    stats = RetentionService.get_lifecycle_statistics(db)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "statistics": stats,
    }


@app.get("/api/documents/{document_id}/lifecycle")
def get_document_lifecycle(document_id: str, db: Session = Depends(get_db)):
    """Obter informações de ciclo de vida de um documento específico."""
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        return {"detail": "document not found"}
    
    retention_years = RetentionService.get_retention_period(document.document_type)
    expiry_date = RetentionService.calculate_expiry_date(document.created_at, document.document_type)
    days_remaining = (expiry_date - datetime.utcnow()).days
    
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
def add_audit(db: Session, entity: str, entity_id: str, action: str, details: str):
    audit_event = models.AuditEvent(
        id=str(len(db.query(models.AuditEvent).all()) + 1),
        document_id="0",  # Placeholder for non-document audits
        entity=entity,
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(audit_event)
    db.commit()
