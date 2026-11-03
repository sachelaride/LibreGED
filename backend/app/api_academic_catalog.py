import json
from datetime import UTC, date, datetime, time
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.academic_history import current_enrollment_academic_link
from app.auth import require_module_access
from app.database import get_db
from app.models_academic_catalog import (
    AcademicClass,
    AcademicCoordinatorAssignment,
    CourseTranscriptProfile,
    AcademicCreditRecognition,
    AcademicClassSchedule,
    AcademicCourse,
    AcademicDepartment,
    AcademicCurriculum,
    AcademicCurriculumDiscipline,
    AcademicCurriculumElectiveDiscipline,
    AcademicCurriculumElectiveGroup,
    AcademicCurriculumEquivalence,
    AcademicCurriculumPrerequisite,
    AcademicDiscipline,
    AcademicOffering,
    AcademicRoom,
    AcademicStaff,
    AcademicSector,
    AcademicTerm,
    InstitutionTranscriptProfile,
    StudentCourseTranscriptProfile,
)

router = APIRouter(prefix="/secretaria/academico", tags=["Secretaria - Base Acadêmica"])
SecretaryUser = Depends(require_module_access("secretaria"))


class CourseCreate(BaseModel):
    campus_id: str | None = None
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=160)
    degree: str = Field(min_length=2, max_length=80)
    modality: Literal["presencial", "ead", "hibrida"]
    duration_periods: int = Field(gt=0, le=30)
    status: Literal["ativo", "inativo"] = "ativo"


class CampusCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class DepartmentCreate(BaseModel):
    campus_id: str | None = None
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=160)
    status: Literal["ativo", "inativo"] = "ativo"


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    status: Literal["ativo", "inativo"] | None = None


class SectorCreate(BaseModel):
    department_id: str
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=160)
    status: Literal["ativo", "inativo"] = "ativo"


class SectorUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    status: Literal["ativo", "inativo"] | None = None


class DisciplineCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=160)
    workload_hours: int = Field(gt=0, le=2000)
    credits: int = Field(ge=0, le=100)
    syllabus: str | None = None
    status: Literal["ativo", "inativo"] = "ativo"


class TermCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=100)
    starts_on: date
    ends_on: date
    status: Literal["planejado", "ativo", "encerrado"] = "planejado"


class EnrollmentTransfer(BaseModel):
    target_class_id: str = Field(min_length=1)


class CurriculumDisciplineCreate(BaseModel):
    discipline_id: str
    term_number: int = Field(gt=0, le=30)
    is_required: bool = True
    prerequisite_discipline_ids: list[str] = Field(default_factory=list)


class CurriculumPrerequisiteCreate(BaseModel):
    prerequisite_discipline_id: str


class CurriculumEquivalenceCreate(BaseModel):
    equivalent_discipline_id: str


class CurriculumElectiveGroupCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=160)
    minimum_credits: int = Field(gt=0, le=1000)
    discipline_ids: list[str] = Field(min_length=1)


class CurriculumCreate(BaseModel):
    course_id: str
    version: str = Field(min_length=1, max_length=30)
    effective_from: date
    disciplines: list[CurriculumDisciplineCreate] = Field(min_length=1)
    status: Literal["ativa", "inativa"] = "ativa"


class CreditRecognitionCreate(BaseModel):
    course_id: str
    curriculum_id: str
    discipline_id: str
    source_institution: str = Field(min_length=2, max_length=200)
    source_course: str = Field(min_length=2, max_length=160)
    source_discipline: str = Field(min_length=2, max_length=160)
    workload_hours: int = Field(gt=0, le=2000)
    credits: int = Field(ge=0, le=100)
    request_note: str | None = Field(default=None, max_length=2000)


class CreditRecognitionDecision(BaseModel):
    status: Literal["approved", "rejected"]
    decision_note: str | None = Field(default=None, max_length=2000)


class StudentTranscriptIdentityUpdate(BaseModel):
    social_name: str | None = Field(default=None, max_length=160)
    sex: str | None = Field(default=None, max_length=40)
    nationality: str | None = Field(default=None, max_length=100)
    birthplace_municipality_code: str | None = Field(default=None, max_length=10)
    birthplace_municipality_name: str | None = Field(default=None, max_length=120)
    birthplace_state: str | None = Field(default=None, min_length=2, max_length=2)
    rg_number: str | None = Field(default=None, max_length=30)
    rg_issuing_authority: str | None = Field(default=None, max_length=40)
    rg_state: str | None = Field(default=None, min_length=2, max_length=2)


class StudentCourseTranscriptProfileUpdate(BaseModel):
    entry_date: date
    access_form: Literal[
        "Vestibular",
        "Enem",
        "Avaliação Seriada",
        "Seleção Simplificada",
        "Egresso BI/LI",
        "PEC-G",
        "Transferência Ex Officio",
        "Decisão judicial",
        "Seleção para Vagas Remanescentes",
        "Seleção para Vagas de Programas Especiais",
    ]


class StaffTranscriptProfileUpdate(BaseModel):
    titulacao: Literal[
        "Tecnólogo",
        "Graduação",
        "Especialização",
        "Mestrado",
        "Doutorado",
    ]
    cpf: str | None = Field(default=None, pattern=r"^\d{11}$")
    lattes: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^https://lattes\.cnpq\.br/\d+$",
    )


class TranscriptAddress(BaseModel):
    logradouro: str = Field(min_length=1, max_length=160)
    numero: str = Field(min_length=1, max_length=20)
    bairro: str = Field(min_length=1, max_length=120)
    codigo_municipio: str = Field(min_length=1, max_length=10)
    nome_municipio: str = Field(min_length=1, max_length=120)
    uf: str = Field(min_length=2, max_length=2)
    cep: str = Field(min_length=1, max_length=12)


class TranscriptPublication(BaseModel):
    tipo: str = Field(min_length=1, max_length=80)
    numero: str = Field(min_length=1, max_length=80)
    data: date
    veiculo_publicacao: str = Field(min_length=1, max_length=160)
    data_publicacao: date
    secao_publicacao: str = Field(min_length=1, max_length=20)
    pagina_publicacao: str = Field(min_length=1, max_length=20)


class TranscriptAuthorization(BaseModel):
    tipo: str = Field(min_length=1, max_length=80)
    numero: str = Field(min_length=1, max_length=80)
    data: date
    veiculo_publicacao: str = Field(min_length=1, max_length=160)
    data_publicacao: date


class TranscriptQualification(BaseModel):
    nome_habilitacao: str = Field(min_length=1, max_length=160)
    data_habilitacao: date


class InstitutionTranscriptProfilePayload(BaseModel):
    codigo_mec: str = Field(min_length=1, max_length=30)
    endereco: TranscriptAddress
    credenciamento: TranscriptPublication
    recredenciamento: TranscriptPublication
    renovacao_de_recredenciamento: TranscriptPublication
    mantenedora_razao_social: str = Field(min_length=2, max_length=200)
    mantenedora_cnpj: str = Field(min_length=14, max_length=18)
    mantenedora_endereco: TranscriptAddress


class CourseTranscriptProfilePayload(BaseModel):
    codigo_curso_emec: str = Field(min_length=1, max_length=30)
    autorizacao: TranscriptAuthorization
    reconhecimento: TranscriptPublication
    renovacao_reconhecimento: TranscriptPublication
    habilitacao: list[TranscriptQualification] = Field(default_factory=list)


class StaffCreate(BaseModel):
    campus_id: str | None = None
    user_id: str | None = None
    staff_code: str = Field(min_length=2, max_length=30)
    full_name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=254)
    staff_type: Literal["professor", "coordenador", "tutor"]
    status: Literal["ativo", "inativo"] = "ativo"


class RoomCreate(BaseModel):
    campus_id: str
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=120)
    capacity: int = Field(gt=0, le=10000)
    room_type: Literal["sala", "laboratorio", "auditorio", "virtual"] = "sala"
    is_active: bool = True


class OfferingCreate(BaseModel):
    course_id: str
    discipline_id: str
    term_id: str
    campus_id: str
    capacity: int = Field(gt=0, le=10000)
    status: Literal["aberta", "fechada", "cancelada"] = "aberta"


class ClassCreate(BaseModel):
    offering_id: str
    code: str = Field(min_length=1, max_length=30)
    teacher_id: str | None = None
    coordinator_id: str | None = None
    capacity: int = Field(gt=0, le=10000)
    status: Literal["planejada", "ativa", "encerrada", "cancelada"] = "planejada"


class ScheduleCreate(BaseModel):
    room_id: str | None = None
    weekday: int = Field(ge=1, le=7)
    starts_at: time
    ends_at: time


class ScheduleUpdate(BaseModel):
    room_id: str | None = None
    weekday: int | None = Field(default=None, ge=1, le=7)
    starts_at: time | None = None
    ends_at: time | None = None


class CourseUpdate(BaseModel):
    campus_id: str | None = None
    code: str | None = Field(default=None, min_length=2, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    degree: str | None = Field(default=None, min_length=2, max_length=80)
    modality: Literal["presencial", "ead", "hibrida"] | None = None
    duration_periods: int | None = Field(default=None, gt=0, le=30)
    status: Literal["ativo", "inativo"] | None = None


class DisciplineUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    workload_hours: int | None = Field(default=None, gt=0, le=2000)
    credits: int | None = Field(default=None, ge=0, le=100)
    syllabus: str | None = None
    status: Literal["ativo", "inativo"] | None = None


class TermUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=100)
    starts_on: date | None = None
    ends_on: date | None = None
    status: Literal["planejado", "ativo", "encerrado"] | None = None


class StaffUpdate(BaseModel):
    campus_id: str | None = None
    user_id: str | None = None
    staff_code: str | None = Field(default=None, min_length=2, max_length=30)
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    email: str | None = Field(default=None, min_length=5, max_length=254)
    staff_type: Literal["professor", "coordenador", "tutor"] | None = None
    status: Literal["ativo", "inativo"] | None = None


class CoordinatorAssignmentCreate(BaseModel):
    coordinator_id: str
    course_id: str
    campus_id: str
    starts_on: date
    ends_on: date


class CoordinatorAssignmentUpdate(BaseModel):
    coordinator_id: str | None = None
    course_id: str | None = None
    campus_id: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None


class RoomUpdate(BaseModel):
    campus_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    capacity: int | None = Field(default=None, gt=0, le=10000)
    room_type: Literal["sala", "laboratorio", "auditorio", "virtual"] | None = None
    is_active: bool | None = None


class OfferingUpdate(BaseModel):
    course_id: str | None = None
    discipline_id: str | None = None
    term_id: str | None = None
    campus_id: str | None = None
    capacity: int | None = Field(default=None, gt=0, le=10000)
    status: Literal["aberta", "fechada", "cancelada"] | None = None


class ClassUpdate(BaseModel):
    offering_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=30)
    teacher_id: str | None = None
    coordinator_id: str | None = None
    capacity: int | None = Field(default=None, gt=0, le=10000)
    status: Literal["planejada", "ativa", "encerrada", "cancelada"] | None = None


def _institution_id(user: Any) -> str:
    institution_id = getattr(user, "institution_id", None)
    if not institution_id:
        raise HTTPException(status_code=403, detail="Usuário sem instituição vinculada")
    return institution_id


def _user_campus_id(user: Any) -> str | None:
    if getattr(user, "role", None) == "admin_global":
        return None
    return getattr(user, "campus_id", None)


def _check_campus(db: Session, campus_id: str | None, institution_id: str, user: Any = None) -> None:
    user_campus_id = _user_campus_id(user)
    if campus_id is None:
        if user_campus_id:
            raise HTTPException(status_code=403, detail="O registro deve pertencer ao campus vinculado ao usuário")
        return
    if user_campus_id and campus_id != user_campus_id:
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    campus = db.query(models.Campus).filter(
        models.Campus.id == campus_id,
        models.Campus.institution_id == institution_id,
    ).first()
    if campus is None:
        raise HTTPException(status_code=404, detail="Campus não encontrado nesta instituição")


def _get_scoped(db: Session, model: Any, record_id: str, institution_id: str, label: str, user: Any = None):
    record = db.query(model).filter(
        model.id == record_id,
        model.institution_id == institution_id,
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail=f"{label} não encontrado")
    record_campus_id = getattr(record, "campus_id", None)
    if record_campus_id is None:
        department = getattr(record, "department", None)
        record_campus_id = getattr(department, "campus_id", None)
    if record_campus_id is None:
        related_campus = getattr(record, "offering", None) or getattr(record, "course", None)
        record_campus_id = getattr(related_campus, "campus_id", None)
    user_campus_id = _user_campus_id(user)
    if user_campus_id and record_campus_id and record_campus_id != user_campus_id:
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    return record


def _save(db: Session, record: Any):
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Registro duplicado ou vinculado a dados inválidos") from exc
    return record


def _audit_catalog_change(
    db: Session,
    user: Any,
    entity: str,
    entity_id: str,
    action: str,
    changes: dict[str, Any],
) -> None:
    from app.main import add_audit

    add_audit(
        db,
        entity,
        entity_id,
        action,
        json.dumps(changes, ensure_ascii=False, sort_keys=True, default=str),
        str(getattr(user, "id", None) or getattr(user, "username", "")) or None,
    )


def _model_dict(record: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: getattr(record, field) for field in fields}


def _validate_staff_user(
    db: Session,
    user_id: str | None,
    staff_type: str,
    institution_id: str,
    campus_id: str | None,
    staff_id: str | None = None,
) -> None:
    if user_id is None:
        return
    if staff_type not in {"professor", "coordenador"}:
        raise HTTPException(status_code=422, detail="Apenas professores e coordenadores podem ser vinculados a contas acadêmicas")
    linked_user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.institution_id == institution_id,
        models.User.role == "academico",
        models.User.is_active.is_(True),
    ).first()
    if linked_user is None:
        raise HTTPException(status_code=422, detail="Selecione uma conta acadêmica ativa da mesma instituição")
    if linked_user.campus_id and campus_id and linked_user.campus_id != campus_id:
        raise HTTPException(status_code=422, detail="A conta e o profissional devem pertencer ao mesmo campus")
    existing_link = db.query(AcademicStaff).filter(
        AcademicStaff.user_id == user_id,
        AcademicStaff.id != (staff_id or ""),
    ).first()
    if existing_link:
        raise HTTPException(status_code=409, detail="A conta já está vinculada a outro profissional acadêmico")


def _resolve_student_curriculum(
    db: Session,
    student: models.Student,
    course: AcademicCourse,
    institution_id: str,
) -> AcademicCurriculum:
    first_course_term = (
        db.query(func.min(AcademicTerm.starts_on))
        .join(AcademicOffering, AcademicOffering.term_id == AcademicTerm.id)
        .join(AcademicClass, AcademicClass.offering_id == AcademicOffering.id)
        .join(
            models.Enrollment,
            models.Enrollment.academic_class_id == AcademicClass.id,
        )
        .filter(
            models.Enrollment.student_id == student.id,
            models.Enrollment.institution_id == institution_id,
            AcademicOffering.course_id == course.id,
            AcademicOffering.institution_id == institution_id,
            AcademicClass.institution_id == institution_id,
        )
        .scalar()
    )
    curriculum = (
        db.query(AcademicCurriculum)
        .filter(
            AcademicCurriculum.institution_id == institution_id,
            AcademicCurriculum.course_id == course.id,
            AcademicCurriculum.status == "ativa",
            AcademicCurriculum.effective_from <= (first_course_term or date.today()),
        )
        .order_by(AcademicCurriculum.effective_from.desc())
        .first()
    )
    if curriculum is None:
        raise HTTPException(
            status_code=409,
            detail="Não há matriz curricular ativa para o início do vínculo do aluno",
        )
    return curriculum


def _credit_recognition_dict(record: AcademicCreditRecognition) -> dict[str, Any]:
    link = record.curriculum_discipline
    return {
        "id": record.id,
        "status": record.status,
        "source_institution": record.source_institution,
        "source_course": record.source_course,
        "source_discipline": record.source_discipline,
        "workload_hours": record.workload_hours,
        "credits": record.credits,
        "request_note": record.request_note,
        "decision_note": record.decision_note,
        "requested_at": record.requested_at,
        "decided_at": record.decided_at,
        "target_discipline": link.discipline.name,
    }


def _apply_partial_update(db: Session, record: Any, payload: BaseModel) -> Any:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return record
    for field, value in data.items():
        if value is not None:
            setattr(record, field, value)
    return _save(db, record)


@router.get("/resumo")
def academic_catalog_summary(
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    campus_id = _user_campus_id(user)
    campus_query = db.query(models.Campus).filter_by(institution_id=institution_id)
    department_query = db.query(AcademicDepartment).filter_by(institution_id=institution_id)
    sector_query = db.query(AcademicSector).filter_by(institution_id=institution_id)
    course_query = db.query(AcademicCourse).filter_by(institution_id=institution_id)
    curriculum_query = db.query(AcademicCurriculum).join(AcademicCourse).filter(AcademicCurriculum.institution_id == institution_id)
    offering_query = db.query(AcademicOffering).filter_by(institution_id=institution_id)
    class_query = db.query(AcademicClass).join(AcademicOffering).filter(AcademicClass.institution_id == institution_id)
    staff_query = db.query(AcademicStaff).filter_by(institution_id=institution_id)
    room_query = db.query(AcademicRoom).filter_by(institution_id=institution_id)
    if campus_id:
        campus_query = campus_query.filter(models.Campus.id == campus_id)
        course_query = course_query.filter(or_(AcademicCourse.campus_id.is_(None), AcademicCourse.campus_id == campus_id))
        curriculum_query = curriculum_query.filter(or_(AcademicCourse.campus_id.is_(None), AcademicCourse.campus_id == campus_id))
        offering_query = offering_query.filter(AcademicOffering.campus_id == campus_id)
        class_query = class_query.filter(AcademicOffering.campus_id == campus_id)
        staff_query = staff_query.filter(or_(AcademicStaff.campus_id.is_(None), AcademicStaff.campus_id == campus_id))
        room_query = room_query.filter(AcademicRoom.campus_id == campus_id)
        department_query = department_query.filter(
            or_(AcademicDepartment.campus_id.is_(None), AcademicDepartment.campus_id == campus_id)
        )
        sector_query = sector_query.join(AcademicDepartment).filter(
            or_(AcademicDepartment.campus_id.is_(None), AcademicDepartment.campus_id == campus_id)
        )
    counts = {
        "campi": campus_query.count(),
        "departamentos": department_query.count(),
        "setores": sector_query.count(),
        "cursos": course_query.count(),
        "disciplinas": db.query(AcademicDiscipline).filter_by(institution_id=institution_id).count(),
        "matrizes": curriculum_query.count(),
        "periodos": db.query(AcademicTerm).filter_by(institution_id=institution_id).count(),
        "ofertas": offering_query.count(),
        "turmas": class_query.count(),
        "professores": staff_query.filter(AcademicStaff.staff_type == "professor").count(),
        "coordenadores": staff_query.filter(AcademicStaff.staff_type == "coordenador").count(),
        "salas": room_query.count(),
    }
    return {"module": "secretaria", "summary": counts}


@router.get("/campi")
def list_campuses(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(models.Campus).filter_by(institution_id=institution_id)
    if _user_campus_id(user):
        query = query.filter(models.Campus.id == _user_campus_id(user))
    records = query.order_by(models.Campus.name).all()
    return {"module": "secretaria", "items": [
        {"id": record.id, "name": record.name}
        for record in records
    ]}


@router.post("/campi", status_code=status.HTTP_201_CREATED)
def create_campus(payload: CampusCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    if getattr(user, "campus_id", None):
        raise HTTPException(status_code=403, detail="Apenas usuários com acesso institucional podem cadastrar campi")
    record = models.Campus(
        id=uuid4().hex,
        institution_id=institution_id,
        name=payload.name.strip(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"module": "secretaria", "campus": {"id": record.id, "name": record.name}}


@router.get("/departamentos")
def list_departments(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(AcademicDepartment).filter_by(institution_id=institution_id)
    if _user_campus_id(user):
        query = query.filter(
            or_(
                AcademicDepartment.campus_id.is_(None),
                AcademicDepartment.campus_id == _user_campus_id(user),
            )
        )
    records = query.order_by(AcademicDepartment.name).all()
    return {
        "module": "secretaria",
        "items": [
            _model_dict(record, ("id", "campus_id", "code", "name", "status"))
            for record in records
        ],
    }


@router.post("/departamentos", status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    campus_id = payload.campus_id or _user_campus_id(user)
    _check_campus(db, campus_id, institution_id, user)
    record = AcademicDepartment(
        id=uuid4().hex,
        institution_id=institution_id,
        campus_id=campus_id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        status=payload.status,
    )
    record = _save(db, record)
    return {
        "module": "secretaria",
        "department": _model_dict(record, ("id", "campus_id", "code", "name", "status")),
    }


@router.patch("/departamentos/{department_id}")
def update_department(
    department_id: str,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    record = _get_scoped(
        db, AcademicDepartment, department_id, institution_id, "Departamento", user
    )
    data = payload.model_dump(exclude_unset=True)
    for field in ("code", "name"):
        if field in data and data[field] is not None:
            data[field] = data[field].strip()
    for field, value in data.items():
        if value is not None:
            setattr(record, field, value)
    record = _save(db, record)
    return {
        "module": "secretaria",
        "department": _model_dict(record, ("id", "campus_id", "code", "name", "status")),
    }


@router.get("/setores")
def list_sectors(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(AcademicSector).join(AcademicDepartment).filter(
        AcademicSector.institution_id == institution_id
    )
    if _user_campus_id(user):
        query = query.filter(
            or_(
                AcademicDepartment.campus_id.is_(None),
                AcademicDepartment.campus_id == _user_campus_id(user),
            )
        )
    records = query.order_by(AcademicDepartment.name, AcademicSector.name).all()
    return {
        "module": "secretaria",
        "items": [
            {
                **_model_dict(record, ("id", "department_id", "code", "name", "status")),
                "department_name": record.department.name,
            }
            for record in records
        ],
    }


@router.post("/setores", status_code=status.HTTP_201_CREATED)
def create_sector(
    payload: SectorCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    department = _get_scoped(
        db, AcademicDepartment, payload.department_id, institution_id, "Departamento", user
    )
    if department.status != "ativo":
        raise HTTPException(status_code=409, detail="O departamento está inativo")
    record = AcademicSector(
        id=uuid4().hex,
        institution_id=institution_id,
        department_id=department.id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        status=payload.status,
    )
    record = _save(db, record)
    return {
        "module": "secretaria",
        "sector": {
            **_model_dict(record, ("id", "department_id", "code", "name", "status")),
            "department_name": department.name,
        },
    }


@router.patch("/setores/{sector_id}")
def update_sector(
    sector_id: str,
    payload: SectorUpdate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicSector, sector_id, institution_id, "Setor", user)
    data = payload.model_dump(exclude_unset=True)
    for field in ("code", "name"):
        if field in data and data[field] is not None:
            data[field] = data[field].strip()
    for field, value in data.items():
        if value is not None:
            setattr(record, field, value)
    record = _save(db, record)
    return {
        "module": "secretaria",
        "sector": {
            **_model_dict(record, ("id", "department_id", "code", "name", "status")),
            "department_name": record.department.name,
        },
    }


@router.get("/historico/perfil-institucional")
def get_institution_transcript_profile(
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    institution = db.query(models.Institution).filter(
        models.Institution.id == institution_id
    ).first()
    if institution is None:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")
    record = db.query(InstitutionTranscriptProfile).filter(
        InstitutionTranscriptProfile.institution_id == institution_id
    ).first()
    return {
        "module": "secretaria",
        "configured": record is not None,
        "institution": {
            "id": institution.id,
            "name": institution.name,
            "cnpj": institution.cnpj,
            "legal_name": institution.legal_name,
        },
        "profile": record.data if record else None,
    }


@router.put("/historico/perfil-institucional")
def save_institution_transcript_profile(
    payload: InstitutionTranscriptProfilePayload,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    institution = db.query(models.Institution).filter(
        models.Institution.id == institution_id
    ).first()
    if institution is None:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")
    record = db.query(InstitutionTranscriptProfile).filter(
        InstitutionTranscriptProfile.institution_id == institution_id
    ).first()
    if record is None:
        record = InstitutionTranscriptProfile(
            id=uuid4().hex,
            institution_id=institution_id,
            data=payload.model_dump(mode="json"),
        )
        db.add(record)
        action = "transcript_profile_created"
    else:
        record.data = payload.model_dump(mode="json")
        action = "transcript_profile_updated"
    from app.main import add_audit
    add_audit(
        db,
        "institution",
        institution_id,
        action,
        "Institution transcript regulatory profile saved",
        str(getattr(user, "id", None) or "") or None,
    )
    db.commit()
    db.refresh(record)
    return {
        "configured": True,
        "institution": {
            "id": institution.id,
            "name": institution.name,
            "cnpj": institution.cnpj,
            "legal_name": institution.legal_name,
        },
        "profile": record.data,
    }


@router.get("/cursos/{course_id}/perfil-historico")
def get_course_transcript_profile(
    course_id: str,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    course = _get_scoped(db, AcademicCourse, course_id, institution_id, "Curso", user)
    record = db.query(CourseTranscriptProfile).filter(
        CourseTranscriptProfile.course_id == course.id,
        CourseTranscriptProfile.institution_id == institution_id,
    ).first()
    return {
        "module": "secretaria",
        "configured": record is not None,
        "course": {"id": course.id, "code": course.code, "name": course.name},
        "profile": record.data if record else None,
    }


@router.put("/cursos/{course_id}/perfil-historico")
def save_course_transcript_profile(
    course_id: str,
    payload: CourseTranscriptProfilePayload,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    course = _get_scoped(db, AcademicCourse, course_id, institution_id, "Curso", user)
    record = db.query(CourseTranscriptProfile).filter(
        CourseTranscriptProfile.course_id == course.id,
        CourseTranscriptProfile.institution_id == institution_id,
    ).first()
    if record is None:
        record = CourseTranscriptProfile(
            id=uuid4().hex,
            institution_id=institution_id,
            course_id=course.id,
            data=payload.model_dump(mode="json"),
        )
        db.add(record)
        action = "transcript_profile_created"
    else:
        record.data = payload.model_dump(mode="json")
        action = "transcript_profile_updated"
    from app.main import add_audit
    add_audit(
        db,
        "academic_course",
        course.id,
        action,
        "Course transcript regulatory profile saved",
        str(getattr(user, "id", None) or "") or None,
    )
    db.commit()
    db.refresh(record)
    return {
        "configured": True,
        "course": {"id": course.id, "code": course.code, "name": course.name},
        "profile": record.data,
    }


@router.get("/cursos")
def list_courses(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(AcademicCourse).filter_by(institution_id=institution_id)
    if _user_campus_id(user):
        query = query.filter(or_(AcademicCourse.campus_id.is_(None), AcademicCourse.campus_id == _user_campus_id(user)))
    records = query.order_by(AcademicCourse.name).all()
    return {"module": "secretaria", "items": [_model_dict(r, ("id", "campus_id", "code", "name", "degree", "modality", "duration_periods", "status")) for r in records]}


@router.post("/cursos", status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    values = payload.model_dump()
    values["campus_id"] = values["campus_id"] or _user_campus_id(user)
    _check_campus(db, values["campus_id"], institution_id, user)
    record = AcademicCourse(id=uuid4().hex, institution_id=institution_id, **values)
    return {"module": "secretaria", "course": _model_dict(_save(db, record), ("id", "campus_id", "code", "name", "degree", "modality", "duration_periods", "status"))}


@router.patch("/cursos/{course_id}")
def update_course(course_id: str, payload: CourseUpdate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicCourse, course_id, institution_id, "Curso", user)
    data = payload.model_dump(exclude_unset=True)
    if "campus_id" in data:
        _check_campus(db, data["campus_id"], institution_id, user)
    if not data:
        return {"module": "secretaria", "course": _model_dict(record, ("id", "campus_id", "code", "name", "degree", "modality", "duration_periods", "status"))}
    for field, value in data.items():
        if value is not None:
            setattr(record, field, value)
    record = _save(db, record)
    return {"module": "secretaria", "course": _model_dict(record, ("id", "campus_id", "code", "name", "degree", "modality", "duration_periods", "status"))}


@router.get("/disciplinas")
def list_disciplines(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    records = db.query(AcademicDiscipline).filter_by(institution_id=institution_id).order_by(AcademicDiscipline.name).all()
    return {"module": "secretaria", "items": [_model_dict(r, ("id", "code", "name", "workload_hours", "credits", "syllabus", "status")) for r in records]}


@router.post("/disciplinas", status_code=status.HTTP_201_CREATED)
def create_discipline(payload: DisciplineCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    record = AcademicDiscipline(id=uuid4().hex, institution_id=institution_id, **payload.model_dump())
    return {"module": "secretaria", "discipline": _model_dict(_save(db, record), ("id", "code", "name", "workload_hours", "credits", "syllabus", "status"))}


@router.patch("/disciplinas/{discipline_id}")
def update_discipline(discipline_id: str, payload: DisciplineUpdate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicDiscipline, discipline_id, institution_id, "Disciplina", user)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return {"module": "secretaria", "discipline": _model_dict(record, ("id", "code", "name", "workload_hours", "credits", "syllabus", "status"))}
    for field, value in data.items():
        if value is not None:
            setattr(record, field, value)
    record = _save(db, record)
    return {"module": "secretaria", "discipline": _model_dict(record, ("id", "code", "name", "workload_hours", "credits", "syllabus", "status"))}


@router.get("/periodos")
def list_terms(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    records = db.query(AcademicTerm).filter_by(institution_id=institution_id).order_by(AcademicTerm.starts_on.desc()).all()
    return {"module": "secretaria", "items": [_model_dict(r, ("id", "code", "name", "starts_on", "ends_on", "status")) for r in records]}


@router.post("/periodos", status_code=status.HTTP_201_CREATED)
def create_term(payload: TermCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    if payload.ends_on < payload.starts_on:
        raise HTTPException(status_code=422, detail="A data final do período deve ser posterior à data inicial")
    institution_id = _institution_id(user)
    record = AcademicTerm(id=uuid4().hex, institution_id=institution_id, **payload.model_dump())
    return {"module": "secretaria", "term": _model_dict(_save(db, record), ("id", "code", "name", "starts_on", "ends_on", "status"))}


@router.patch("/periodos/{term_id}")
def update_term(term_id: str, payload: TermUpdate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicTerm, term_id, institution_id, "Período letivo", user)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return {"module": "secretaria", "term": _model_dict(record, ("id", "code", "name", "starts_on", "ends_on", "status"))}
    if "starts_on" in data and "ends_on" in data and data["ends_on"] < data["starts_on"]:
        raise HTTPException(status_code=422, detail="A data final do período deve ser posterior à data inicial")
    if "starts_on" in data and "ends_on" not in data and record.ends_on < data["starts_on"]:
        raise HTTPException(status_code=422, detail="A data final do período deve ser posterior à data inicial")
    if "ends_on" in data and "starts_on" not in data and data["ends_on"] < record.starts_on:
        raise HTTPException(status_code=422, detail="A data final do período deve ser posterior à data inicial")
    for field, value in data.items():
        if value is not None:
            setattr(record, field, value)
    record = _save(db, record)
    return {"module": "secretaria", "term": _model_dict(record, ("id", "code", "name", "starts_on", "ends_on", "status"))}


@router.get("/matrizes")
def list_curricula(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(AcademicCurriculum).join(AcademicCourse).filter(AcademicCurriculum.institution_id == institution_id)
    if _user_campus_id(user):
        query = query.filter(or_(AcademicCourse.campus_id.is_(None), AcademicCourse.campus_id == _user_campus_id(user)))
    records = query.order_by(AcademicCurriculum.effective_from.desc()).all()
    items = []
    for record in records:
        links = db.query(AcademicCurriculumDiscipline).filter_by(curriculum_id=record.id).order_by(AcademicCurriculumDiscipline.term_number).all()
        link_ids = [link.id for link in links]
        equivalence_rows = (
            db.query(
                AcademicCurriculumEquivalence.curriculum_discipline_id,
                AcademicDiscipline.id,
                AcademicDiscipline.name,
            )
            .join(
                AcademicDiscipline,
                AcademicDiscipline.id == AcademicCurriculumEquivalence.equivalent_discipline_id,
            )
            .filter(AcademicCurriculumEquivalence.curriculum_discipline_id.in_(link_ids))
            .order_by(AcademicDiscipline.name)
            .all()
            if link_ids
            else []
        )
        equivalences_by_link: dict[str, list[dict[str, str]]] = {}
        for target_link_id, equivalent_id, equivalent_name in equivalence_rows:
            equivalences_by_link.setdefault(target_link_id, []).append({
                "discipline_id": equivalent_id,
                "discipline_name": equivalent_name,
            })
        prerequisite_rows = (
            db.query(
                AcademicCurriculumPrerequisite.curriculum_discipline_id,
                AcademicDiscipline.id,
                AcademicDiscipline.name,
            )
            .join(
                AcademicCurriculumDiscipline,
                AcademicCurriculumDiscipline.id
                == AcademicCurriculumPrerequisite.prerequisite_curriculum_discipline_id,
            )
            .join(AcademicDiscipline)
            .filter(AcademicCurriculumPrerequisite.curriculum_discipline_id.in_(link_ids))
            .all()
            if link_ids
            else []
        )
        elective_rows = (
            db.query(
                AcademicCurriculumElectiveDiscipline.curriculum_discipline_id,
                AcademicCurriculumElectiveGroup.id,
                AcademicCurriculumElectiveGroup.code,
                AcademicCurriculumElectiveGroup.name,
                AcademicCurriculumElectiveGroup.minimum_credits,
            )
            .join(
                AcademicCurriculumElectiveGroup,
                AcademicCurriculumElectiveGroup.id
                == AcademicCurriculumElectiveDiscipline.elective_group_id,
            )
            .filter(AcademicCurriculumElectiveGroup.curriculum_id == record.id)
            .all()
        )
        elective_groups_by_link: dict[str, dict[str, Any]] = {}
        elective_groups_by_id: dict[str, dict[str, Any]] = {}
        for link_id, group_id, code, name, minimum_credits in elective_rows:
            group = elective_groups_by_id.setdefault(group_id, {
                "id": group_id,
                "code": code,
                "name": name,
                "minimum_credits": minimum_credits,
                "discipline_ids": [],
            })
            elective_groups_by_link[link_id] = group
            group["discipline_ids"].append(
                next(link.discipline_id for link in links if link.id == link_id)
            )
        prerequisites_by_link: dict[str, list[dict[str, str]]] = {}
        for target_link_id, prerequisite_id, prerequisite_name in prerequisite_rows:
            prerequisites_by_link.setdefault(target_link_id, []).append({
                "discipline_id": prerequisite_id,
                "discipline_name": prerequisite_name,
            })
        items.append({
            **_model_dict(record, ("id", "course_id", "version", "effective_from", "status")),
            "disciplines": [
                {
                    **_model_dict(link, ("discipline_id", "term_number", "is_required")),
                    "prerequisites": prerequisites_by_link.get(link.id, []),
                    "equivalences": equivalences_by_link.get(link.id, []),
                    "elective_group": elective_groups_by_link.get(link.id),
                }
                for link in links
            ],
            "elective_groups": list(elective_groups_by_id.values()),
        })
    return {"module": "secretaria", "items": items}


@router.get("/alunos/{student_id}/progresso")
def get_student_curriculum_progress(
    student_id: str,
    course_id: str,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    student = db.query(models.Student).filter(
        models.Student.id == student_id,
        models.Student.institution_id == institution_id,
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    if _user_campus_id(user) and student.campus_id != _user_campus_id(user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    course = _get_scoped(db, AcademicCourse, course_id, institution_id, "Curso", user)

    curriculum = _resolve_student_curriculum(db, student, course, institution_id)

    passed_discipline_ids = {
        discipline_id
        for (discipline_id,) in (
            db.query(AcademicOffering.discipline_id)
            .join(AcademicClass, AcademicClass.offering_id == AcademicOffering.id)
            .join(
                models.Enrollment,
                models.Enrollment.academic_class_id == AcademicClass.id,
            )
            .filter(
                models.Enrollment.student_id == student.id,
                models.Enrollment.institution_id == institution_id,
                models.Enrollment.status == "completed",
                models.Enrollment.result == "passed",
                AcademicOffering.institution_id == institution_id,
                AcademicClass.institution_id == institution_id,
                AcademicOffering.course_id == course.id,
            )
            .distinct()
            .all()
        )
    }

    curriculum_links = (
        db.query(AcademicCurriculumDiscipline)
        .filter(AcademicCurriculumDiscipline.curriculum_id == curriculum.id)
        .all()
    )
    approved_recognitions = (
        db.query(AcademicCreditRecognition)
        .filter(
            AcademicCreditRecognition.student_id == student.id,
            AcademicCreditRecognition.institution_id == institution_id,
            AcademicCreditRecognition.course_id == course.id,
            AcademicCreditRecognition.status == "approved",
            AcademicCreditRecognition.curriculum_discipline_id.in_(
                [link.id for link in curriculum_links]
            ),
        )
        .all()
        if curriculum_links
        else []
    )
    recognition_by_link = {
        record.curriculum_discipline_id: record
        for record in approved_recognitions
    }
    required_links = [link for link in curriculum_links if link.is_required]
    required_link_ids = [link.id for link in required_links]
    equivalence_rows = (
        db.query(
            AcademicCurriculumEquivalence.curriculum_discipline_id,
            AcademicCurriculumEquivalence.equivalent_discipline_id,
        )
        .filter(AcademicCurriculumEquivalence.curriculum_discipline_id.in_(required_link_ids))
        .all()
        if required_link_ids
        else []
    )
    equivalents_by_link: dict[str, set[str]] = {}
    for link_id, equivalent_id in equivalence_rows:
        equivalents_by_link.setdefault(link_id, set()).add(equivalent_id)
    all_equivalent_ids = {
        equivalent_id
        for equivalent_ids in equivalents_by_link.values()
        for equivalent_id in equivalent_ids
    }
    passed_equivalence_ids = {
        discipline_id
        for (discipline_id,) in (
            db.query(AcademicOffering.discipline_id)
            .join(AcademicClass, AcademicClass.offering_id == AcademicOffering.id)
            .join(
                models.Enrollment,
                models.Enrollment.academic_class_id == AcademicClass.id,
            )
            .filter(
                models.Enrollment.student_id == student.id,
                models.Enrollment.institution_id == institution_id,
                models.Enrollment.status == "completed",
                models.Enrollment.result == "passed",
                AcademicOffering.institution_id == institution_id,
                AcademicClass.institution_id == institution_id,
                AcademicOffering.discipline_id.in_(all_equivalent_ids),
            )
            .distinct()
            .all()
        )
    } if all_equivalent_ids else set()

    required_items = []
    completed_required_credits = 0
    for link in required_links:
        recognition = recognition_by_link.get(link.id)
        satisfied = (
            recognition is not None
            or link.discipline_id in passed_discipline_ids
            or bool(equivalents_by_link.get(link.id, set()) & passed_equivalence_ids)
        )
        if satisfied:
            completed_required_credits += link.discipline.credits
        required_items.append({
            "discipline_id": link.discipline_id,
            "discipline_name": link.discipline.name,
            "credits": link.discipline.credits,
            "status": "completed" if satisfied else "pending",
            "fulfillment": (
                "approved_recognition"
                if recognition is not None
                else "completed_enrollment"
                if link.discipline_id in passed_discipline_ids
                else "equivalent_enrollment"
                if satisfied
                else None
            ),
            "recognition": (
                _credit_recognition_dict(recognition)
                if recognition is not None
                else None
            ),
        })

    groups = (
        db.query(AcademicCurriculumElectiveGroup)
        .filter(AcademicCurriculumElectiveGroup.curriculum_id == curriculum.id)
        .order_by(AcademicCurriculumElectiveGroup.code)
        .all()
    )
    elective_group_items = []
    completed_elective_credits = 0
    all_elective_groups_met = True
    for group in groups:
        elective_links = (
            db.query(AcademicCurriculumDiscipline)
            .join(
                AcademicCurriculumElectiveDiscipline,
                AcademicCurriculumElectiveDiscipline.curriculum_discipline_id
                == AcademicCurriculumDiscipline.id,
            )
            .filter(AcademicCurriculumElectiveDiscipline.elective_group_id == group.id)
            .all()
        )
        earned_disciplines = [
            {
                "discipline_id": link.discipline_id,
                "discipline_name": link.discipline.name,
                "credits": link.discipline.credits,
                "fulfillment": (
                    "approved_recognition"
                    if link.id in recognition_by_link
                    else "completed_enrollment"
                ),
                "recognition": (
                    _credit_recognition_dict(recognition_by_link[link.id])
                    if link.id in recognition_by_link
                    else None
                ),
            }
            for link in elective_links
            if link.discipline_id in passed_discipline_ids
            or link.id in recognition_by_link
        ]
        earned_credits = sum(item["credits"] for item in earned_disciplines)
        completed_elective_credits += earned_credits
        group_met = earned_credits >= group.minimum_credits
        all_elective_groups_met = all_elective_groups_met and group_met
        elective_group_items.append({
            "id": group.id,
            "code": group.code,
            "name": group.name,
            "minimum_credits": group.minimum_credits,
            "earned_credits": earned_credits,
            "status": "completed" if group_met else "pending",
            "completed_disciplines": earned_disciplines,
        })

    required_completed = all(item["status"] == "completed" for item in required_items)
    required_credits = sum(link.discipline.credits for link in required_links)
    total_required_credits = required_credits + sum(group.minimum_credits for group in groups)
    eligible_to_complete = required_completed and all_elective_groups_met
    return {
        "module": "secretaria",
        "student": {"id": student.id, "full_name": student.full_name},
        "course": {"id": course.id, "name": course.name},
        "curriculum": {
            "id": curriculum.id,
            "version": curriculum.version,
            "effective_from": curriculum.effective_from,
        },
        "required_disciplines": required_items,
        "elective_groups": elective_group_items,
        "credits": {
            "completed_required": completed_required_credits,
            "required": required_credits,
            "completed_elective": completed_elective_credits,
            "required_elective": sum(group.minimum_credits for group in groups),
            "completed_total": completed_required_credits + completed_elective_credits,
            "required_total": total_required_credits,
        },
        "eligible_to_complete": eligible_to_complete,
    }


@router.get("/alunos/{student_id}/historico")
def get_student_academic_history(
    student_id: str,
    course_id: str,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    student = db.query(models.Student).filter(
        models.Student.id == student_id,
        models.Student.institution_id == institution_id,
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    if _user_campus_id(user) and student.campus_id != _user_campus_id(user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    course = _get_scoped(db, AcademicCourse, course_id, institution_id, "Curso", user)
    curriculum = _resolve_student_curriculum(db, student, course, institution_id)

    enrollments = (
        db.query(models.Enrollment)
        .join(AcademicClass, AcademicClass.id == models.Enrollment.academic_class_id)
        .join(AcademicOffering, AcademicOffering.id == AcademicClass.offering_id)
        .filter(
            models.Enrollment.student_id == student.id,
            models.Enrollment.institution_id == institution_id,
            AcademicClass.institution_id == institution_id,
            AcademicOffering.institution_id == institution_id,
            AcademicOffering.course_id == course.id,
        )
        .all()
    )
    records: list[dict[str, Any]] = []
    history_teachers: dict[str, AcademicStaff] = {}
    unassigned_teacher_count = 0
    for enrollment in enrollments:
        offering = enrollment.academic_class.offering
        term = offering.term
        teacher = enrollment.academic_class.teacher
        if teacher is None:
            unassigned_teacher_count += 1
        else:
            history_teachers[teacher.id] = teacher
        records.append({
            "type": "enrollment",
            "discipline_id": offering.discipline_id,
            "discipline_name": offering.discipline.name,
            "period": term.name,
            "period_start": term.starts_on,
            "period_end": term.ends_on,
            "class_code": enrollment.academic_class.code,
            "workload_hours": offering.discipline.workload_hours,
            "credits": offering.discipline.credits,
            "enrollment_status": enrollment.status,
            "result": enrollment.result,
            "source": "Matrícula em turma",
            "decision_note": None,
            "reviewer_id": None,
            "recorded_at": enrollment.created_at,
        })

    curriculum_links = db.query(AcademicCurriculumDiscipline).filter(
        AcademicCurriculumDiscipline.curriculum_id == curriculum.id
    ).all()
    approved_recognitions = (
        db.query(AcademicCreditRecognition)
        .filter(
            AcademicCreditRecognition.student_id == student.id,
            AcademicCreditRecognition.institution_id == institution_id,
            AcademicCreditRecognition.course_id == course.id,
            AcademicCreditRecognition.status == "approved",
            AcademicCreditRecognition.curriculum_discipline_id.in_(
                [link.id for link in curriculum_links]
            ),
        )
        .all()
        if curriculum_links
        else []
    )
    for recognition in approved_recognitions:
        target = recognition.curriculum_discipline.discipline
        records.append({
            "type": "credit_recognition",
            "discipline_id": target.id,
            "discipline_name": target.name,
            "period": None,
            "period_start": None,
            "period_end": None,
            "class_code": None,
            "workload_hours": recognition.workload_hours,
            "credits": target.credits,
            "enrollment_status": "recognized",
            "result": "approved",
            "source": (
                f"{recognition.source_discipline} — {recognition.source_course}, "
                f"{recognition.source_institution}"
            ),
            "decision_note": recognition.decision_note,
            "reviewer_id": recognition.reviewer_id,
            "recorded_at": recognition.decided_at,
        })

    records.sort(
        key=lambda item: (
            item["period_start"] or date.min,
            item["recorded_at"] or datetime.min,
            item["discipline_name"],
        )
    )
    pending_requests = (
        db.query(AcademicCreditRecognition)
        .filter(
            AcademicCreditRecognition.student_id == student.id,
            AcademicCreditRecognition.institution_id == institution_id,
            AcademicCreditRecognition.course_id == course.id,
            AcademicCreditRecognition.status == "pending",
            AcademicCreditRecognition.curriculum_discipline_id.in_(
                [link.id for link in curriculum_links]
            ),
        )
        .all()
        if curriculum_links
        else []
    )
    institution_profile = db.query(InstitutionTranscriptProfile).filter(
        InstitutionTranscriptProfile.institution_id == institution_id
    ).first()
    course_profile = db.query(CourseTranscriptProfile).filter(
        CourseTranscriptProfile.institution_id == institution_id,
        CourseTranscriptProfile.course_id == course.id,
    ).first()
    student_course_profile = db.query(StudentCourseTranscriptProfile).filter(
        StudentCourseTranscriptProfile.institution_id == institution_id,
        StudentCourseTranscriptProfile.student_id == student.id,
        StudentCourseTranscriptProfile.course_id == course.id,
    ).first()
    student_identity = {
        "Nome": student.full_name,
        "Nome social": student.social_name,
        "Sexo": student.sex,
        "Nacionalidade": student.nationality,
        "Código IBGE de naturalidade": student.birthplace_municipality_code,
        "Município de naturalidade": student.birthplace_municipality_name,
        "UF de naturalidade": student.birthplace_state,
        "CPF": student.cpf,
        "Data de nascimento": student.birth_date,
        "Número do RG": student.rg_number,
        "Órgão expedidor do RG": student.rg_issuing_authority,
        "UF do RG": student.rg_state,
    }
    missing_identity_fields = [
        label
        for label, value in student_identity.items()
        if not value or not str(value).strip()
    ]
    missing_teacher_title_count = sum(
        not teacher.transcript_title for teacher in history_teachers.values()
    )
    return {
        "module": "secretaria",
        "student": {"id": student.id, "full_name": student.full_name},
        "course": {"id": course.id, "name": course.name},
        "curriculum": {"id": curriculum.id, "version": curriculum.version},
        "records": records,
        "pending_recognitions": [
            {
                "id": record.id,
                "discipline_name": record.curriculum_discipline.discipline.name,
                "source_discipline": record.source_discipline,
                "requested_at": record.requested_at,
            }
            for record in pending_requests
        ],
        "official_document_issued": False,
        "official_history_blockers": [
            *(
                [f"Dados pessoais pendentes: {', '.join(missing_identity_fields)}"]
                if missing_identity_fields
                else []
            ),
            *(
                ["Perfil regulatório da IES não cadastrado."]
                if institution_profile is None
                else []
            ),
            *(
                ["Perfil regulatório do curso não cadastrado."]
                if course_profile is None
                else []
            ),
            "A validação contra o leiaute MEC v1.05 está disponível, mas a geração ainda não está integrada aos registros acadêmicos.",
            *(
                ["Forma de acesso e data de ingresso do aluno no curso ainda não estão cadastradas."]
                if student_course_profile is None
                else []
            ),
            "A carga horária em hora-aula e a duração da hora-aula ainda não estão configuradas.",
            *(
                [
                    f"{unassigned_teacher_count} disciplina(s) sem docente vinculado para o histórico."
                ]
                if unassigned_teacher_count
                else []
            ),
            *(
                [
                    f"Titulação pendente para {missing_teacher_title_count} docente(s) vinculado(s) ao histórico."
                ]
                if missing_teacher_title_count
                else []
            ),
            *(
                [
                    "Aproveitamentos deferidos não possuem docentes da instituição de origem vinculados."
                ]
                if approved_recognitions
                else []
            ),
            "O leiaute MEC exige assinatura digital; a emissão assinada permanece pendente.",
        ],
        "official_history_profiles": {
            "institution_configured": institution_profile is not None,
            "course_configured": course_profile is not None,
            "student_entry_configured": student_course_profile is not None,
            "teachers_linked": len(history_teachers),
            "teachers_without_title": missing_teacher_title_count,
            "disciplines_without_teacher": unassigned_teacher_count,
        },
    }


@router.get("/alunos/{student_id}/cursos/{course_id}/dados-ingresso-historico")
def get_student_course_transcript_profile(
    student_id: str,
    course_id: str,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    student = db.query(models.Student).filter(
        models.Student.id == student_id,
        models.Student.institution_id == institution_id,
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    if _user_campus_id(user) and student.campus_id != _user_campus_id(user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    course = _get_scoped(db, AcademicCourse, course_id, institution_id, "Curso", user)
    record = db.query(StudentCourseTranscriptProfile).filter(
        StudentCourseTranscriptProfile.institution_id == institution_id,
        StudentCourseTranscriptProfile.student_id == student.id,
        StudentCourseTranscriptProfile.course_id == course.id,
    ).first()
    return {
        "configured": record is not None,
        "student_id": student.id,
        "course_id": course.id,
        "entry_date": record.entry_date if record else None,
        "access_form": record.access_form if record else None,
    }


@router.put("/alunos/{student_id}/cursos/{course_id}/dados-ingresso-historico")
def save_student_course_transcript_profile(
    student_id: str,
    course_id: str,
    payload: StudentCourseTranscriptProfileUpdate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    student = db.query(models.Student).filter(
        models.Student.id == student_id,
        models.Student.institution_id == institution_id,
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    if _user_campus_id(user) and student.campus_id != _user_campus_id(user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    course = _get_scoped(db, AcademicCourse, course_id, institution_id, "Curso", user)
    record = db.query(StudentCourseTranscriptProfile).filter(
        StudentCourseTranscriptProfile.institution_id == institution_id,
        StudentCourseTranscriptProfile.student_id == student.id,
        StudentCourseTranscriptProfile.course_id == course.id,
    ).first()
    if record is None:
        record = StudentCourseTranscriptProfile(
            id=uuid4().hex,
            institution_id=institution_id,
            student_id=student.id,
            course_id=course.id,
            entry_date=payload.entry_date,
            access_form=payload.access_form,
        )
        db.add(record)
        action = "transcript_entry_profile_created"
    else:
        record.entry_date = payload.entry_date
        record.access_form = payload.access_form
        action = "transcript_entry_profile_updated"
    from app.main import add_audit
    add_audit(
        db,
        "student",
        student.id,
        action,
        f"Course transcript admission fields updated for course {course.id}",
        str(getattr(user, "id", None) or "") or None,
    )
    db.commit()
    db.refresh(record)
    return {
        "configured": True,
        "student_id": student.id,
        "course_id": course.id,
        "entry_date": record.entry_date,
        "access_form": record.access_form,
    }


@router.patch("/alunos/{student_id}/dados-historico")
def update_student_transcript_identity(
    student_id: str,
    payload: StudentTranscriptIdentityUpdate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    student = db.query(models.Student).filter(
        models.Student.id == student_id,
        models.Student.institution_id == institution_id,
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    if _user_campus_id(user) and student.campus_id != _user_campus_id(user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Informe ao menos um dado para atualizar")
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(student, field, value)
    from app.main import add_audit
    add_audit(
        db,
        "student",
        student.id,
        "transcript_identity_updated",
        f"Student transcript identity fields updated: {', '.join(sorted(changes))}",
        str(getattr(user, "id", None) or "") or None,
    )
    db.commit()
    db.refresh(student)
    return {
        "student_id": student.id,
        **{
            field: getattr(student, field)
            for field in StudentTranscriptIdentityUpdate.model_fields
        },
    }


@router.get("/aproveitamentos")
def list_credit_recognitions(
    student_id: str | None = None,
    recognition_status: Literal["pending", "approved", "rejected"] | None = None,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    query = db.query(AcademicCreditRecognition).filter(
        AcademicCreditRecognition.institution_id == institution_id
    )
    if student_id:
        query = query.filter(AcademicCreditRecognition.student_id == student_id)
    if recognition_status:
        query = query.filter(AcademicCreditRecognition.status == recognition_status)
    if _user_campus_id(user):
        query = query.join(
            models.Student,
            models.Student.id == AcademicCreditRecognition.student_id,
        ).filter(models.Student.campus_id == _user_campus_id(user))

    items = []
    for record in query.order_by(AcademicCreditRecognition.requested_at.desc()).all():
        item = _credit_recognition_dict(record)
        item.update({
            "student_id": record.student_id,
            "student_name": record.student.full_name,
            "course_id": record.course_id,
            "course_name": record.course.name,
            "curriculum_id": record.curriculum_discipline.curriculum_id,
            "discipline_id": record.curriculum_discipline.discipline_id,
            "reviewer_id": record.reviewer_id,
        })
        items.append(item)
    return {"module": "secretaria", "items": items}


@router.post(
    "/alunos/{student_id}/aproveitamentos",
    status_code=status.HTTP_201_CREATED,
)
def create_credit_recognition(
    student_id: str,
    payload: CreditRecognitionCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    student = db.query(models.Student).filter(
        models.Student.id == student_id,
        models.Student.institution_id == institution_id,
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    if _user_campus_id(user) and student.campus_id != _user_campus_id(user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    course = _get_scoped(db, AcademicCourse, payload.course_id, institution_id, "Curso", user)
    curriculum = _resolve_student_curriculum(db, student, course, institution_id)
    if curriculum.id != payload.curriculum_id:
        raise HTTPException(
            status_code=409,
            detail="A matriz selecionada não é a matriz curricular aplicável ao aluno",
        )
    curriculum_link = db.query(AcademicCurriculumDiscipline).filter(
        AcademicCurriculumDiscipline.curriculum_id == curriculum.id,
        AcademicCurriculumDiscipline.discipline_id == payload.discipline_id,
    ).first()
    if curriculum_link is None:
        raise HTTPException(
            status_code=404,
            detail="A disciplina de destino não pertence à matriz curricular do aluno",
        )
    existing_request = db.query(AcademicCreditRecognition).filter(
        AcademicCreditRecognition.student_id == student.id,
        AcademicCreditRecognition.course_id == course.id,
        AcademicCreditRecognition.curriculum_discipline_id == curriculum_link.id,
        AcademicCreditRecognition.status.in_(("pending", "approved")),
    ).first()
    if existing_request:
        raise HTTPException(
            status_code=409,
            detail="Já existe solicitação pendente ou aprovada para esta disciplina",
        )
    record = AcademicCreditRecognition(
        id=uuid4().hex,
        institution_id=institution_id,
        student_id=student.id,
        course_id=course.id,
        curriculum_discipline_id=curriculum_link.id,
        source_institution=payload.source_institution,
        source_course=payload.source_course,
        source_discipline=payload.source_discipline,
        workload_hours=payload.workload_hours,
        credits=payload.credits,
        request_note=payload.request_note,
        status="pending",
    )
    db.add(record)
    _save(db, record)
    item = _credit_recognition_dict(record)
    item.update({
        "student_id": student.id,
        "student_name": student.full_name,
        "course_id": course.id,
        "course_name": course.name,
        "curriculum_id": curriculum.id,
        "discipline_id": curriculum_link.discipline_id,
        "reviewer_id": record.reviewer_id,
    })
    return {"recognition": item}


@router.patch("/aproveitamentos/{recognition_id}/decisao")
def decide_credit_recognition(
    recognition_id: str,
    payload: CreditRecognitionDecision,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    record = db.query(AcademicCreditRecognition).filter(
        AcademicCreditRecognition.id == recognition_id,
        AcademicCreditRecognition.institution_id == institution_id,
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Solicitação de aproveitamento não encontrada")
    if _user_campus_id(user) and record.student.campus_id != _user_campus_id(user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao campus vinculado ao usuário")
    if record.status != "pending":
        raise HTTPException(status_code=409, detail="A solicitação já recebeu uma decisão")
    if payload.status == "rejected" and not (payload.decision_note or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Informe o motivo da rejeição",
        )
    record.status = payload.status
    record.decision_note = (payload.decision_note or "").strip() or None
    record.reviewer_id = str(getattr(user, "id", None) or getattr(user, "username", ""))
    record.decided_at = datetime.now(UTC).replace(tzinfo=None)
    _save(db, record)
    return {"recognition": _credit_recognition_dict(record)}


@router.post("/matrizes", status_code=status.HTTP_201_CREATED)
def create_curriculum(payload: CurriculumCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    course = _get_scoped(db, AcademicCourse, payload.course_id, institution_id, "Curso", user)
    discipline_ids = {item.discipline_id for item in payload.disciplines}
    disciplines = db.query(AcademicDiscipline).filter(
        AcademicDiscipline.institution_id == institution_id,
        AcademicDiscipline.id.in_(discipline_ids),
    ).all()
    if len(disciplines) != len(discipline_ids):
        raise HTTPException(status_code=404, detail="Uma ou mais disciplinas não existem nesta instituição")
    curriculum_items = {item.discipline_id: item for item in payload.disciplines}
    if len(curriculum_items) != len(payload.disciplines):
        raise HTTPException(status_code=422, detail="A matriz contém disciplinas duplicadas")
    for item in payload.disciplines:
        if len(set(item.prerequisite_discipline_ids)) != len(item.prerequisite_discipline_ids):
            raise HTTPException(status_code=422, detail="Pré-requisitos duplicados na disciplina")
        for prerequisite_id in item.prerequisite_discipline_ids:
            prerequisite = curriculum_items.get(prerequisite_id)
            if prerequisite is None:
                raise HTTPException(
                    status_code=422,
                    detail="Pré-requisitos devem pertencer à mesma matriz curricular",
                )
            if prerequisite_id == item.discipline_id:
                raise HTTPException(status_code=422, detail="Uma disciplina não pode ser pré-requisito dela mesma")
            if prerequisite.term_number >= item.term_number:
                raise HTTPException(
                    status_code=422,
                    detail="O pré-requisito deve estar em um período anterior da matriz",
                )
    curriculum = AcademicCurriculum(
        id=uuid4().hex,
        institution_id=institution_id,
        course_id=course.id,
        version=payload.version,
        effective_from=payload.effective_from,
        status=payload.status,
    )
    try:
        db.add(curriculum)
        db.flush()
        curriculum_links: dict[str, AcademicCurriculumDiscipline] = {}
        for item in payload.disciplines:
            link = AcademicCurriculumDiscipline(
                id=uuid4().hex,
                curriculum_id=curriculum.id,
                discipline_id=item.discipline_id,
                term_number=item.term_number,
                is_required=item.is_required,
            )
            db.add(link)
            curriculum_links[item.discipline_id] = link
        db.flush()
        for item in payload.disciplines:
            for prerequisite_id in item.prerequisite_discipline_ids:
                db.add(AcademicCurriculumPrerequisite(
                    id=uuid4().hex,
                    curriculum_discipline_id=curriculum_links[item.discipline_id].id,
                    prerequisite_curriculum_discipline_id=curriculum_links[prerequisite_id].id,
                ))
        db.commit()
        db.refresh(curriculum)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe esta versão da matriz curricular") from exc
    return {"module": "secretaria", "curriculum": _model_dict(curriculum, ("id", "course_id", "version", "effective_from", "status"))}


@router.post(
    "/matrizes/{curriculum_id}/disciplinas/{discipline_id}/pre-requisitos",
    status_code=status.HTTP_201_CREATED,
)
def add_curriculum_prerequisite(
    curriculum_id: str,
    discipline_id: str,
    payload: CurriculumPrerequisiteCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    curriculum = _get_scoped(db, AcademicCurriculum, curriculum_id, institution_id, "Matriz curricular", user)
    target = (
        db.query(AcademicCurriculumDiscipline)
        .filter_by(curriculum_id=curriculum.id, discipline_id=discipline_id)
        .first()
    )
    prerequisite = (
        db.query(AcademicCurriculumDiscipline)
        .filter_by(curriculum_id=curriculum.id, discipline_id=payload.prerequisite_discipline_id)
        .first()
    )
    if target is None or prerequisite is None:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada nesta matriz curricular")
    if target.id == prerequisite.id:
        raise HTTPException(status_code=422, detail="Uma disciplina não pode ser pré-requisito dela mesma")
    if prerequisite.term_number >= target.term_number:
        raise HTTPException(
            status_code=422,
            detail="O pré-requisito deve estar em um período anterior da matriz",
        )
    record = AcademicCurriculumPrerequisite(
        id=uuid4().hex,
        curriculum_discipline_id=target.id,
        prerequisite_curriculum_discipline_id=prerequisite.id,
    )
    try:
        db.add(record)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Este pré-requisito já está cadastrado") from exc
    return {
        "module": "secretaria",
        "prerequisite": {
            "discipline_id": payload.prerequisite_discipline_id,
            "discipline_name": prerequisite.discipline.name,
        },
    }


@router.post(
    "/matrizes/{curriculum_id}/disciplinas/{discipline_id}/equivalencias",
    status_code=status.HTTP_201_CREATED,
)
def add_curriculum_equivalence(
    curriculum_id: str,
    discipline_id: str,
    payload: CurriculumEquivalenceCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    curriculum = _get_scoped(
        db, AcademicCurriculum, curriculum_id, institution_id, "Matriz curricular", user
    )
    target = (
        db.query(AcademicCurriculumDiscipline)
        .filter_by(curriculum_id=curriculum.id, discipline_id=discipline_id)
        .first()
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada nesta matriz curricular")
    if not target.is_required:
        raise HTTPException(
            status_code=409,
            detail="Equivalências só podem ser vinculadas a disciplinas obrigatórias",
        )
    equivalent = _get_scoped(
        db,
        AcademicDiscipline,
        payload.equivalent_discipline_id,
        institution_id,
        "Disciplina equivalente",
        user,
    )
    if equivalent.id == target.discipline_id:
        raise HTTPException(status_code=422, detail="Uma disciplina não pode ser equivalente a ela mesma")
    record = AcademicCurriculumEquivalence(
        id=uuid4().hex,
        curriculum_discipline_id=target.id,
        equivalent_discipline_id=equivalent.id,
    )
    try:
        db.add(record)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Esta equivalência já está cadastrada") from exc
    return {
        "module": "secretaria",
        "equivalence": {
            "discipline_id": equivalent.id,
            "discipline_name": equivalent.name,
        },
    }


@router.post(
    "/matrizes/{curriculum_id}/optativas",
    status_code=status.HTTP_201_CREATED,
)
def create_curriculum_elective_group(
    curriculum_id: str,
    payload: CurriculumElectiveGroupCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    curriculum = _get_scoped(
        db, AcademicCurriculum, curriculum_id, institution_id, "Matriz curricular", user
    )
    discipline_ids = set(payload.discipline_ids)
    if len(discipline_ids) != len(payload.discipline_ids):
        raise HTTPException(status_code=422, detail="A lista de disciplinas optativas contém duplicatas")
    links = (
        db.query(AcademicCurriculumDiscipline)
        .join(AcademicDiscipline)
        .filter(
            AcademicCurriculumDiscipline.curriculum_id == curriculum.id,
            AcademicCurriculumDiscipline.discipline_id.in_(discipline_ids),
        )
        .all()
    )
    if len(links) != len(discipline_ids):
        raise HTTPException(
            status_code=422,
            detail="Todas as disciplinas optativas devem pertencer à mesma matriz curricular",
        )
    if any(link.is_required for link in links):
        raise HTTPException(
            status_code=422,
            detail="O grupo optativo pode conter somente disciplinas marcadas como não obrigatórias",
        )
    assigned_ids = {
        link_id
        for (link_id,) in db.query(
            AcademicCurriculumElectiveDiscipline.curriculum_discipline_id
        )
        .filter(AcademicCurriculumElectiveDiscipline.curriculum_discipline_id.in_(
            [link.id for link in links]
        ))
        .all()
    }
    if assigned_ids:
        raise HTTPException(
            status_code=409,
            detail="Uma ou mais disciplinas já pertencem a um grupo optativo",
        )
    available_credits = sum(link.discipline.credits for link in links)
    if available_credits < payload.minimum_credits:
        raise HTTPException(
            status_code=422,
            detail="A soma dos créditos optativos disponíveis é inferior ao mínimo exigido",
        )
    group = AcademicCurriculumElectiveGroup(
        id=uuid4().hex,
        curriculum_id=curriculum.id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        minimum_credits=payload.minimum_credits,
    )
    try:
        db.add(group)
        db.flush()
        db.add_all([
            AcademicCurriculumElectiveDiscipline(
                id=uuid4().hex,
                elective_group_id=group.id,
                curriculum_discipline_id=link.id,
            )
            for link in links
        ])
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Grupo optativo duplicado ou inválido") from exc
    return {
        "module": "secretaria",
        "elective_group": {
            "id": group.id,
            "code": group.code,
            "name": group.name,
            "minimum_credits": group.minimum_credits,
            "discipline_ids": sorted(discipline_ids),
        },
    }


@router.post("/matrizes/{curriculum_id}/disciplinas", status_code=status.HTTP_201_CREATED)
def add_curriculum_discipline(
    curriculum_id: str,
    payload: CurriculumDisciplineCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    curriculum = _get_scoped(db, AcademicCurriculum, curriculum_id, institution_id, "Matriz curricular", user)
    _get_scoped(db, AcademicDiscipline, payload.discipline_id, institution_id, "Disciplina", user)
    if len(set(payload.prerequisite_discipline_ids)) != len(payload.prerequisite_discipline_ids):
        raise HTTPException(status_code=422, detail="Pré-requisitos duplicados na disciplina")
    prerequisites = []
    for prerequisite_id in payload.prerequisite_discipline_ids:
        prerequisite = (
            db.query(AcademicCurriculumDiscipline)
            .filter_by(curriculum_id=curriculum.id, discipline_id=prerequisite_id)
            .first()
        )
        if prerequisite is None:
            raise HTTPException(
                status_code=422,
                detail="Pré-requisitos devem pertencer à mesma matriz curricular",
            )
        if prerequisite.term_number >= payload.term_number:
            raise HTTPException(
                status_code=422,
                detail="O pré-requisito deve estar em um período anterior da matriz",
            )
        prerequisites.append(prerequisite)
    link = AcademicCurriculumDiscipline(
        id=uuid4().hex,
        curriculum_id=curriculum.id,
        discipline_id=payload.discipline_id,
        term_number=payload.term_number,
        is_required=payload.is_required,
    )
    try:
        db.add(link)
        db.flush()
        db.add_all([
            AcademicCurriculumPrerequisite(
                id=uuid4().hex,
                curriculum_discipline_id=link.id,
                prerequisite_curriculum_discipline_id=prerequisite.id,
            )
            for prerequisite in prerequisites
        ])
        db.commit()
        db.refresh(link)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Disciplina já cadastrada nesta matriz curricular") from exc
    return {"module": "secretaria", "item": _model_dict(link, ("id", "curriculum_id", "discipline_id", "term_number", "is_required"))}


@router.get("/profissionais")
def list_staff(
    staff_type: Literal["professor", "coordenador", "tutor"] | None = None,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    query = db.query(AcademicStaff).filter_by(institution_id=institution_id)
    if _user_campus_id(user):
        query = query.filter(or_(AcademicStaff.campus_id.is_(None), AcademicStaff.campus_id == _user_campus_id(user)))
    if staff_type:
        query = query.filter(AcademicStaff.staff_type == staff_type)
    records = query.order_by(AcademicStaff.full_name).all()
    return {"module": "secretaria", "items": [_model_dict(r, ("id", "campus_id", "user_id", "staff_code", "full_name", "email", "staff_type", "status")) for r in records]}


@router.get("/usuarios-vinculaveis")
def list_linkable_staff_users(
    staff_id: str | None = None,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    current_staff = None
    if staff_id:
        current_staff = _get_scoped(db, AcademicStaff, staff_id, institution_id, "Profissional acadêmico", user)
    query = db.query(models.User).filter(
        models.User.institution_id == institution_id,
        models.User.role == "academico",
        models.User.is_active.is_(True),
    )
    campus_id = _user_campus_id(user)
    if campus_id:
        query = query.filter(or_(models.User.campus_id.is_(None), models.User.campus_id == campus_id))
    linked_user_ids = db.query(AcademicStaff.user_id).filter(
        AcademicStaff.user_id.is_not(None),
        AcademicStaff.id != (current_staff.id if current_staff else ""),
    )
    records = query.filter(
        or_(
            models.User.id.not_in(linked_user_ids),
            models.User.id == (current_staff.user_id if current_staff else ""),
        )
    ).order_by(models.User.username).all()
    return {
        "module": "secretaria",
        "items": [{"id": record.id, "username": record.username} for record in records],
    }


@router.post("/profissionais", status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    values = payload.model_dump()
    values["campus_id"] = values["campus_id"] or _user_campus_id(user)
    _check_campus(db, values["campus_id"], institution_id, user)
    _validate_staff_user(
        db,
        values["user_id"],
        values["staff_type"],
        institution_id,
        values["campus_id"],
    )
    record = AcademicStaff(id=uuid4().hex, institution_id=institution_id, **values)
    _audit_catalog_change(
        db,
        user,
        "academic_staff",
        record.id,
        "academic_staff_created",
        {"changed_fields": sorted(values)},
    )
    return {"module": "secretaria", "staff": _model_dict(_save(db, record), ("id", "campus_id", "user_id", "staff_code", "full_name", "email", "staff_type", "status"))}


@router.patch("/profissionais/{staff_id}")
def update_staff(staff_id: str, payload: StaffUpdate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicStaff, staff_id, institution_id, "Profissional acadêmico", user)
    data = payload.model_dump(exclude_unset=True)
    if "campus_id" in data:
        _check_campus(db, data["campus_id"], institution_id, user)
    target_staff_type = data.get("staff_type", record.staff_type)
    target_user_id = data.get("user_id", record.user_id)
    target_campus_id = data.get("campus_id", record.campus_id)
    if "user_id" in data or "staff_type" in data or "campus_id" in data:
        _validate_staff_user(
            db,
            target_user_id,
            target_staff_type,
            institution_id,
            target_campus_id,
            record.id,
        )
    if not data:
        return {"module": "secretaria", "staff": _model_dict(record, ("id", "campus_id", "user_id", "staff_code", "full_name", "email", "staff_type", "status"))}
    changes = {
        field: value
        for field, value in data.items()
        if (field == "user_id" or value is not None) and getattr(record, field) != value
    }
    if not changes:
        return {"module": "secretaria", "staff": _model_dict(record, ("id", "campus_id", "user_id", "staff_code", "full_name", "email", "staff_type", "status"))}
    for field, value in changes.items():
        setattr(record, field, value)
    _audit_catalog_change(
        db,
        user,
        "academic_staff",
        record.id,
        "academic_staff_updated",
        {"changed_fields": sorted(changes)},
    )
    record = _save(db, record)
    return {"module": "secretaria", "staff": _model_dict(record, ("id", "campus_id", "user_id", "staff_code", "full_name", "email", "staff_type", "status"))}


@router.get("/profissionais/{staff_id}/dados-historico")
def get_staff_transcript_profile(
    staff_id: str,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicStaff, staff_id, institution_id, "Profissional acadêmico", user)
    if record.staff_type != "professor":
        raise HTTPException(status_code=409, detail="Apenas docentes podem receber dados para o histórico escolar")
    return {
        "configured": bool(record.transcript_title),
        "staff_id": record.id,
        "titulacao": record.transcript_title,
        "cpf_configured": bool(record.transcript_cpf),
        "lattes_configured": bool(record.transcript_lattes),
    }


@router.put("/profissionais/{staff_id}/dados-historico")
def save_staff_transcript_profile(
    staff_id: str,
    payload: StaffTranscriptProfileUpdate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicStaff, staff_id, institution_id, "Profissional acadêmico", user)
    if record.staff_type != "professor":
        raise HTTPException(status_code=409, detail="Apenas docentes podem receber dados para o histórico escolar")
    fields = payload.model_dump(exclude_unset=True)
    record.transcript_title = fields["titulacao"]
    if "cpf" in fields:
        record.transcript_cpf = fields["cpf"]
    if "lattes" in fields:
        record.transcript_lattes = fields["lattes"]
    from app.main import add_audit
    add_audit(
        db,
        "academic_staff",
        record.id,
        "transcript_profile_updated",
        "Faculty transcript qualification fields updated",
        str(getattr(user, "id", None) or "") or None,
    )
    db.commit()
    db.refresh(record)
    return {
        "configured": bool(record.transcript_title),
        "staff_id": record.id,
        "titulacao": record.transcript_title,
        "cpf_configured": bool(record.transcript_cpf),
        "lattes_configured": bool(record.transcript_lattes),
    }


def _validate_coordinator_assignment(
    db: Session,
    user: Any,
    institution_id: str,
    coordinator_id: str,
    course_id: str,
    campus_id: str,
    starts_on: date,
    ends_on: date,
    exclude_assignment_id: str | None = None,
) -> tuple[AcademicStaff, AcademicCourse]:
    if ends_on < starts_on:
        raise HTTPException(
            status_code=422,
            detail="O fim da responsabilidade deve ser posterior ou igual ao início",
        )
    coordinator = _get_scoped(
        db,
        AcademicStaff,
        coordinator_id,
        institution_id,
        "Coordenador",
        user,
    )
    course = _get_scoped(db, AcademicCourse, course_id, institution_id, "Curso", user)
    _check_campus(db, campus_id, institution_id, user)
    if coordinator.staff_type != "coordenador":
        raise HTTPException(status_code=422, detail="O profissional informado não está cadastrado como coordenador")
    if coordinator.status != "ativo":
        raise HTTPException(status_code=422, detail="O coordenador informado está inativo")
    if coordinator.campus_id and coordinator.campus_id != campus_id:
        raise HTTPException(status_code=422, detail="O coordenador está vinculado a outro campus")
    if course.campus_id and course.campus_id != campus_id:
        raise HTTPException(status_code=422, detail="O campus não corresponde ao campus ofertante do curso")

    overlapping = db.query(AcademicCoordinatorAssignment).filter(
        AcademicCoordinatorAssignment.institution_id == institution_id,
        AcademicCoordinatorAssignment.course_id == course_id,
        AcademicCoordinatorAssignment.campus_id == campus_id,
        AcademicCoordinatorAssignment.starts_on <= ends_on,
        AcademicCoordinatorAssignment.ends_on >= starts_on,
    )
    if exclude_assignment_id:
        overlapping = overlapping.filter(
            AcademicCoordinatorAssignment.id != exclude_assignment_id
        )
    if overlapping.first():
        raise HTTPException(
            status_code=409,
            detail="Já existe uma responsabilidade de coordenação sobreposta para este curso e campus",
        )
    return coordinator, course


@router.get("/responsabilidades-coordenacao")
def list_coordinator_assignments(
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    query = db.query(AcademicCoordinatorAssignment).filter_by(
        institution_id=institution_id
    )
    if _user_campus_id(user):
        query = query.filter(
            AcademicCoordinatorAssignment.campus_id == _user_campus_id(user)
        )
    records = query.order_by(
        AcademicCoordinatorAssignment.starts_on.desc(),
        AcademicCoordinatorAssignment.id,
    ).all()
    return {
        "module": "secretaria",
        "items": [
            {
                **_model_dict(
                    record,
                    ("id", "coordinator_id", "course_id", "campus_id", "starts_on", "ends_on"),
                ),
                "coordinator_name": record.coordinator.full_name,
                "course_name": record.course.name,
                "campus_name": record.campus.name,
            }
            for record in records
        ],
    }


@router.post(
    "/responsabilidades-coordenacao",
    status_code=status.HTTP_201_CREATED,
)
def create_coordinator_assignment(
    payload: CoordinatorAssignmentCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    _validate_coordinator_assignment(
        db,
        user,
        institution_id,
        payload.coordinator_id,
        payload.course_id,
        payload.campus_id,
        payload.starts_on,
        payload.ends_on,
    )
    record = AcademicCoordinatorAssignment(
        id=uuid4().hex,
        institution_id=institution_id,
        **payload.model_dump(),
    )
    _audit_catalog_change(
        db,
        user,
        "academic_coordinator_assignment",
        record.id,
        "academic_coordinator_assignment_created",
        payload.model_dump(mode="json"),
    )
    saved = _save(db, record)
    return {
        "module": "secretaria",
        "assignment": _model_dict(
            saved,
            ("id", "coordinator_id", "course_id", "campus_id", "starts_on", "ends_on"),
        ),
    }


@router.patch("/responsabilidades-coordenacao/{assignment_id}")
def update_coordinator_assignment(
    assignment_id: str,
    payload: CoordinatorAssignmentUpdate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    record = _get_scoped(
        db,
        AcademicCoordinatorAssignment,
        assignment_id,
        institution_id,
        "Responsabilidade de coordenação",
        user,
    )
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return {
            "module": "secretaria",
            "assignment": _model_dict(
                record,
                ("id", "coordinator_id", "course_id", "campus_id", "starts_on", "ends_on"),
            ),
        }
    if any(value is None for value in data.values()):
        raise HTTPException(status_code=422, detail="Os dados da responsabilidade não podem ser nulos")

    proposed = {
        field: data.get(field, getattr(record, field))
        for field in ("coordinator_id", "course_id", "campus_id", "starts_on", "ends_on")
    }
    _validate_coordinator_assignment(
        db,
        user,
        institution_id,
        **proposed,
        exclude_assignment_id=record.id,
    )
    changes = {
        field: {"before": getattr(record, field), "after": value}
        for field, value in data.items()
        if getattr(record, field) != value
    }
    if not changes:
        return {
            "module": "secretaria",
            "assignment": _model_dict(
                record,
                ("id", "coordinator_id", "course_id", "campus_id", "starts_on", "ends_on"),
            ),
        }
    for field, value in data.items():
        setattr(record, field, value)
    _audit_catalog_change(
        db,
        user,
        "academic_coordinator_assignment",
        record.id,
        "academic_coordinator_assignment_updated",
        changes,
    )
    saved = _save(db, record)
    return {
        "module": "secretaria",
        "assignment": _model_dict(
            saved,
            ("id", "coordinator_id", "course_id", "campus_id", "starts_on", "ends_on"),
        ),
    }


@router.get("/salas")
def list_rooms(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(AcademicRoom).filter_by(institution_id=institution_id)
    if _user_campus_id(user):
        query = query.filter(AcademicRoom.campus_id == _user_campus_id(user))
    records = query.order_by(AcademicRoom.code).all()
    return {"module": "secretaria", "items": [_model_dict(r, ("id", "campus_id", "code", "name", "capacity", "room_type", "is_active")) for r in records]}


@router.post("/salas", status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    _check_campus(db, payload.campus_id, institution_id, user)
    record = AcademicRoom(id=uuid4().hex, institution_id=institution_id, **payload.model_dump())
    return {"module": "secretaria", "room": _model_dict(_save(db, record), ("id", "campus_id", "code", "name", "capacity", "room_type", "is_active"))}


@router.patch("/salas/{room_id}")
def update_room(room_id: str, payload: RoomUpdate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicRoom, room_id, institution_id, "Sala", user)
    data = payload.model_dump(exclude_unset=True)
    if "campus_id" in data:
        _check_campus(db, data["campus_id"], institution_id, user)
    if not data:
        return {"module": "secretaria", "room": _model_dict(record, ("id", "campus_id", "code", "name", "capacity", "room_type", "is_active"))}
    for field, value in data.items():
        if value is not None:
            setattr(record, field, value)
    record = _save(db, record)
    return {"module": "secretaria", "room": _model_dict(record, ("id", "campus_id", "code", "name", "capacity", "room_type", "is_active"))}


@router.get("/ofertas")
def list_offerings(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(AcademicOffering).filter_by(institution_id=institution_id)
    if _user_campus_id(user):
        query = query.filter(AcademicOffering.campus_id == _user_campus_id(user))
    records = query.all()
    items = []
    for record in records:
        items.append({
            **_model_dict(record, ("id", "course_id", "discipline_id", "term_id", "campus_id", "capacity", "status")),
            "course_name": record.course.name,
            "discipline_name": record.discipline.name,
            "term_name": record.term.name,
        })
    return {"module": "secretaria", "items": items}


@router.post("/ofertas", status_code=status.HTTP_201_CREATED)
def create_offering(payload: OfferingCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    course = _get_scoped(db, AcademicCourse, payload.course_id, institution_id, "Curso", user)
    _get_scoped(db, AcademicDiscipline, payload.discipline_id, institution_id, "Disciplina", user)
    _get_scoped(db, AcademicTerm, payload.term_id, institution_id, "Período letivo", user)
    _check_campus(db, payload.campus_id, institution_id, user)
    if course.campus_id and course.campus_id != payload.campus_id:
        raise HTTPException(status_code=422, detail="O curso não está vinculado ao campus da oferta")
    record = AcademicOffering(id=uuid4().hex, institution_id=institution_id, **payload.model_dump())
    _audit_catalog_change(
        db,
        user,
        "academic_offering",
        record.id,
        "academic_offering_created",
        payload.model_dump(mode="json"),
    )
    return {"module": "secretaria", "offering": _model_dict(_save(db, record), ("id", "course_id", "discipline_id", "term_id", "campus_id", "capacity", "status"))}


@router.patch("/ofertas/{offering_id}")
def update_offering(offering_id: str, payload: OfferingUpdate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicOffering, offering_id, institution_id, "Oferta", user)
    data = payload.model_dump(exclude_unset=True)
    if "campus_id" in data:
        _check_campus(db, data["campus_id"], institution_id, user)
    if "course_id" in data:
        course = _get_scoped(db, AcademicCourse, data["course_id"], institution_id, "Curso", user)
        if course.campus_id and (data.get("campus_id") or record.campus_id) and course.campus_id != (data.get("campus_id") or record.campus_id):
            raise HTTPException(status_code=422, detail="O curso não está vinculado ao campus da oferta")
    if "discipline_id" in data:
        _get_scoped(db, AcademicDiscipline, data["discipline_id"], institution_id, "Disciplina", user)
    if "term_id" in data:
        _get_scoped(db, AcademicTerm, data["term_id"], institution_id, "Período letivo", user)
    if not data:
        return {"module": "secretaria", "offering": _model_dict(record, ("id", "course_id", "discipline_id", "term_id", "campus_id", "capacity", "status"))}
    changes = {
        field: {"before": getattr(record, field), "after": value}
        for field, value in data.items()
        if getattr(record, field) != value
    }
    if not changes:
        return {"module": "secretaria", "offering": _model_dict(record, ("id", "course_id", "discipline_id", "term_id", "campus_id", "capacity", "status"))}
    for field, value in data.items():
        if value is not None:
            setattr(record, field, value)
    _audit_catalog_change(
        db,
        user,
        "academic_offering",
        record.id,
        "academic_offering_updated",
        changes,
    )
    record = _save(db, record)
    return {"module": "secretaria", "offering": _model_dict(record, ("id", "course_id", "discipline_id", "term_id", "campus_id", "capacity", "status"))}


@router.get("/turmas")
def list_academic_classes(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(AcademicClass).join(AcademicOffering).filter(AcademicClass.institution_id == institution_id)
    if _user_campus_id(user):
        query = query.filter(AcademicOffering.campus_id == _user_campus_id(user))
    records = query.all()
    return {"module": "secretaria", "items": [
        {
            **_model_dict(record, ("id", "offering_id", "code", "teacher_id", "coordinator_id", "capacity", "status")),
            "course_name": record.offering.course.name,
            "discipline_name": record.offering.discipline.name,
            "term_name": record.offering.term.name,
            "teacher_name": record.teacher.full_name if record.teacher else None,
            "coordinator_name": record.coordinator.full_name if record.coordinator else None,
        }
        for record in records
    ]}


@router.get("/matriculas/turmas-disponiveis")
def list_enrollable_classes(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    has_effective_curriculum_discipline = (
        db.query(AcademicCurriculumDiscipline.id)
        .join(
            AcademicCurriculum,
            AcademicCurriculum.id == AcademicCurriculumDiscipline.curriculum_id,
        )
        .filter(
            AcademicCurriculum.institution_id == institution_id,
            AcademicCurriculum.course_id == AcademicOffering.course_id,
            AcademicCurriculum.status == "ativa",
            AcademicCurriculum.effective_from <= AcademicTerm.starts_on,
            AcademicCurriculumDiscipline.discipline_id == AcademicOffering.discipline_id,
        )
        .exists()
    )
    query = (
        db.query(AcademicClass)
        .join(AcademicOffering)
        .join(AcademicCourse)
        .join(AcademicDiscipline)
        .join(AcademicTerm)
        .filter(
            AcademicClass.institution_id == institution_id,
            AcademicClass.status == "ativa",
            AcademicOffering.status == "aberta",
            AcademicCourse.status == "ativo",
            AcademicDiscipline.status == "ativo",
            AcademicTerm.status != "encerrado",
            AcademicTerm.ends_on >= date.today(),
            has_effective_curriculum_discipline,
        )
    )
    if _user_campus_id(user):
        query = query.filter(AcademicOffering.campus_id == _user_campus_id(user))
    records = query.order_by(AcademicTerm.starts_on, AcademicCourse.name, AcademicClass.code).all()
    if not records:
        return {"module": "secretaria", "items": []}

    class_ids = [record.id for record in records]
    enrollment_counts = dict(
        db.query(
            models.Enrollment.academic_class_id,
            func.count(models.Enrollment.id),
        )
        .filter(
            models.Enrollment.academic_class_id.in_(class_ids),
            models.Enrollment.status.in_(("active", "pending")),
        )
        .group_by(models.Enrollment.academic_class_id)
        .all()
    )
    items = []
    for record in records:
        enrolled_count = enrollment_counts.get(record.id, 0)
        available_seats = record.capacity - enrolled_count
        if available_seats <= 0:
            continue
        items.append({
            "id": record.id,
            "code": record.code,
            "campus_id": record.offering.campus_id,
            "course_name": record.offering.course.name,
            "term_name": record.offering.term.name,
            "term_year": record.offering.term.starts_on.year,
            "campus_name": record.offering.campus.name,
            "available_seats": available_seats,
        })
    return {"module": "secretaria", "items": items}


@router.post("/matriculas/{enrollment_id}/transferir")
def transfer_enrollment(
    enrollment_id: str,
    payload: EnrollmentTransfer,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    source = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.id == enrollment_id,
            models.Enrollment.institution_id == institution_id,
        )
        .with_for_update()
        .first()
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    if _user_campus_id(user) and source.campus_id != _user_campus_id(user):
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    if source.status not in {"active", "pending"}:
        raise HTTPException(
            status_code=409,
            detail="Somente matrículas ativas ou pendentes podem ser transferidas",
        )

    student = db.query(models.Student).filter(
        models.Student.id == source.student_id,
        models.Student.institution_id == institution_id,
    ).with_for_update().first()
    if student is None:
        raise HTTPException(status_code=409, detail="Aluno da matrícula não encontrado")

    target_class = _get_scoped(
        db,
        AcademicClass,
        payload.target_class_id,
        institution_id,
        "Turma de destino",
        user,
    )
    target_class = (
        db.query(AcademicClass)
        .filter(AcademicClass.id == target_class.id)
        .with_for_update()
        .first()
    )
    target_offering = target_class.offering
    target_term = target_offering.term
    target_campus_id = target_offering.campus_id
    if source.academic_class_id == target_class.id:
        raise HTTPException(status_code=409, detail="A matrícula já está vinculada à turma de destino")
    if (
        target_class.status != "ativa"
        or target_offering.status != "aberta"
        or target_offering.course.status != "ativo"
        or target_offering.discipline.status != "ativo"
        or target_term.status == "encerrado"
        or target_term.ends_on < date.today()
    ):
        raise HTTPException(status_code=409, detail="A turma de destino não está disponível para transferência")
    target_curriculum_discipline = (
        db.query(AcademicCurriculumDiscipline)
        .join(
            AcademicCurriculum,
            AcademicCurriculum.id == AcademicCurriculumDiscipline.curriculum_id,
        )
        .filter(
            AcademicCurriculum.institution_id == institution_id,
            AcademicCurriculum.course_id == target_offering.course_id,
            AcademicCurriculum.status == "ativa",
            AcademicCurriculum.effective_from <= target_term.starts_on,
            AcademicCurriculumDiscipline.discipline_id == target_offering.discipline_id,
        )
        .order_by(AcademicCurriculum.effective_from.desc())
        .first()
    )
    if target_curriculum_discipline is None:
        raise HTTPException(
            status_code=409,
            detail="A disciplina de destino não pertence a uma matriz curricular vigente",
        )
    prerequisite_links = db.query(AcademicCurriculumPrerequisite).filter(
        AcademicCurriculumPrerequisite.curriculum_discipline_id
        == target_curriculum_discipline.id
    ).all()
    if prerequisite_links:
        prerequisite_link_ids = {
            link.prerequisite_curriculum_discipline_id
            for link in prerequisite_links
        }
        prerequisite_disciplines = {
            link.id: link.discipline_id
            for link in db.query(AcademicCurriculumDiscipline).filter(
                AcademicCurriculumDiscipline.id.in_(prerequisite_link_ids)
            ).all()
        }
        equivalents_by_prerequisite: dict[str, set[str]] = {}
        for curriculum_discipline_id, equivalent_discipline_id in db.query(
            AcademicCurriculumEquivalence.curriculum_discipline_id,
            AcademicCurriculumEquivalence.equivalent_discipline_id,
        ).filter(
            AcademicCurriculumEquivalence.curriculum_discipline_id.in_(
                prerequisite_link_ids
            )
        ).all():
            equivalents_by_prerequisite.setdefault(
                curriculum_discipline_id,
                set(),
            ).add(equivalent_discipline_id)

        prerequisite_discipline_ids = set(prerequisite_disciplines.values())
        equivalent_discipline_ids = {
            equivalent_id
            for equivalent_ids in equivalents_by_prerequisite.values()
            for equivalent_id in equivalent_ids
        }
        passed_prerequisites = {
            discipline_id
            for (discipline_id,) in db.query(AcademicOffering.discipline_id)
            .join(
                AcademicClass,
                AcademicClass.offering_id == AcademicOffering.id,
            )
            .join(
                models.Enrollment,
                models.Enrollment.academic_class_id == AcademicClass.id,
            )
            .filter(
                models.Enrollment.institution_id == institution_id,
                models.Enrollment.student_id == student.id,
                models.Enrollment.status == "completed",
                models.Enrollment.result == "passed",
                AcademicOffering.institution_id == institution_id,
                AcademicClass.institution_id == institution_id,
                AcademicOffering.course_id == target_offering.course_id,
                AcademicOffering.discipline_id.in_(prerequisite_discipline_ids),
            )
            .distinct()
            .all()
        }
        passed_equivalences = {
            discipline_id
            for (discipline_id,) in db.query(AcademicOffering.discipline_id)
            .join(
                AcademicClass,
                AcademicClass.offering_id == AcademicOffering.id,
            )
            .join(
                models.Enrollment,
                models.Enrollment.academic_class_id == AcademicClass.id,
            )
            .filter(
                models.Enrollment.institution_id == institution_id,
                models.Enrollment.student_id == student.id,
                models.Enrollment.status == "completed",
                models.Enrollment.result == "passed",
                AcademicOffering.institution_id == institution_id,
                AcademicClass.institution_id == institution_id,
                AcademicOffering.discipline_id.in_(equivalent_discipline_ids),
            )
            .distinct()
            .all()
        }
        approved_credit_link_ids = {
            curriculum_discipline_id
            for (curriculum_discipline_id,) in db.query(
                AcademicCreditRecognition.curriculum_discipline_id
            ).filter(
                AcademicCreditRecognition.institution_id == institution_id,
                AcademicCreditRecognition.student_id == student.id,
                AcademicCreditRecognition.course_id == target_offering.course_id,
                AcademicCreditRecognition.curriculum_discipline_id.in_(
                    prerequisite_link_ids
                ),
                AcademicCreditRecognition.status == "approved",
            ).all()
        }
        missing_prerequisites = set()
        for prerequisite in prerequisite_links:
            prerequisite_id = prerequisite.prerequisite_curriculum_discipline_id
            discipline_id = prerequisite_disciplines[prerequisite_id]
            is_satisfied = (
                prerequisite_id in approved_credit_link_ids
                or discipline_id in passed_prerequisites
                or bool(
                    equivalents_by_prerequisite.get(prerequisite_id, set())
                    & passed_equivalences
                )
            )
            if not is_satisfied:
                missing_prerequisites.add(discipline_id)
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
                detail="Pré-requisitos acadêmicos pendentes: " + ", ".join(missing_names),
            )
    if student.campus_id != target_campus_id:
        other_current_enrollment = db.query(models.Enrollment.id).filter(
            models.Enrollment.student_id == student.id,
            models.Enrollment.institution_id == institution_id,
            models.Enrollment.id != source.id,
            models.Enrollment.status.in_(("active", "pending")),
            or_(
                models.Enrollment.campus_id != target_campus_id,
                models.Enrollment.campus_id.is_(None),
            ),
        ).first()
        if other_current_enrollment:
            raise HTTPException(
                status_code=409,
                detail="O aluno possui outras matrículas vigentes em outro campus",
            )
    duplicate = db.query(models.Enrollment.id).filter(
        models.Enrollment.student_id == student.id,
        models.Enrollment.institution_id == institution_id,
        models.Enrollment.academic_class_id == target_class.id,
        models.Enrollment.status.in_(("active", "pending")),
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="O aluno já possui vínculo vigente na turma de destino")
    occupied_seats = db.query(func.count(models.Enrollment.id)).filter(
        models.Enrollment.academic_class_id == target_class.id,
        models.Enrollment.institution_id == institution_id,
        models.Enrollment.status.in_(("active", "pending")),
    ).scalar() or 0
    if occupied_seats >= target_class.capacity:
        raise HTTPException(status_code=409, detail="A turma de destino não possui vagas disponíveis")

    source_link, _ = current_enrollment_academic_link(db, source)
    source_status = source.status
    source.status = "transferred"
    target = models.Enrollment(
        id=uuid4().hex,
        institution_id=institution_id,
        student_id=student.id,
        academic_class_id=target_class.id,
        course_name=target_offering.course.name,
        class_name=target_class.code,
        year=target_term.starts_on.year,
        status="pending",
        campus_id=target_campus_id,
    )
    db.add(target)
    db.flush()
    target_link, _ = current_enrollment_academic_link(db, target)
    _audit_catalog_change(
        db,
        user,
        "enrollment",
        source.id,
        "academic_transfer_out",
        {
            "academic_link": source_link,
            "before": {"status": source_status, "academic_link": source_link},
            "after": {"status": "transferred", "academic_link": target_link},
            "destination_enrollment_id": target.id,
        },
    )
    _audit_catalog_change(
        db,
        user,
        "enrollment",
        target.id,
        "academic_transfer_in",
        {
            "academic_link": target_link,
            "source_enrollment_id": source.id,
            "before": None,
            "after": {"status": "pending", "academic_link": target_link},
        },
    )
    if student.campus_id != target_campus_id:
        previous_campus_id = student.campus_id
        student.campus_id = target_campus_id
        _audit_catalog_change(
            db,
            user,
            "student",
            student.id,
            "academic_campus_transferred",
            {"campus_id": {"before": previous_campus_id, "after": target_campus_id}},
        )
    db.commit()
    db.refresh(source)
    db.refresh(target)
    return {
        "module": "secretaria",
        "message": "Transferência acadêmica registrada",
        "source_enrollment": {
            "id": source.id,
            "status": source.status,
            "academic_link": source_link,
        },
        "target_enrollment": {
            "id": target.id,
            "status": target.status,
            "academic_link": target_link,
        },
    }


@router.post("/turmas", status_code=status.HTTP_201_CREATED)
def create_academic_class(payload: ClassCreate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    offering = _get_scoped(db, AcademicOffering, payload.offering_id, institution_id, "Oferta", user)
    if payload.capacity > offering.capacity:
        raise HTTPException(status_code=422, detail="A capacidade da turma não pode exceder a capacidade da oferta")
    teacher = _get_scoped(db, AcademicStaff, payload.teacher_id, institution_id, "Professor", user) if payload.teacher_id else None
    coordinator = _get_scoped(db, AcademicStaff, payload.coordinator_id, institution_id, "Coordenador", user) if payload.coordinator_id else None
    if teacher and teacher.staff_type != "professor":
        raise HTTPException(status_code=422, detail="O profissional informado não está cadastrado como professor")
    if coordinator and coordinator.staff_type != "coordenador":
        raise HTTPException(status_code=422, detail="O profissional informado não está cadastrado como coordenador")
    if teacher and teacher.status != "ativo":
        raise HTTPException(status_code=422, detail="O professor informado está inativo")
    if coordinator and coordinator.status != "ativo":
        raise HTTPException(status_code=422, detail="O coordenador informado está inativo")
    if teacher and teacher.campus_id and teacher.campus_id != offering.campus_id:
        raise HTTPException(status_code=422, detail="O professor está vinculado a outro campus")
    if coordinator and coordinator.campus_id and coordinator.campus_id != offering.campus_id:
        raise HTTPException(status_code=422, detail="O coordenador está vinculado a outro campus")
    record = AcademicClass(id=uuid4().hex, institution_id=institution_id, **payload.model_dump())
    _audit_catalog_change(
        db,
        user,
        "academic_class",
        record.id,
        "academic_class_created",
        payload.model_dump(mode="json"),
    )
    return {"module": "secretaria", "class": _model_dict(_save(db, record), ("id", "offering_id", "code", "teacher_id", "coordinator_id", "capacity", "status"))}


@router.patch("/turmas/{class_id}")
def update_academic_class(class_id: str, payload: ClassUpdate, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    record = _get_scoped(db, AcademicClass, class_id, institution_id, "Turma", user)
    data = payload.model_dump(exclude_unset=True)
    if "offering_id" in data:
        offering = _get_scoped(db, AcademicOffering, data["offering_id"], institution_id, "Oferta", user)
        target_capacity = data.get("capacity", record.capacity)
        if target_capacity > offering.capacity:
            raise HTTPException(status_code=422, detail="A capacidade da turma não pode exceder a capacidade da oferta")
    elif "capacity" in data:
        if data["capacity"] > record.offering.capacity:
            raise HTTPException(status_code=422, detail="A capacidade da turma não pode exceder a capacidade da oferta")
    if "teacher_id" in data and data["teacher_id"] is not None:
        teacher = _get_scoped(db, AcademicStaff, data["teacher_id"], institution_id, "Professor", user)
        if teacher.staff_type != "professor":
            raise HTTPException(status_code=422, detail="O profissional informado não está cadastrado como professor")
        if teacher.status != "ativo":
            raise HTTPException(status_code=422, detail="O professor informado está inativo")
        if teacher.campus_id and teacher.campus_id != record.offering.campus_id:
            raise HTTPException(status_code=422, detail="O professor está vinculado a outro campus")
    if "coordinator_id" in data and data["coordinator_id"] is not None:
        coordinator = _get_scoped(db, AcademicStaff, data["coordinator_id"], institution_id, "Coordenador", user)
        if coordinator.staff_type != "coordenador":
            raise HTTPException(status_code=422, detail="O profissional informado não está cadastrado como coordenador")
        if coordinator.status != "ativo":
            raise HTTPException(status_code=422, detail="O coordenador informado está inativo")
        if coordinator.campus_id and coordinator.campus_id != record.offering.campus_id:
            raise HTTPException(status_code=422, detail="O coordenador está vinculado a outro campus")
    if not data:
        return {"module": "secretaria", "class": _model_dict(record, ("id", "offering_id", "code", "teacher_id", "coordinator_id", "capacity", "status"))}
    changes = {
        field: {"before": getattr(record, field), "after": value}
        for field, value in data.items()
        if getattr(record, field) != value
    }
    if not changes:
        return {"module": "secretaria", "class": _model_dict(record, ("id", "offering_id", "code", "teacher_id", "coordinator_id", "capacity", "status"))}
    for field, value in data.items():
        setattr(record, field, value)
    allocation_changed = bool({"teacher_id", "coordinator_id"} & changes.keys())
    _audit_catalog_change(
        db,
        user,
        "academic_class",
        record.id,
        "faculty_allocation_updated" if allocation_changed else "academic_class_updated",
        changes,
    )
    record = _save(db, record)
    return {"module": "secretaria", "class": _model_dict(record, ("id", "offering_id", "code", "teacher_id", "coordinator_id", "capacity", "status"))}


@router.get("/turmas/{class_id}/horarios")
def list_class_schedules(class_id: str, db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    _get_scoped(db, AcademicClass, class_id, institution_id, "Turma", user)
    records = db.query(AcademicClassSchedule).filter_by(
        institution_id=institution_id,
        class_id=class_id,
    ).order_by(AcademicClassSchedule.weekday, AcademicClassSchedule.starts_at).all()
    return {"module": "secretaria", "items": [
        {
            **_model_dict(record, ("id", "class_id", "room_id", "weekday", "starts_at", "ends_at")),
            "room_name": record.room.name if record.room else None,
        }
        for record in records
    ]}


@router.get("/horarios")
def list_academic_schedules(db: Session = Depends(get_db), user: Any = SecretaryUser):
    institution_id = _institution_id(user)
    query = db.query(AcademicClassSchedule).join(AcademicClass).join(AcademicOffering).filter(
        AcademicClassSchedule.institution_id == institution_id,
    )
    if _user_campus_id(user):
        query = query.filter(AcademicOffering.campus_id == _user_campus_id(user))
    records = query.order_by(
        AcademicClassSchedule.weekday,
        AcademicClassSchedule.starts_at,
    ).all()
    return {"module": "secretaria", "items": [
        {
            **_model_dict(record, ("id", "class_id", "room_id", "weekday", "starts_at", "ends_at")),
            "class_code": record.academic_class.code,
            "discipline_name": record.academic_class.offering.discipline.name,
            "room_name": record.room.name if record.room else "Virtual/sem sala",
        }
        for record in records
    ]}


@router.get("/historico-alteracoes/{entity_type}/{entity_id}")
def get_academic_change_history(
    entity_type: Literal[
        "oferta",
        "turma",
        "horario",
        "profissional",
        "responsabilidade-coordenacao",
    ],
    entity_id: str,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    if entity_type == "oferta":
        _get_scoped(db, AcademicOffering, entity_id, institution_id, "Oferta", user)
        audit_entity = "academic_offering"
    elif entity_type == "turma":
        _get_scoped(db, AcademicClass, entity_id, institution_id, "Turma", user)
        audit_entity = "academic_class"
    elif entity_type == "profissional":
        _get_scoped(db, AcademicStaff, entity_id, institution_id, "Profissional acadêmico", user)
        audit_entity = "academic_staff"
    elif entity_type == "responsabilidade-coordenacao":
        _get_scoped(
            db,
            AcademicCoordinatorAssignment,
            entity_id,
            institution_id,
            "Responsabilidade de coordenação",
            user,
        )
        audit_entity = "academic_coordinator_assignment"
    else:
        schedule = db.query(AcademicClassSchedule).filter(
            AcademicClassSchedule.id == entity_id,
            AcademicClassSchedule.institution_id == institution_id,
        ).first()
        if schedule is None:
            raise HTTPException(status_code=404, detail="Horário não encontrado")
        _get_scoped(
            db,
            AcademicClass,
            schedule.class_id,
            institution_id,
            "Turma",
            user,
        )
        audit_entity = "academic_schedule"

    events = (
        db.query(models.AuditEvent)
        .filter(
            models.AuditEvent.entity == audit_entity,
            models.AuditEvent.entity_id == entity_id,
        )
        .order_by(models.AuditEvent.created_at.desc(), models.AuditEvent.id.desc())
        .all()
    )
    return {
        "module": "secretaria",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "items": [
            {
                "action": event.action,
                "details": event.details,
                "user_id": event.user_id,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


def _validate_schedule(
    db: Session,
    user: Any,
    institution_id: str,
    academic_class: AcademicClass,
    room_id: str | None,
    weekday: int,
    starts_at: time,
    ends_at: time,
    exclude_schedule_id: str | None = None,
) -> None:
    if ends_at <= starts_at:
        raise HTTPException(status_code=422, detail="O horário final deve ser posterior ao horário inicial")

    room = _get_scoped(db, AcademicRoom, room_id, institution_id, "Sala", user) if room_id else None
    if room:
        if not room.is_active:
            raise HTTPException(status_code=409, detail="A sala está inativa")
        if room.campus_id != academic_class.offering.campus_id:
            raise HTTPException(status_code=422, detail="A sala deve pertencer ao campus da oferta")
        if room.capacity < academic_class.capacity:
            raise HTTPException(status_code=422, detail="A capacidade da sala é menor que a capacidade da turma")

    overlapping_query = db.query(AcademicClassSchedule).filter(
        AcademicClassSchedule.institution_id == institution_id,
        AcademicClassSchedule.weekday == weekday,
        AcademicClassSchedule.starts_at < ends_at,
        AcademicClassSchedule.ends_at > starts_at,
    )
    if exclude_schedule_id:
        overlapping_query = overlapping_query.filter(
            AcademicClassSchedule.id != exclude_schedule_id
        )
    class_conflict = overlapping_query.filter(
        AcademicClassSchedule.class_id == academic_class.id
    ).first()
    if class_conflict:
        raise HTTPException(status_code=409, detail="A turma já possui um horário sobreposto")
    if room:
        room_conflict = overlapping_query.filter(AcademicClassSchedule.room_id == room.id).first()
        if room_conflict:
            raise HTTPException(status_code=409, detail="A sala já está ocupada neste horário")

    if academic_class.teacher_id:
        teacher_conflict = overlapping_query.join(
            AcademicClass,
            AcademicClassSchedule.class_id == AcademicClass.id,
        ).filter(
            AcademicClass.teacher_id == academic_class.teacher_id,
            AcademicClass.id != academic_class.id,
        ).first()
        if teacher_conflict:
            raise HTTPException(status_code=409, detail="O professor já possui outra turma neste horário")


@router.post("/turmas/{class_id}/horarios", status_code=status.HTTP_201_CREATED)
def create_class_schedule(
    class_id: str,
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    academic_class = _get_scoped(db, AcademicClass, class_id, institution_id, "Turma", user)
    _validate_schedule(
        db,
        user,
        institution_id,
        academic_class,
        payload.room_id,
        payload.weekday,
        payload.starts_at,
        payload.ends_at,
    )

    record = AcademicClassSchedule(
        id=uuid4().hex,
        institution_id=institution_id,
        class_id=class_id,
        **payload.model_dump(),
    )
    _audit_catalog_change(
        db,
        user,
        "academic_schedule",
        record.id,
        "academic_schedule_created",
        payload.model_dump(mode="json"),
    )
    return {"module": "secretaria", "schedule": _model_dict(_save(db, record), ("id", "class_id", "room_id", "weekday", "starts_at", "ends_at"))}


@router.patch("/horarios/{schedule_id}")
def update_class_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    user: Any = SecretaryUser,
):
    institution_id = _institution_id(user)
    record = db.query(AcademicClassSchedule).filter(
        AcademicClassSchedule.id == schedule_id,
        AcademicClassSchedule.institution_id == institution_id,
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Horário não encontrado")
    academic_class = _get_scoped(
        db,
        AcademicClass,
        record.class_id,
        institution_id,
        "Turma",
        user,
    )
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return {
            "module": "secretaria",
            "schedule": _model_dict(record, ("id", "class_id", "room_id", "weekday", "starts_at", "ends_at")),
        }
    if any(data.get(field) is None for field in ("weekday", "starts_at", "ends_at") if field in data):
        raise HTTPException(status_code=422, detail="Dia e horários não podem ser nulos")

    room_id = data.get("room_id", record.room_id)
    weekday = data.get("weekday", record.weekday)
    starts_at = data.get("starts_at", record.starts_at)
    ends_at = data.get("ends_at", record.ends_at)
    _validate_schedule(
        db,
        user,
        institution_id,
        academic_class,
        room_id,
        weekday,
        starts_at,
        ends_at,
        exclude_schedule_id=record.id,
    )
    changes = {
        field: {"before": getattr(record, field), "after": value}
        for field, value in data.items()
        if getattr(record, field) != value
    }
    if not changes:
        return {
            "module": "secretaria",
            "schedule": _model_dict(record, ("id", "class_id", "room_id", "weekday", "starts_at", "ends_at")),
        }
    for field, value in data.items():
        setattr(record, field, value)
    _audit_catalog_change(
        db,
        user,
        "academic_schedule",
        record.id,
        "academic_schedule_updated",
        changes,
    )
    record = _save(db, record)
    return {
        "module": "secretaria",
        "schedule": _model_dict(record, ("id", "class_id", "room_id", "weekday", "starts_at", "ends_at")),
    }
