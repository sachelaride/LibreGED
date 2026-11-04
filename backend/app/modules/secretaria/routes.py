import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app import models, models_ged
from app.academic_history import current_enrollment_academic_link
from app.auth import require_module_access
from app.database import get_db
from app.modules.data_store import (courses, documents, enrollments,
                                    financial_contracts, get_academic_summary,
                                    get_active_enrollment_count,
                                    get_pending_document_count, get_student_context,
                                    get_student_detail, get_student_lifecycle_summary,
                                    invoices, pending_actions, student_journey,
                                    students)

router = APIRouter(prefix="/secretaria", tags=["Secretaria"])


def _append_student_journey(student_id: str, stage: str, status: str, details: str, responsible: str = "secretaria") -> None:
    history = student_journey.setdefault(student_id, [])
    history.append({
        "id": f"JOU-{student_id}-{len(history) + 1}",
        "stage": stage,
        "status": status,
        "date": "2026-01-15",
        "responsible": responsible,
        "details": details,
    })


def _db_scope_query(db: Session, user: Any):
    query = db.query(models.Student)
    institution_id = getattr(user, "institution_id", None)
    if institution_id:
        query = query.filter(models.Student.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        query = query.filter(models.Student.campus_id == campus_id)
    return query


def _serialize_student(student: models.Student) -> dict[str, Any]:
    enrollments_count = len(student.enrollments or [])
    return {
        "student_id": student.id,
        "user_id": student.user_id,
        "person_id": None,
        "full_name": student.full_name,
        "cpf": student.cpf,
        "email": student.email,
        "course": "Sem curso vinculado",
        "course_id": None,
        "campus": student.campus.name if student.campus else None,
        "enrollment_status": "matriculado" if enrollments_count else "pendente",
        "start_date": student.created_at.date().isoformat() if student.created_at else None,
        "status": "matriculado" if enrollments_count else "pendente",
        "document_status": "pendente",
        "responsible_financial": "Responsável pendente",
    }


def _serialize_enrollment(enrollment: models.Enrollment) -> dict[str, Any]:
    return {
        "enrollment_id": enrollment.id,
        "student_id": enrollment.student_id,
        "course_id": enrollment.course_name,
        "course_name": enrollment.course_name,
        "period": f"{enrollment.year}/1",
        "status": enrollment.status,
        "campus": enrollment.campus.name if enrollment.campus else None,
        "start_date": enrollment.created_at.date().isoformat() if enrollment.created_at else None,
        "contract_status": "em_validacao",
        "responsible_financial_name": "Responsável pendente",
        "payment_plan": "anuidade_semestre",
        "documents_ok": enrollment.status in {"active", "matriculado", "ativo"},
        "approved_by": "secretaria" if enrollment.status in {"active", "matriculado", "ativo"} else None,
    }


class StudentCreate(BaseModel):
    student_id: str
    full_name: str
    cpf: str
    email: str | None = None
    course: str | None = None
    campus: str | None = None
    enrollment_status: str | None = None
    start_date: str | None = None
    responsible_financial: str | None = None
    phone: str | None = None
    address_street: str | None = None
    address_number: str | None = None
    address_complement: str | None = None
    address_neighborhood: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_postal_code: str | None = None


class EnrollmentCreate(BaseModel):
    student_id: str
    course_id: str | None = None
    course_name: str | None = None
    campus: str | None = None
    period: str = "2026/1"
    status: str = "matriculado"
    contract_status: str = "em_validacao"
    responsible_financial_name: str | None = None
    payment_plan: str | None = None


class EnrollmentStatusUpdate(BaseModel):
    status: str
    contract_status: str | None = None
    notes: str | None = None


@router.get("/dashboard")
def secretaria_dashboard(user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    base = get_academic_summary()
    scoped_students = _db_scope_query(db, user).all()
    active_enrollments = db.query(models.Enrollment)
    institution_id = getattr(user, "institution_id", None)
    if institution_id:
        active_enrollments = active_enrollments.filter(models.Enrollment.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        active_enrollments = active_enrollments.filter(models.Enrollment.campus_id == campus_id)
    return {
        "module": "secretaria",
        "title": "Dashboard da Secretaria",
        "stats": {
            "alunos_cadastrados": len(scoped_students),
            "matriculas_ativas": active_enrollments.filter(models.Enrollment.status.in_(["active", "matriculado", "ativo"])).count(),
            "pendencias": sum(1 for s in scoped_students if not s.cpf),
            "documentos_pendentes": max(get_pending_document_count(), len(scoped_students)),
            "processos_abertos": sum(len(items) for items in student_journey.values()),
            "curso_mais_popular": "Análise e Desenvolvimento de Sistemas",
            "total_cursos": len(base["courses"]),
            "total_turmas": len(base["classes"]),
        },
        "institution": base["institution"],
        "campuses": base["campuses"],
        "courses": base["courses"],
        "classes": base["classes"],
        "features": [
            "Cadastro de alunos",
            "Matrículas",
            "Processos acadêmicos",
            "Documentos pessoais",
            "Histórico acadêmico",
            "Acompanhamento de curso",
        ],
        "user": getattr(user, "username", None),
    }


@router.get("/base-academica")
def academic_base_snapshot(user: Any = Depends(require_module_access("secretaria"))):
    return {
        "module": "secretaria",
        "summary": get_academic_summary(),
    }


@router.get("/alunos")
def list_students(user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    records = _db_scope_query(db, user).all()
    if records:
        return {"module": "secretaria", "items": [_serialize_student(student) for student in records]}
    return {"module": "secretaria", "items": list(students.values())}


@router.get("/alunos/{student_id}")
def get_student(student_id: str, user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    student = _db_scope_query(db, user).filter(models.Student.id == student_id).first()
    if not student:
        legacy = students.get(student_id)
        if not legacy:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        return {"module": "secretaria", "student": get_student_detail(student_id)}
    return {"module": "secretaria", "student": _serialize_student(student)}


@router.get("/alunos/{student_id}/detalhe")
def get_student_detail_route(student_id: str, user: Any = Depends(require_module_access("secretaria"))):
    detail = get_student_detail(student_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return {"module": "secretaria", "detail": detail}


@router.get("/alunos/{student_id}/contexto")
def get_student_academic_context(student_id: str, user: Any = Depends(require_module_access("secretaria"))):
    context = get_student_context(student_id)
    if not context:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return {"module": "secretaria", "context": context}


@router.get("/processos")
def list_academic_processes(user: Any = Depends(require_module_access("secretaria"))):
    processes = []
    for student_id, items in student_journey.items():
        for item in items:
            processes.append({
                "student_id": student_id,
                "student_name": students.get(student_id, {}).get("full_name"),
                **item,
            })
    return {"module": "secretaria", "items": processes}


@router.post("/alunos")
def create_student(payload: StudentCreate, user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    existing = _db_scope_query(db, user).filter(models.Student.id == payload.student_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Aluno já existente")

    institution_id = getattr(user, "institution_id", None)
    campus_id = getattr(user, "campus_id", None) or payload.campus
    if isinstance(campus_id, str):
        campus_record = db.query(models.Campus).filter(models.Campus.id == campus_id, models.Campus.institution_id == institution_id).first()
        if not campus_record and institution_id:
            campus_record = db.query(models.Campus).filter(models.Campus.institution_id == institution_id).first()
        if campus_record:
            campus_id = campus_record.id
    if not institution_id:
        raise HTTPException(status_code=403, detail="Usuário sem instituição vinculada")

    student = models.Student(
        id=payload.student_id,
        institution_id=institution_id,
        full_name=payload.full_name,
        birth_date=payload.start_date or "2000-01-01",
        cpf=payload.cpf,
        email=payload.email or f"{payload.student_id}@example.com",
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
    db.commit()
    db.refresh(student)

    student_journey.setdefault(payload.student_id, []).append({
        "id": f"JOU-{payload.student_id}-1",
        "stage": "cadastro",
        "status": "registrado",
        "date": payload.start_date or "2026-01-15",
        "responsible": "secretaria",
        "details": "Aluno cadastrado e aguardando processamento de matrícula.",
    })
    return {"message": "Aluno registrado com sucesso", "module": "secretaria", "student": _serialize_student(student)}


@router.get("/matriculas")
def list_enrollments(user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    query = db.query(models.Enrollment)
    institution_id = getattr(user, "institution_id", None)
    if institution_id:
        query = query.filter(models.Enrollment.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        query = query.filter(models.Enrollment.campus_id == campus_id)
    records = query.options(joinedload(models.Enrollment.student), joinedload(models.Enrollment.campus)).all()
    if records:
        return {"module": "secretaria", "items": [_serialize_enrollment(item) for item in records]}
    return {"module": "secretaria", "items": list(enrollments.values())}


@router.get("/matriculas/{enrollment_id}")
def get_enrollment_detail(enrollment_id: str, user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if not enrollment:
        legacy = enrollments.get(enrollment_id)
        if not legacy:
            raise HTTPException(status_code=404, detail="Matrícula não encontrada")
        return {"module": "secretaria", "enrollment": legacy, "student": students.get(legacy["student_id"], {}), "lifecycle": get_student_lifecycle_summary(legacy["student_id"])}

    student = db.query(models.Student).filter(models.Student.id == enrollment.student_id).first()
    return {"module": "secretaria", "enrollment": _serialize_enrollment(enrollment), "student": _serialize_student(student) if student else {}, "lifecycle": get_student_lifecycle_summary(enrollment.student_id)}


@router.post("/matriculas/{enrollment_id}/status")
def update_enrollment_status(enrollment_id: str, payload: EnrollmentStatusUpdate, user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    valid_statuses = {
        "matriculado",
        "pendente",
        "ativo",
        "inativo",
        "trancado",
        "cancelado",
        "reingresso",
        "transferido",
        "concluido",
        "active",
        "pending",
        "inactive",
        "transferred",
        "graduated",
        "completed",
    }
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status inválido: {payload.status}")

    if not enrollment:
        legacy = enrollments.get(enrollment_id)
        if not legacy:
            raise HTTPException(status_code=404, detail="Matrícula não encontrada")
        legacy["status"] = payload.status
        if payload.contract_status:
            legacy["contract_status"] = payload.contract_status
        student = students.get(legacy["student_id"])
        if student:
            student["status"] = payload.status
            student["enrollment_status"] = payload.status
        _append_student_journey(
            legacy["student_id"],
            "matricula",
            payload.status,
            payload.notes or "Status da matrícula atualizado pela secretaria.",
            responsible="secretaria",
        )
        return {"message": "Status da matrícula atualizado com sucesso", "module": "secretaria", "enrollment": legacy}

    if payload.contract_status is not None:
        raise HTTPException(
            status_code=422,
            detail="Situação financeira deve ser atualizada no módulo financeiro.",
        )
    if user.role != "admin_global" and enrollment.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    if user.campus_id and enrollment.campus_id != user.campus_id:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    if enrollment.student.institution_id != enrollment.institution_id:
        raise HTTPException(status_code=409, detail="Matrícula possui vínculo institucional inconsistente")

    previous_state = {
        "status": enrollment.status,
        "result": enrollment.result,
    }
    academic_link, link_source = current_enrollment_academic_link(db, enrollment)
    enrollment.status = payload.status
    cancelled_financial_installments = 0
    if previous_state["status"] != enrollment.status:
        from app.main import add_audit
        from app.financial_services import apply_enrollment_financial_policy

        add_audit(
            db,
            "enrollment",
            enrollment.id,
            "status_updated",
            json.dumps(
                {
                    "before": previous_state,
                    "after": {
                        "status": enrollment.status,
                        "result": enrollment.result,
                    },
                    "academic_link": academic_link,
                    "academic_link_source": link_source,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            str(user.id),
        )
        cancelled_financial_installments = apply_enrollment_financial_policy(
            db,
            enrollment,
            payload.status,
            str(user.id),
        )
    db.commit()
    _append_student_journey(
        enrollment.student_id,
        "matricula",
        payload.status,
        payload.notes or "Status da matrícula atualizado pela secretaria.",
        responsible="secretaria",
    )
    return {
        "message": "Status da matrícula atualizado com sucesso",
        "module": "secretaria",
        "enrollment": _serialize_enrollment(enrollment),
        "financial_effects": {
            "cancelled_future_installments": cancelled_financial_installments,
        },
    }


@router.get("/fluxo")
def list_academic_flow(user: Any = Depends(require_module_access("secretaria"))):
    return {
        "module": "secretaria",
        "items": [get_student_lifecycle_summary(student_id) for student_id in students],
    }


@router.get("/fluxo-integrado/{student_id}")
def get_integrated_student_flow(student_id: str, user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    student = _db_scope_query(db, user).filter(models.Student.id == student_id).first()
    if not student:
        legacy_student = students.get(student_id)
        if not legacy_student:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        legacy_enrollment = next((item for item in enrollments.values() if item.get("student_id") == student_id), None)
        return {
            "module": "secretaria",
            "student_id": student_id,
            "student": legacy_student,
            "enrollment": legacy_enrollment,
            "documents": [doc for doc in documents.values() if doc.get("student_id") == student_id],
            "pendencias": [item for item in pending_actions if item.get("student_id") == student_id],
            "financeiro": {
                "boletos": [item for item in invoices.values() if item.get("student_id") == student_id],
                "contratos": [item for item in financial_contracts.values() if item.get("student_id") == student_id],
            },
            "status_global": "pendente" if not legacy_enrollment else legacy_enrollment.get("status"),
        }

    enrollment = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == student.id)
        .order_by(models.Enrollment.created_at.desc())
        .first()
    )
    documents_for_student = db.query(models_ged.GEDDocument).filter(models_ged.GEDDocument.student_id == student.id).all()
    pendencias = [item for item in pending_actions if item.get("student_id") == student.id]
    financial_rows = {
        "boletos": [item for item in invoices.values() if item.get("student_id") == student.id],
        "contratos": [item for item in financial_contracts.values() if item.get("student_id") == student.id],
    }
    status_global = "pendente"
    if enrollment:
        status_global = enrollment.status

    return {
        "module": "secretaria",
        "student_id": student.id,
        "student": _serialize_student(student),
        "enrollment": _serialize_enrollment(enrollment) if enrollment else None,
        "documents": [_serialize_ged_document(doc) for doc in documents_for_student],
        "pendencias": pendencias,
        "financeiro": financial_rows,
        "status_global": status_global,
        "journey": student_journey.get(student.id, []),
    }


def _serialize_ged_document(doc: models_ged.GEDDocument) -> dict[str, Any]:
    return {
        "document_id": doc.id,
        "title": doc.title,
        "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        "category": doc.category.name if doc.category else "Acadêmico",
        "student_id": doc.student_id,
        "institution_id": doc.institution_id,
        "campus_id": doc.campus_id,
    }


@router.post("/matriculas")
def create_enrollment(payload: EnrollmentCreate, user: Any = Depends(require_module_access("secretaria")), db: Session = Depends(get_db)):
    student = _db_scope_query(db, user).filter(models.Student.id == payload.student_id).first()
    if not student:
        legacy_student = students.get(payload.student_id)
        if not legacy_student:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        legacy_student["status"] = payload.status
        legacy_student["enrollment_status"] = payload.status
        course_data = courses.get(payload.course_id or "CUR-ADS", {})
        enrollment_id = f"MAT-{len(enrollments) + 1:04d}"
        enrollment = {
            "enrollment_id": enrollment_id,
            "student_id": payload.student_id,
            "course_id": payload.course_id or course_data.get("course_id", "CUR-ADS"),
            "course_name": payload.course_name or course_data.get("name") or legacy_student.get("course"),
            "period": payload.period,
            "status": payload.status,
            "campus": payload.campus or legacy_student.get("campus", "Campus Central"),
            "start_date": legacy_student.get("start_date") or "2026-01-15",
            "contract_status": payload.contract_status,
            "responsible_financial_id": f"PES-RESP-{len(enrollments) + 1}",
            "responsible_financial_name": payload.responsible_financial_name or legacy_student.get("responsible_financial", "Responsável pendente"),
            "payment_plan": payload.payment_plan or "anuidade_semestre",
            "documents_ok": payload.status == "matriculado",
            "approved_by": "secretaria" if payload.status == "matriculado" else None,
        }
        enrollments[enrollment_id] = enrollment
        student_journey.setdefault(payload.student_id, []).append({
            "id": f"JOU-{payload.student_id}-{len(student_journey.get(payload.student_id, [])) + 1}",
            "stage": "matricula",
            "status": payload.status,
            "date": enrollment["start_date"],
            "responsible": "secretaria",
            "details": "Nova matrícula registrada com dados integrados de aluno, curso e responsável financeiro.",
        })
        return {"message": "Matrícula registrada com sucesso", "module": "secretaria", "enrollment": enrollment}

    institution_id = getattr(user, "institution_id", None)
    if not institution_id:
        raise HTTPException(status_code=403, detail="Usuário sem instituição vinculada")

    enrollment_id = str(uuid4())
    campus_id = getattr(user, "campus_id", None)
    if payload.campus:
        campus_record = db.query(models.Campus).filter(models.Campus.id == payload.campus, models.Campus.institution_id == institution_id).first()
        if campus_record:
            campus_id = campus_record.id

    new_enrollment = models.Enrollment(
        id=enrollment_id,
        institution_id=institution_id,
        student_id=student.id,
        course_name=payload.course_name or "Curso não informado",
        class_name=payload.period,
        year=int(payload.period.split("/")[0]) if "/" in payload.period else 2026,
        status=payload.status,
        campus_id=campus_id,
    )
    db.add(new_enrollment)
    db.flush()
    from app.main import add_audit

    add_audit(
        db,
        "enrollment",
        new_enrollment.id,
        "created",
        json.dumps(
            {
                "academic_link": {
                    "course_name": new_enrollment.course_name,
                    "class_name": new_enrollment.class_name,
                    "year": new_enrollment.year,
                    "campus_id": new_enrollment.campus_id,
                },
                "academic_link_source": "legacy_enrollment",
                "status": new_enrollment.status,
                "result": new_enrollment.result,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        str(user.id),
    )
    db.commit()
    db.refresh(new_enrollment)
    _append_student_journey(
        student.id,
        "matricula",
        payload.status,
        "Matrícula registrada pela secretaria com validação de instituição e campus.",
        responsible="secretaria",
    )

    return {"message": "Matrícula registrada com sucesso", "module": "secretaria", "enrollment": _serialize_enrollment(new_enrollment)}
