import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_db
from app import models
from app.academic_history import current_enrollment_academic_link
from app.models_ged import GEDDocument
from app.models_xsd import SchemaVersion
from app.auth import (
    check_campus_access,
    check_institution_access,
    get_current_active_user,
    role_checker,
)
from app.privacy_utils import mask_cpf, mask_email, mask_name, mask_phone

class XmlGenerationRequest(BaseModel):
    student_name: str
    course_name: str
    status: str
    document_type: str
    schema_version: Optional[str] = None
    namespace: Optional[str] = None
    environment: str = "homologation"

router = APIRouter(tags=["GED - Vida Acadêmica (Curso e Diplomação)"])


def _mask_student_response(student: models.Student, current_user: models.User) -> "StudentResponse":
    if current_user.role == "admin_global":
        return StudentResponse(
            id=student.id,
            institution_id=student.institution_id,
            campus_id=student.campus_id,
            full_name=student.full_name,
            social_name=student.social_name,
            sex=student.sex,
            nationality=student.nationality,
            birthplace_municipality_code=student.birthplace_municipality_code,
            birthplace_municipality_name=student.birthplace_municipality_name,
            birthplace_state=student.birthplace_state,
            birth_date=student.birth_date,
            rg_number=student.rg_number,
            rg_issuing_authority=student.rg_issuing_authority,
            rg_state=student.rg_state,
            cpf=student.cpf,
            email=student.email,
            phone=student.phone,
            address_street=student.address_street,
            address_number=student.address_number,
            address_complement=student.address_complement,
            address_neighborhood=student.address_neighborhood,
            address_city=student.address_city,
            address_state=student.address_state,
            address_postal_code=student.address_postal_code,
        )

    return StudentResponse(
        id=student.id,
        institution_id=student.institution_id,
        campus_id=student.campus_id,
        full_name=mask_name(student.full_name),
        social_name=None,
        sex=None,
        nationality=None,
        birthplace_municipality_code=None,
        birthplace_municipality_name=None,
        birthplace_state=None,
        birth_date=student.birth_date,
        rg_number=None,
        rg_issuing_authority=None,
        rg_state=None,
        cpf=mask_cpf(student.cpf),
        email=mask_email(student.email),
        phone=mask_phone(student.phone),
    )

def _mask_guardian_response(guardian: models.Guardian, current_user: models.User) -> GuardianResponse:
    if current_user.role == "admin_global":
        return GuardianResponse.model_validate(guardian)
    return GuardianResponse(
        id=guardian.id,
        student_id=guardian.student_id,
        full_name=mask_name(guardian.full_name),
        cpf=mask_cpf(guardian.cpf),
        email=mask_email(guardian.email),
        phone=mask_phone(guardian.phone),
        relationship_type=guardian.relationship_type,
    )

def _get_accessible_student(db: Session, student_id: str, current_user: models.User) -> models.Student:
    query = db.query(models.Student).filter(models.Student.id == student_id)
    if current_user.role != "admin_global":
        if not current_user.institution_id:
            raise HTTPException(status_code=403, detail="Usuário sem instituição vinculada")
        query = query.filter(models.Student.institution_id == current_user.institution_id)
        if current_user.campus_id:
            query = query.filter(models.Student.campus_id == current_user.campus_id)
    student = query.first()
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    check_institution_access(current_user, student.institution_id)
    check_campus_access(current_user, student.campus_id)
    return student


# Schemas repetidos ou importados
class StudentResponse(BaseModel):
    id: str
    institution_id: str
    campus_id: Optional[str] = None
    full_name: str
    social_name: Optional[str] = None
    sex: Optional[str] = None
    nationality: Optional[str] = None
    birthplace_municipality_code: Optional[str] = None
    birthplace_municipality_name: Optional[str] = None
    birthplace_state: Optional[str] = None
    birth_date: date
    rg_number: Optional[str] = None
    rg_issuing_authority: Optional[str] = None
    rg_state: Optional[str] = None
    cpf: str
    email: str
    phone: Optional[str] = None
    address_street: Optional[str] = None
    address_number: Optional[str] = None
    address_complement: Optional[str] = None
    address_neighborhood: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class StudentUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2)
    social_name: Optional[str] = Field(default=None, max_length=160)
    sex: Optional[str] = Field(default=None, max_length=40)
    nationality: Optional[str] = Field(default=None, max_length=100)
    birthplace_municipality_code: Optional[str] = Field(default=None, max_length=10)
    birthplace_municipality_name: Optional[str] = Field(default=None, max_length=120)
    birthplace_state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    birth_date: Optional[date] = None
    rg_number: Optional[str] = Field(default=None, max_length=30)
    rg_issuing_authority: Optional[str] = Field(default=None, max_length=40)
    rg_state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    cpf: Optional[str] = Field(default=None, min_length=11, max_length=11)
    email: Optional[str] = Field(default=None, min_length=3)
    phone: Optional[str] = Field(default=None, max_length=32)
    address_street: Optional[str] = Field(default=None, max_length=160)
    address_number: Optional[str] = Field(default=None, max_length=20)
    address_complement: Optional[str] = Field(default=None, max_length=120)
    address_neighborhood: Optional[str] = Field(default=None, max_length=120)
    address_city: Optional[str] = Field(default=None, max_length=120)
    address_state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    address_postal_code: Optional[str] = Field(default=None, max_length=12)
    campus_id: Optional[str] = None

class GuardianResponse(BaseModel):
    id: str
    student_id: str
    full_name: str
    cpf: str
    email: str
    phone: Optional[str] = None
    address_street: Optional[str] = None
    address_number: Optional[str] = None
    address_complement: Optional[str] = None
    address_neighborhood: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    relationship_type: str
    model_config = ConfigDict(from_attributes=True)

class GuardianUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2)
    cpf: Optional[str] = Field(default=None, min_length=11, max_length=11)
    email: Optional[str] = Field(default=None, min_length=3)
    phone: Optional[str] = Field(default=None, max_length=32)
    address_street: Optional[str] = Field(default=None, max_length=160)
    address_number: Optional[str] = Field(default=None, max_length=20)
    address_complement: Optional[str] = Field(default=None, max_length=120)
    address_neighborhood: Optional[str] = Field(default=None, max_length=120)
    address_city: Optional[str] = Field(default=None, max_length=120)
    address_state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    address_postal_code: Optional[str] = Field(default=None, max_length=12)
    relationship_type: Optional[str] = Field(default=None, min_length=2)

class EnrollmentResponse(BaseModel):
    id: str
    institution_id: str
    student_id: str
    academic_class_id: Optional[str] = None
    course_name: str
    class_name: str
    year: int
    status: str
    result: str = "pending"
    model_config = ConfigDict(from_attributes=True)

@router.get("/api/students", response_model=List[StudentResponse])
def get_students(
    institution_id: Optional[str] = None,
    cpf: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Student)
    if institution_id:
        query = query.filter(models.Student.institution_id == institution_id)
    if cpf:
        query = query.filter(models.Student.cpf == cpf)
    # Por segurança, sempre filtramos pela instituição do usuário, a não ser que ele seja admin global
    if current_user.role != "admin_global":
        query = query.filter(models.Student.institution_id == current_user.institution_id)
        if current_user.campus_id:
            query = query.filter(models.Student.campus_id == current_user.campus_id)

    students = query.all()
    return [_mask_student_response(student, current_user) for student in students]

@router.get("/api/students/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    student = _get_accessible_student(db, student_id, current_user)
    return _mask_student_response(student, current_user)

@router.patch("/api/students/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: str,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        role_checker(["admin_global", "admin_instituicao", "operador", "academico"])
    ),
):
    student = _get_accessible_student(db, student_id, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if "campus_id" in changes and changes["campus_id"] is not None:
        campus = db.query(models.Campus).filter(
            models.Campus.id == changes["campus_id"],
            models.Campus.institution_id == student.institution_id,
        ).first()
        if campus is None:
            raise HTTPException(status_code=422, detail="campus does not belong to student's institution")
        check_campus_access(current_user, campus.id)

    cpf = changes.get("cpf")
    if cpf and db.query(models.Student).filter(
        models.Student.cpf == cpf,
        models.Student.id != student.id,
    ).first():
        raise HTTPException(status_code=409, detail="student CPF already exists")

    if "birth_date" in changes and changes["birth_date"] is not None:
        changes["birth_date"] = changes["birth_date"].isoformat()
    changed_fields = [
        field for field, value in changes.items()
        if getattr(student, field) != value
    ]
    for field in changed_fields:
        setattr(student, field, changes[field])

    if changed_fields:
        from app.main import add_audit
        add_audit(
            db,
            "student",
            student.id,
            "updated",
            f"Student fields updated: {', '.join(sorted(changed_fields))}",
            current_user.id,
        )
    db.commit()
    db.refresh(student)
    return _mask_student_response(student, current_user)

@router.get("/api/students/{student_id}/guardians", response_model=List[GuardianResponse])
def get_student_guardians(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    _get_accessible_student(db, student_id, current_user)
    guardians = db.query(models.Guardian).filter(
        models.Guardian.student_id == student_id
    ).order_by(models.Guardian.full_name).all()
    return [_mask_guardian_response(guardian, current_user) for guardian in guardians]

@router.patch(
    "/api/students/{student_id}/guardians/{guardian_id}",
    response_model=GuardianResponse,
)
def update_student_guardian(
    student_id: str,
    guardian_id: str,
    payload: GuardianUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        role_checker(["admin_global", "admin_instituicao", "operador", "academico"])
    ),
):
    _get_accessible_student(db, student_id, current_user)
    guardian = db.query(models.Guardian).filter(
        models.Guardian.id == guardian_id,
        models.Guardian.student_id == student_id,
    ).first()
    if guardian is None:
        raise HTTPException(status_code=404, detail="guardian not found")

    changes = payload.model_dump(exclude_unset=True)
    cpf = changes.get("cpf")
    if cpf and db.query(models.Guardian).filter(
        models.Guardian.cpf == cpf,
        models.Guardian.id != guardian.id,
    ).first():
        raise HTTPException(status_code=409, detail="guardian CPF already exists")

    changed_fields = [
        field for field, value in changes.items()
        if getattr(guardian, field) != value
    ]
    for field in changed_fields:
        setattr(guardian, field, changes[field])
    if changed_fields:
        from app.main import add_audit
        add_audit(
            db,
            "guardian",
            guardian.id,
            "updated",
            f"Guardian fields updated: {', '.join(sorted(changed_fields))}",
            current_user.id,
        )
    db.commit()
    db.refresh(guardian)
    return _mask_guardian_response(guardian, current_user)

@router.get("/api/students/{student_id}/history")
def get_student_contact_history(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    student = _get_accessible_student(db, student_id, current_user)
    guardian_ids = [
        row[0] for row in db.query(models.Guardian.id).filter(
            models.Guardian.student_id == student.id
        ).all()
    ]
    events_query = db.query(models.AuditEvent).filter(
        models.AuditEvent.entity == "student",
        models.AuditEvent.entity_id == student.id,
    )
    if guardian_ids:
        guardian_events = db.query(models.AuditEvent).filter(
            models.AuditEvent.entity == "guardian",
            models.AuditEvent.entity_id.in_(guardian_ids),
        ).all()
    else:
        guardian_events = []
    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student.id,
        models.Enrollment.institution_id == student.institution_id,
    ).all()
    enrollment_ids = [enrollment.id for enrollment in enrollments]
    enrollment_events = (
        db.query(models.AuditEvent)
        .filter(
            models.AuditEvent.entity == "enrollment",
            models.AuditEvent.entity_id.in_(enrollment_ids),
        )
        .all()
        if enrollment_ids
        else []
    )
    events = events_query.all() + guardian_events + enrollment_events
    events.sort(key=lambda event: (event.created_at, event.id), reverse=True)

    enrollment_by_id = {enrollment.id: enrollment for enrollment in enrollments}
    stored_links: dict[str, dict] = {}
    for event in enrollment_events:
        try:
            details = json.loads(event.details or "")
        except json.JSONDecodeError:
            continue
        if (
            isinstance(details, dict)
            and isinstance(details.get("academic_link"), dict)
        ):
            stored_links.setdefault(event.entity_id, details["academic_link"])

    items = []
    enrollments_with_events: set[str] = set()
    for event in events:
        if event.entity == "enrollment":
            try:
                details = json.loads(event.details or "")
            except json.JSONDecodeError:
                details = {}
            if not isinstance(details, dict):
                details = {}
            enrollment = enrollment_by_id.get(event.entity_id)
            academic_link = details.get("academic_link")
            snapshot_available = isinstance(academic_link, dict)
            link_source = "audit_snapshot" if snapshot_available else None
            if not snapshot_available:
                academic_link = stored_links.get(event.entity_id)
                snapshot_available = academic_link is not None
                if snapshot_available:
                    link_source = "audit_snapshot"
            if academic_link is None and enrollment is not None:
                academic_link, link_source = current_enrollment_academic_link(
                    db,
                    enrollment,
                )
            if not academic_link:
                academic_link = None
            required_snapshot_fields = (
                "course_id",
                "curriculum_id",
                "discipline_id",
                "class_id",
                "term_id",
                "campus_id",
            )
            snapshot_complete = snapshot_available and all(
                academic_link.get(field) is not None
                for field in required_snapshot_fields
            )

            enrollments_with_events.add(event.entity_id)
            items.append({
                "entity_type": "enrollment",
                "action": event.action,
                "user_id": event.user_id,
                "created_at": event.created_at,
                "_sort_id": event.id,
                "academic_link": academic_link,
                "academic_link_source": link_source,
                "snapshot_complete": snapshot_complete,
                "state_change": {
                    "before": details.get("before"),
                    "after": details.get("after") or {
                        key: details[key]
                        for key in ("status", "result")
                        if key in details
                    },
                } if any(key in details for key in ("before", "after", "status", "result")) else None,
                "snapshot_available": snapshot_available,
                "is_audit_event": True,
            })
            continue
        prefix = {
            ("student", "updated"): "Student fields updated: ",
            ("guardian", "updated"): "Guardian fields updated: ",
        }.get((event.entity, event.action))
        details = event.details or ""
        changed_fields = (
            [field.strip() for field in details[len(prefix):].split(", ") if field.strip()]
            if prefix and details.startswith(prefix)
            else []
        )
        items.append({
            "entity_type": event.entity,
            "action": event.action,
            "user_id": event.user_id,
            "created_at": event.created_at,
            "_sort_id": event.id,
            "changed_fields": changed_fields,
            "academic_link": None,
            "state_change": None,
            "snapshot_available": False,
        })

    for enrollment in enrollments:
        if enrollment.id in enrollments_with_events:
            continue
        academic_link, link_source = current_enrollment_academic_link(db, enrollment)
        items.append({
            "entity_type": "enrollment",
            "action": "legacy_record",
            "user_id": None,
            "created_at": enrollment.created_at,
            "_sort_id": enrollment.id,
            "academic_link": academic_link or None,
            "academic_link_source": link_source,
            "snapshot_complete": False,
            "state_change": {
                "before": None,
                "after": {
                    "status": enrollment.status,
                    "result": enrollment.result,
                },
            },
            "snapshot_available": False,
            "is_audit_event": False,
        })

    items.sort(
        key=lambda item: (
            item["created_at"],
            item["_sort_id"],
        ),
        reverse=True,
    )
    for item in items:
        item.pop("_sort_id")
    return {"student_id": student.id, "items": items}

@router.get("/api/enrollments", response_model=List[EnrollmentResponse])
def get_enrollments(
    student_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Enrollment)
    if student_id:
        query = query.filter(models.Enrollment.student_id == student_id)
    
    if current_user.role != "admin_global":
        query = query.filter(models.Enrollment.institution_id == current_user.institution_id)
        if current_user.campus_id:
            query = query.filter(models.Enrollment.campus_id == current_user.campus_id)
        
    return query.all()

@router.post("/api/documents/{document_id}/xml")
def generate_xml_for_document(
    document_id: str,
    payload: XmlGenerationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Validar documento
    document = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Verificar permissão do documento
    from app.auth import verify_document_ownership
    verify_document_ownership(current_user, document)

    if not payload.schema_version:
        from app.main import add_audit
        add_audit(
            db,
            "document",
            document_id,
            "xml_generation_blocked",
            "Schema version is required; inference is forbidden.",
            current_user.id,
        )
        db.commit()
        raise HTTPException(409, "schema version inference is forbidden")

    schema = db.query(SchemaVersion).filter(
        SchemaVersion.code == payload.schema_version,
        SchemaVersion.environment == payload.environment,
        SchemaVersion.status == "approved",
    ).first()
    if not schema:
        raise HTTPException(409, "schema version is not approved")

    if payload.document_type == "historico":
        from app.main import add_audit
        add_audit(
            db,
            "document",
            document_id,
            "xml_generation_blocked",
            "Historical XML generation requires complete v1.05 academic data and XML signatures.",
            current_user.id,
        )
        db.commit()
        raise HTTPException(
            status_code=409,
            detail=(
                "Historical XML generation is unavailable until the complete MEC v1.05 "
                "data mapping and XML signature flow are implemented."
            ),
        )

    generated_xml = ""
    # Selecionar o gerador correto de acordo com o tipo
    if payload.document_type == "diploma":
        from app.diploma_generator import generate_diploma_xml
        from app.schemas_diploma import Model as DiplomaPayload
        # Dados mockados para gerar XML. Na vida real viriam do ERP ou form
        data = DiplomaPayload(
            student_name=payload.student_name,
            course_name=payload.course_name,
            status=payload.status,
            namespace=payload.namespace,
            environment=payload.environment
        )
        generated_xml = generate_diploma_xml(data)
    elif payload.document_type == "curriculo":
        from app.curriculo_generator import generate_curriculo_xml
        from app.schemas_curriculo import Model as CurriculoPayload
        data = CurriculoPayload(
            course_name=payload.course_name
        )
        generated_xml = generate_curriculo_xml(data)
    else:
        raise HTTPException(status_code=400, detail="Invalid document type for XML generation")
        
    from app.main import add_audit
    add_audit(db, "document", document_id, "xml_generated", f"XML generated for {payload.document_type}", current_user.id)
    db.commit()
    return {"xml_content": generated_xml}


@router.post("/api/documents/{document_id}/representation")
def generate_visual_representation(
    document_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Essa rota geraria o RVDD (Representação Visual do Diploma Digital) ou HTML do histórico.
    document = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.auth import verify_document_ownership
    verify_document_ownership(current_user, document)

    from app.rvdd_generator import generate_rvdd_html
    html_content = generate_rvdd_html(document_id, payload.get("student_name", "Aluno"), payload.get("course_name", "Curso"))
    
    from app.main import add_audit
    add_audit(db, "document", document_id, "representation_generated", "Visual representation generated", current_user.id)
    db.commit()
    
    # Retornar como JSON para facilidade, o frontend renderiza num iframe
    return {"html_content": html_content}
