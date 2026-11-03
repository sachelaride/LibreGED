from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app import models
from app.auth import require_module_access
from app.database import get_db
from app.modules.data_store import (
    documents,
    enrollments,
    get_active_enrollment_count,
    get_pending_document_count,
    get_student_detail,
    student_journey,
    students,
)

router = APIRouter(prefix="/sead", tags=["SEAD"])


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
    return {
        "student_id": student.id,
        "person_id": None,
        "full_name": student.full_name,
        "cpf": student.cpf,
        "email": student.email,
        "status": "matriculado",
        "course": "Sem curso vinculado",
        "course_id": None,
        "campus": student.campus.name if student.campus else None,
        "enrollment_status": "matriculado",
        "document_status": "pendente",
        "document_checklist": [],
        "required_documents": [],
        "responsible_financial": "Responsável pendente",
        "entry_channel": "cadastro",
        "period": "2026/1",
        "admission_stage": "cadastro",
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
        "approved_by": "sead" if enrollment.status in {"active", "matriculado", "ativo"} else None,
    }


class AcademicRequestCreate(BaseModel):
    student_id: str
    type: str = "requerimento"
    category: str = "documentacao"
    description: str
    priority: str = "media"
    due_date: str | None = None


@router.get("/dashboard")
def sead_dashboard(user: Any = Depends(require_module_access("sead")), db: Session = Depends(get_db)):
    scoped_students = _db_scope_query(db, user).all()
    active_enrollments = db.query(models.Enrollment)
    institution_id = getattr(user, "institution_id", None)
    if institution_id:
        active_enrollments = active_enrollments.filter(models.Enrollment.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        active_enrollments = active_enrollments.filter(models.Enrollment.campus_id == campus_id)
    active_enrollments = active_enrollments.filter(models.Enrollment.status.in_(["active", "matriculado", "ativo"]))

    data = {
        "module": "sead",
        "title": "SEAD — Secretaria Acadêmica Digital",
        "stats": {
            "alunos_cadastrados": len(scoped_students),
            "matriculas_ativas": active_enrollments.count(),
            "pendencias_academicas": sum(1 for student in scoped_students if student.cpf is None),
            "documentos_pendentes": max(get_pending_document_count(), len(scoped_students)),
            "processos_abertos": sum(len(items) for items in student_journey.values()),
            "grau_atendimento": "94%",
        },
        "features": [
            "Atendimento e protocolo",
            "Matrículas e rematrículas",
            "Histórico e documentos acadêmicos",
            "Requerimentos e decisões",
            "Integração com GED e Financeiro",
        ],
        "user": getattr(user, "username", None),
    }
    return data


@router.get("/alunos")
def list_students(user: Any = Depends(require_module_access("sead")), db: Session = Depends(get_db)):
    records = _db_scope_query(db, user).all()
    return {"module": "sead", "items": [_serialize_student(student) for student in records] or list(students.values())}


@router.get("/alunos/{student_id}")
def get_student(student_id: str, user: Any = Depends(require_module_access("sead")), db: Session = Depends(get_db)):
    student = _db_scope_query(db, user).filter(models.Student.id == student_id).first()
    if not student:
        legacy = students.get(student_id)
        if not legacy:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        return {"module": "sead", "student": legacy}
    return {"module": "sead", "student": _serialize_student(student)}


@router.get("/matriculas")
def list_enrollments(user: Any = Depends(require_module_access("sead")), db: Session = Depends(get_db)):
    query = db.query(models.Enrollment)
    institution_id = getattr(user, "institution_id", None)
    if institution_id:
        query = query.filter(models.Enrollment.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        query = query.filter(models.Enrollment.campus_id == campus_id)
    records = query.options(joinedload(models.Enrollment.student), joinedload(models.Enrollment.campus)).all()
    return {"module": "sead", "items": [_serialize_enrollment(item) for item in records] or list(enrollments.values())}


@router.get("/processos")
def list_processes(user: Any = Depends(require_module_access("sead"))):
    processes = []
    for student_id, items in student_journey.items():
        for item in items:
            processes.append({
                "student_id": student_id,
                "student_name": students.get(student_id, {}).get("full_name"),
                **item,
            })
    return {"module": "sead", "items": processes}


@router.get("/documentos")
def list_documents(user: Any = Depends(require_module_access("sead"))):
    return {"module": "sead", "items": list(documents.values())}


@router.post("/processos")
def create_process(payload: AcademicRequestCreate, user: Any = Depends(require_module_access("sead"))):
    if payload.student_id not in students:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    process_item = {
        "id": f"REQ-{payload.student_id}-{len(student_journey.get(payload.student_id, [])) + 1:03d}",
        "stage": payload.category,
        "status": "em_analise",
        "date": "2026-11-01",
        "responsible": "sead",
        "details": payload.description,
        "type": payload.type,
        "priority": payload.priority,
        "due_date": payload.due_date,
    }

    student_journey.setdefault(payload.student_id, []).append(process_item)
    return {"module": "sead", "message": "Requerimento registrado na SEAD", "process": process_item}


@router.post("/matriculas")
def create_enrollment(payload: dict, user: Any = Depends(require_module_access("sead")), db: Session = Depends(get_db)):
    student_id = payload.get("student_id")
    student = None
    if student_id:
        student = _db_scope_query(db, user).filter(models.Student.id == student_id).first()
    if not student:
        legacy = students.get(student_id)
        if not legacy:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        student = legacy

    enrollment_id = payload.get("enrollment_id") or f"MAT-{len(enrollments) + 1:04d}"
    status_value = payload.get("status", "matriculado")
    if isinstance(student, dict):
        course_name = payload.get("course_name") or student.get("course") or "Sem curso vinculado"
    else:
        course_name = payload.get("course_name") or "Sem curso vinculado"

    campus_id = payload.get("campus_id")
    if isinstance(student, models.Student):
        campus_id = campus_id or student.campus_id
        institution_id = student.institution_id
        new_enrollment = models.Enrollment(
            id=enrollment_id,
            institution_id=institution_id,
            student_id=student.id,
            course_name=course_name,
            class_name=payload.get("class_name") or "Turma inicial",
            year=int(payload.get("year", 2026)),
            status=status_value,
            campus_id=campus_id,
        )
        db.add(new_enrollment)
        db.commit()
        db.refresh(new_enrollment)
        payload_enrollment = _serialize_enrollment(new_enrollment)
    else:
        enrollment = {
            "enrollment_id": enrollment_id,
            "student_id": payload["student_id"],
            "course_id": payload.get("course_id") or "CUR-ADS",
            "course_name": course_name,
            "period": payload.get("period", "2026/1"),
            "status": status_value,
            "campus": payload.get("campus") or students[payload["student_id"]].get("campus", "Campus Central"),
            "start_date": payload.get("start_date") or "2026-01-15",
            "contract_status": payload.get("contract_status", "em_validacao"),
            "responsible_financial_name": payload.get("responsible_financial_name") or students[payload["student_id"]].get("responsible_financial", "Responsável pendente"),
            "payment_plan": payload.get("payment_plan") or "anuidade_semestre",
            "documents_ok": status_value == "matriculado",
            "approved_by": "sead" if status_value == "matriculado" else None,
        }
        enrollments[enrollment_id] = enrollment
        payload_enrollment = enrollment

    if isinstance(student, dict):
        student["status"] = status_value
        student["enrollment_status"] = status_value
        student["period"] = payload.get("period", "2026/1")
        student_journey.setdefault(payload["student_id"], []).append({
            "id": f"JOU-{payload['student_id']}-{len(student_journey.get(payload['student_id'], [])) + 1}",
            "stage": "matricula",
            "status": status_value,
            "date": payload.get("start_date") or "2026-01-15",
            "responsible": "sead",
            "details": "Matrícula confirmada pela SEAD com vínculo acadêmico e financeiro integrado.",
        })

    return {"module": "sead", "message": "Matrícula registrada pela SEAD", "enrollment": payload_enrollment}
