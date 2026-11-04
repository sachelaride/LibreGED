import json
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models
from app.auth import require_module_access
from app.database import get_db
from app.financial_services import (
    accessible_contracts_query,
    accessible_invoices_query,
    serialize_financial_contract,
    serialize_financial_invoice,
)
from app.models_academic_catalog import (
    AcademicClass,
    AcademicCoordinationAction,
    AcademicCoordinatorAssignment,
    AcademicCourse,
    AcademicCreditRecognition,
    AcademicOffering,
    AcademicStaff,
)
from app.models_financial import FinancialContract, FinancialInvoice

router = APIRouter(prefix="/coordenacao", tags=["Coordenação"])


def _serialize_student(
    student: models.Student,
    scoped_enrollments: list[models.Enrollment],
) -> dict[str, Any]:
    primary_enrollment = scoped_enrollments[0] if scoped_enrollments else None
    offering = (
        primary_enrollment.academic_class.offering
        if primary_enrollment
        else None
    )
    return {
        "student_id": student.id,
        "full_name": student.full_name,
        "course": offering.course.name if offering else None,
        "campus": student.campus.name if student.campus else None,
        "status": primary_enrollment.status if primary_enrollment else None,
        "course_id": offering.course_id if offering else None,
        "matriculas": [
            _coordination_enrollment_response(enrollment)
            for enrollment in scoped_enrollments
        ],
    }


class PendingAction(BaseModel):
    student_id: str
    course_id: str | None = None
    issue: str = Field(min_length=2, max_length=500)
    priority: Literal["alta", "média", "baixa"] = "média"
    status: Literal["em andamento", "aguardando"] = "em andamento"
    responsible: str | None = Field(default=None, max_length=160)
    deadline: date | None = None
    category: str = Field(default="Documentação", min_length=2, max_length=120)


class CreditRecognitionDecision(BaseModel):
    status: Literal["approved", "rejected"]
    decision_note: str | None = Field(default=None, max_length=2000)


def _accessible_credit_recognitions(db: Session, user: Any):
    query = db.query(AcademicCreditRecognition).join(
        models.Student,
        models.Student.id == AcademicCreditRecognition.student_id,
    ).join(
        AcademicCourse,
        AcademicCourse.id == AcademicCreditRecognition.course_id,
    ).filter(
        AcademicCreditRecognition.institution_id == models.Student.institution_id,
        AcademicCreditRecognition.institution_id == AcademicCourse.institution_id,
    )
    manager_roles = {"admin_global", "admin_instituicao", "operador"}
    if user.role in manager_roles:
        if user.role != "admin_global" or user.institution_id:
            query = query.filter(AcademicCreditRecognition.institution_id == user.institution_id)
        if user.campus_id:
            query = query.filter(
                func.coalesce(models.Student.campus_id, AcademicCourse.campus_id) == user.campus_id
            )
        return query

    coordinator = db.query(AcademicStaff).filter(
        AcademicStaff.user_id == user.id,
        AcademicStaff.institution_id == user.institution_id,
        AcademicStaff.staff_type == "coordenador",
        AcademicStaff.status == "ativo",
    ).first()
    if coordinator is None:
        return query.filter(AcademicCreditRecognition.id == "")
    today = date.today()
    assignment_exists = db.query(AcademicCoordinatorAssignment.id).filter(
        AcademicCoordinatorAssignment.institution_id == AcademicCreditRecognition.institution_id,
        AcademicCoordinatorAssignment.coordinator_id == coordinator.id,
        AcademicCoordinatorAssignment.course_id == AcademicCreditRecognition.course_id,
        AcademicCoordinatorAssignment.campus_id
        == func.coalesce(models.Student.campus_id, AcademicCourse.campus_id),
        AcademicCoordinatorAssignment.starts_on <= today,
        AcademicCoordinatorAssignment.ends_on >= today,
    )
    query = query.filter(
        AcademicCreditRecognition.institution_id == user.institution_id,
        assignment_exists.exists(),
    )
    if user.campus_id:
        query = query.filter(
            func.coalesce(models.Student.campus_id, AcademicCourse.campus_id) == user.campus_id
        )
    return query


def _accessible_enrollments(db: Session, user: Any):
    query = (
        db.query(models.Enrollment)
        .join(models.Student, models.Student.id == models.Enrollment.student_id)
        .join(AcademicClass, AcademicClass.id == models.Enrollment.academic_class_id)
        .join(AcademicOffering, AcademicOffering.id == AcademicClass.offering_id)
        .join(AcademicCourse, AcademicCourse.id == AcademicOffering.course_id)
        .filter(
            models.Enrollment.institution_id == models.Student.institution_id,
            models.Enrollment.institution_id == AcademicClass.institution_id,
            models.Enrollment.institution_id == AcademicOffering.institution_id,
            models.Enrollment.campus_id == models.Student.campus_id,
            models.Student.campus_id == AcademicOffering.campus_id,
        )
    )
    manager_roles = {"admin_global", "admin_instituicao", "operador"}
    if user.role in manager_roles:
        if user.role != "admin_global" or user.institution_id:
            query = query.filter(models.Enrollment.institution_id == user.institution_id)
        if user.campus_id:
            query = query.filter(AcademicOffering.campus_id == user.campus_id)
        return query

    coordinator = db.query(AcademicStaff).filter(
        AcademicStaff.user_id == user.id,
        AcademicStaff.institution_id == user.institution_id,
        AcademicStaff.staff_type == "coordenador",
        AcademicStaff.status == "ativo",
    ).first()
    if coordinator is None:
        return query.filter(models.Enrollment.id == "")
    today = date.today()
    assignment_exists = db.query(AcademicCoordinatorAssignment.id).filter(
        AcademicCoordinatorAssignment.institution_id == models.Enrollment.institution_id,
        AcademicCoordinatorAssignment.coordinator_id == coordinator.id,
        AcademicCoordinatorAssignment.course_id == AcademicOffering.course_id,
        AcademicCoordinatorAssignment.campus_id == AcademicOffering.campus_id,
        AcademicCoordinatorAssignment.starts_on <= today,
        AcademicCoordinatorAssignment.ends_on >= today,
    )
    query = query.filter(
        models.Enrollment.institution_id == user.institution_id,
        assignment_exists.exists(),
    )
    if user.campus_id:
        query = query.filter(AcademicOffering.campus_id == user.campus_id)
    return query


def _accessible_pending_enrollments(db: Session, user: Any):
    return _accessible_enrollments(db, user).filter(
        models.Enrollment.status.in_(("pending", "pendente"))
    )


def _accessible_coordination_actions(db: Session, user: Any):
    query = (
        db.query(AcademicCoordinationAction)
        .join(models.Student, models.Student.id == AcademicCoordinationAction.student_id)
        .join(AcademicCourse, AcademicCourse.id == AcademicCoordinationAction.course_id)
        .join(models.Campus, models.Campus.id == AcademicCoordinationAction.campus_id)
        .filter(
            AcademicCoordinationAction.institution_id == models.Student.institution_id,
            AcademicCoordinationAction.institution_id == AcademicCourse.institution_id,
            AcademicCoordinationAction.institution_id == models.Campus.institution_id,
            AcademicCoordinationAction.campus_id == models.Student.campus_id,
            or_(
                AcademicCourse.campus_id.is_(None),
                AcademicCourse.campus_id == AcademicCoordinationAction.campus_id,
            ),
        )
    )
    manager_roles = {"admin_global", "admin_instituicao", "operador"}
    if user.role in manager_roles:
        if user.role != "admin_global" or user.institution_id:
            query = query.filter(
                AcademicCoordinationAction.institution_id == user.institution_id
            )
        if user.campus_id:
            query = query.filter(AcademicCoordinationAction.campus_id == user.campus_id)
        return query

    coordinator = db.query(AcademicStaff).filter(
        AcademicStaff.user_id == user.id,
        AcademicStaff.institution_id == user.institution_id,
        AcademicStaff.staff_type == "coordenador",
        AcademicStaff.status == "ativo",
    ).first()
    if coordinator is None:
        return query.filter(AcademicCoordinationAction.id == "")
    today = date.today()
    assignment_exists = db.query(AcademicCoordinatorAssignment.id).filter(
        AcademicCoordinatorAssignment.institution_id
        == AcademicCoordinationAction.institution_id,
        AcademicCoordinatorAssignment.coordinator_id == coordinator.id,
        AcademicCoordinatorAssignment.course_id == AcademicCoordinationAction.course_id,
        AcademicCoordinatorAssignment.campus_id == AcademicCoordinationAction.campus_id,
        AcademicCoordinatorAssignment.starts_on <= today,
        AcademicCoordinatorAssignment.ends_on >= today,
    )
    query = query.filter(
        AcademicCoordinationAction.institution_id == user.institution_id,
        assignment_exists.exists(),
    )
    if user.campus_id:
        query = query.filter(AcademicCoordinationAction.campus_id == user.campus_id)
    return query


def _coordination_action_response(action: AcademicCoordinationAction) -> dict[str, Any]:
    return {
        "id": action.id,
        "student_id": action.student_id,
        "student_name": action.student.full_name,
        "course_id": action.course_id,
        "course_name": action.course.name,
        "campus_id": action.campus_id,
        "campus_name": action.campus.name,
        "issue": action.issue,
        "priority": action.priority,
        "status": action.status,
        "responsible": action.responsible,
        "deadline": action.deadline.isoformat() if action.deadline is not None else None,
        "category": action.category,
        "created_by": action.created_by,
        "created_at": action.created_at,
        "resolved_by": action.resolved_by,
        "resolved_at": action.resolved_at,
    }


def _scoped_pending_actions(
    db: Session,
    user: Any,
    student_id: str | None = None,
) -> list[dict[str, Any]]:
    query = _accessible_coordination_actions(db, user)
    if student_id:
        query = query.filter(AcademicCoordinationAction.student_id == student_id)
    actions = query.order_by(
        AcademicCoordinationAction.created_at.desc(),
        AcademicCoordinationAction.id,
    ).all()
    return [_coordination_action_response(action) for action in actions]


def _coordination_enrollment_response(enrollment: models.Enrollment) -> dict[str, Any]:
    academic_class = enrollment.academic_class
    offering = academic_class.offering
    return {
        "enrollment_id": enrollment.id,
        "student_id": enrollment.student_id,
        "full_name": enrollment.student.full_name,
        "course_id": offering.course_id,
        "course": offering.course.name,
        "discipline_id": offering.discipline_id,
        "discipline": offering.discipline.name,
        "class_id": academic_class.id,
        "class": academic_class.code,
        "term_id": offering.term_id,
        "term": offering.term.name,
        "campus_id": offering.campus_id,
        "campus": offering.campus.name,
        "status": enrollment.status,
    }


def _integrated_enrollment_status(enrollment: models.Enrollment) -> str:
    if enrollment.status in {"active", "matriculado", "ativo"}:
        return "matriculado"
    if enrollment.status in {"pending", "pendente"}:
        return "pendente"
    return enrollment.status


def _pending_enrollment_response(enrollment: models.Enrollment) -> dict[str, Any]:
    academic_class = enrollment.academic_class
    offering = academic_class.offering
    return {
        "id": enrollment.id,
        "student_id": enrollment.student_id,
        "student_name": enrollment.student.full_name,
        "course_id": offering.course_id,
        "course_name": offering.course.name,
        "discipline_name": offering.discipline.name,
        "class_id": academic_class.id,
        "class_code": academic_class.code,
        "campus_id": offering.campus_id,
        "term_id": offering.term_id,
        "term_name": offering.term.name,
        "status": enrollment.status,
        "created_at": enrollment.created_at,
    }


def _credit_recognition_response(recognition: AcademicCreditRecognition) -> dict[str, Any]:
    target_discipline = (
        recognition.curriculum_discipline.discipline
        if recognition.curriculum_discipline
        else None
    )
    return {
        "id": recognition.id,
        "student_id": recognition.student_id,
        "student_name": recognition.student.full_name,
        "course_id": recognition.course_id,
        "course_name": recognition.course.name,
        "target_discipline": target_discipline.name if target_discipline else None,
        "source_institution": recognition.source_institution,
        "source_course": recognition.source_course,
        "source_discipline": recognition.source_discipline,
        "workload_hours": recognition.workload_hours,
        "credits": recognition.credits,
        "request_note": recognition.request_note,
        "status": recognition.status,
        "decision_note": recognition.decision_note,
        "reviewer_id": recognition.reviewer_id,
        "requested_at": recognition.requested_at,
        "decided_at": recognition.decided_at,
    }


def _audit_coordinator_decision(
    db: Session,
    user: Any,
    recognition: AcademicCreditRecognition,
    previous_status: str,
) -> None:
    from app.main import add_audit

    add_audit(
        db,
        "academic_credit_recognition",
        recognition.id,
        "coordinator_decision",
        json.dumps(
            {
                "before": previous_status,
                "after": recognition.status,
                "course_id": recognition.course_id,
            },
            sort_keys=True,
        ),
        str(user.id),
    )


def _audit_enrollment_approval(
    db: Session,
    user: Any,
    enrollment: models.Enrollment,
    previous_status: str,
) -> None:
    from app.main import add_audit

    academic_class = enrollment.academic_class
    add_audit(
        db,
        "enrollment",
        str(enrollment.id),
        "coordinator_approved",
        json.dumps(
            {
                "before": previous_status,
                "after": "active",
                "course_id": academic_class.offering.course_id,
                "campus_id": academic_class.offering.campus_id,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        str(user.id),
    )


def _audit_coordination_action(
    db: Session,
    user: Any,
    action: AcademicCoordinationAction,
    previous_status: str | None,
) -> None:
    from app.main import add_audit

    add_audit(
        db,
        "academic_coordination_action",
        str(action.id),
        "created" if previous_status is None else "resolved",
        json.dumps(
            {
                "before": previous_status,
                "after": str(action.status),
                "student_id": action.student_id,
                "course_id": action.course_id,
                "campus_id": action.campus_id,
                "priority": action.priority,
                "deadline": (
                    action.deadline.isoformat()
                    if action.deadline is not None
                    else None
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        str(user.id),
    )


@router.get("/dashboard")
def coordenacao_dashboard(user: Any = Depends(require_module_access("coordenacao")), db: Session = Depends(get_db)):
    scoped_enrollments = _accessible_enrollments(db, user).all()
    pending = _scoped_pending_actions(db, user)
    scoped_course_ids = {
        enrollment.academic_class.offering.course_id
        for enrollment in scoped_enrollments
    }
    scoped_class_ids = {
        enrollment.academic_class.id
        for enrollment in scoped_enrollments
    }
    scoped_courses = [
        {
            "id": course.id,
            "code": course.code,
            "name": course.name,
        }
        for course in db.query(AcademicCourse).filter(
            AcademicCourse.id.in_(scoped_course_ids),
            AcademicCourse.status == "ativo",
        ).order_by(AcademicCourse.name).all()
    ] if scoped_course_ids else []
    scoped_classes = [
        {
            "id": academic_class.id,
            "code": academic_class.code,
            "course_id": academic_class.offering.course_id,
            "course_name": academic_class.offering.course.name,
            "discipline_name": academic_class.offering.discipline.name,
            "campus_id": academic_class.offering.campus_id,
        }
        for academic_class in db.query(AcademicClass).filter(
            AcademicClass.id.in_(scoped_class_ids),
            AcademicClass.status == "ativa",
        ).order_by(AcademicClass.code).all()
    ] if scoped_class_ids else []
    stats = {
        "pendencias": len(pending),
        "prioridade_alta": sum(1 for p in pending if str(p["priority"]).lower() == "alta"),
        "prioridade_media": sum(1 for p in pending if str(p["priority"]).lower() == "média"),
        "em_andamento": sum(1 for p in pending if str(p.get("status", "aberta")).lower() == "em andamento"),
        "concluidas": sum(1 for p in pending if str(p.get("status", "aberta")).lower() == "concluída"),
        "alunos_em_risco": sum(1 for p in pending if str(p.get("priority", "")).lower() in {"alta", "média"}),
        "cursos_ativos": len(scoped_courses),
        "turmas_ativas": len(scoped_classes),
        "matriculas_pendentes": sum(
            1 for enrollment in scoped_enrollments
            if enrollment.status in {"pending", "pendente"}
        ),
    }
    return {
        "module": "coordenacao",
        "title": "Dashboard da Coordenação",
        "stats": stats,
        "courses": scoped_courses,
        "classes": scoped_classes,
        "features": [
            "Validação curricular",
            "Pendências acadêmicas",
            "Monitoramento de alunos",
            "Relatórios institucionais",
            "Acompanhamento de matrícula",
        ],
        "user": getattr(user, "username", None),
    }


@router.get("/alunos")
def list_coordination_students(user: Any = Depends(require_module_access("coordenacao")), db: Session = Depends(get_db)):
    records = _accessible_enrollments(db, user).order_by(
        models.Student.full_name,
        AcademicCourse.name,
        AcademicOffering.discipline_id,
        AcademicClass.code,
    ).all()
    return {
        "module": "coordenacao",
        "items": [_coordination_enrollment_response(record) for record in records],
    }


@router.get("/pendencias")
def list_pending_actions(
    user: Any = Depends(require_module_access("coordenacao")),
    db: Session = Depends(get_db),
):
    return {
        "module": "coordenacao",
        "items": _scoped_pending_actions(db, user),
    }


@router.get("/solicitacoes-aproveitamento")
def list_credit_recognition_requests(
    status_filter: Literal["pending", "approved", "rejected"] | None = None,
    user: Any = Depends(require_module_access("coordenacao")),
    db: Session = Depends(get_db),
):
    query = _accessible_credit_recognitions(db, user)
    if status_filter:
        query = query.filter(AcademicCreditRecognition.status == status_filter)
    records = query.order_by(AcademicCreditRecognition.requested_at.desc()).all()
    return {
        "module": "coordenacao",
        "items": [_credit_recognition_response(record) for record in records],
    }


@router.patch("/solicitacoes-aproveitamento/{recognition_id}/decisao")
def decide_credit_recognition(
    recognition_id: str,
    payload: CreditRecognitionDecision,
    user: Any = Depends(require_module_access("coordenacao")),
    db: Session = Depends(get_db),
):
    recognition = (
        _accessible_credit_recognitions(db, user)
        .filter(AcademicCreditRecognition.id == recognition_id)
        .with_for_update()
        .first()
    )
    if recognition is None:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada no escopo da coordenação")
    if recognition.status != "pending":
        raise HTTPException(status_code=409, detail="A solicitação já recebeu uma decisão")

    recognition.status = payload.status
    recognition.decision_note = payload.decision_note
    recognition.reviewer_id = str(user.id)
    recognition.decided_at = datetime.now(UTC).replace(tzinfo=None)
    _audit_coordinator_decision(db, user, recognition, "pending")
    db.commit()
    db.refresh(recognition)
    return {
        "module": "coordenacao",
        "decision": _credit_recognition_response(recognition),
    }


@router.get("/matriculas-pendentes")
def list_pending_enrollment_approvals(
    user: Any = Depends(require_module_access("coordenacao")),
    db: Session = Depends(get_db),
):
    records = _accessible_pending_enrollments(db, user).order_by(
        models.Enrollment.created_at,
        models.Enrollment.id,
    ).all()
    return {
        "module": "coordenacao",
        "items": [_pending_enrollment_response(record) for record in records],
    }


@router.get("/integracao")
def integrated_student_flow(user: Any = Depends(require_module_access("coordenacao")), db: Session = Depends(get_db)):
    result = []
    scoped_enrollments = _accessible_enrollments(db, user).all()
    for academic_enrollment in scoped_enrollments:
        student_id = academic_enrollment.student_id
        student = academic_enrollment.student
        student_data = {
            "student_id": student_id,
            "full_name": student.full_name,
            "course": academic_enrollment.academic_class.offering.course.name,
            "campus": student.campus.name if student.campus else None,
        }
        course_id = academic_enrollment.academic_class.offering.course_id
        pending = _scoped_pending_actions(db, user, str(student_id))
        invoice_entries = [
            serialize_financial_invoice(item)
            for item in accessible_invoices_query(db, user).filter(
                FinancialInvoice.student_id == student_id,
                FinancialInvoice.course_id == course_id,
            ).all()
        ]
        contract_entries = [
            serialize_financial_contract(item)
            for item in accessible_contracts_query(db, user).filter(
                FinancialContract.student_id == student_id,
                FinancialContract.course_id == course_id,
            ).all()
        ]
        result.append({
            "student_id": student_id,
            "student": student_data,
            "academic_enrollment": _coordination_enrollment_response(academic_enrollment),
            "enrollment": _coordination_enrollment_response(academic_enrollment),
            "pendencias": pending,
            "boletos": invoice_entries,
            "contratos": contract_entries,
            "status_integrado": _integrated_enrollment_status(academic_enrollment),
        })
    return {"module": "coordenacao", "items": result}


@router.get("/matriculas/{student_id}/integracao")
def get_student_integration(student_id: str, user: Any = Depends(require_module_access("coordenacao")), db: Session = Depends(get_db)):
    scoped_enrollments = _accessible_enrollments(db, user).filter(
        models.Enrollment.student_id == student_id
    ).all()
    if not scoped_enrollments:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    student = scoped_enrollments[0].student
    scoped_course_ids = {
        item.academic_class.offering.course_id
        for item in scoped_enrollments
    }
    financial = {
        "boletos": [
            serialize_financial_invoice(item)
            for item in accessible_invoices_query(db, user).filter(
                FinancialInvoice.student_id == student_id,
                FinancialInvoice.course_id.in_(scoped_course_ids),
            ).all()
        ],
        "contratos": [
            serialize_financial_contract(item)
            for item in accessible_contracts_query(db, user).filter(
                FinancialContract.student_id == student_id,
                FinancialContract.course_id.in_(scoped_course_ids),
            ).all()
        ],
    }
    return {
        "module": "coordenacao",
        "student_id": student_id,
        "student": _serialize_student(student, scoped_enrollments),
        "academic_enrollments": [
            _coordination_enrollment_response(item)
            for item in scoped_enrollments
        ],
        "enrollment": _coordination_enrollment_response(scoped_enrollments[0]),
        "pendencias": _scoped_pending_actions(db, user, student_id),
        "financeiro": financial,
    }


@router.get("/pendencias/{student_id}")
def get_pending_action(
    student_id: str,
    course_id: str | None = None,
    action_id: str | None = None,
    user: Any = Depends(require_module_access("coordenacao")),
    db: Session = Depends(get_db),
):
    query = _accessible_coordination_actions(db, user).filter(
        AcademicCoordinationAction.student_id == student_id
    )
    if course_id is not None:
        query = query.filter(AcademicCoordinationAction.course_id == course_id)
    if action_id is not None:
        query = query.filter(AcademicCoordinationAction.id == action_id)
    matching_actions = [
        _coordination_action_response(action)
        for action in query.order_by(AcademicCoordinationAction.created_at.desc()).all()
    ]
    if not matching_actions:
        raise HTTPException(status_code=404, detail="Pendência não encontrada no escopo da coordenação")
    if len(matching_actions) > 1:
        raise HTTPException(status_code=409, detail="Informe o ID da pendência para identificá-la")
    return {
        "module": "coordenacao",
        "pending": matching_actions[0],
    }


@router.post("/pendencias")
def create_pending_action(
    payload: PendingAction,
    user: Any = Depends(require_module_access("coordenacao")),
    db: Session = Depends(get_db),
):
    query = _accessible_enrollments(db, user).filter(
        models.Enrollment.student_id == payload.student_id
    )
    if payload.course_id:
        query = query.filter(AcademicOffering.course_id == payload.course_id)
    scoped_enrollments = query.all()
    if not scoped_enrollments:
        raise HTTPException(status_code=404, detail="Aluno ou curso não encontrado no escopo da coordenação")
    scoped_course_ids = {
        item.academic_class.offering.course_id
        for item in scoped_enrollments
    }
    if len(scoped_course_ids) > 1 and not payload.course_id:
        raise HTTPException(status_code=422, detail="Informe o curso da pendência para este aluno")
    course_id = payload.course_id or next(iter(scoped_course_ids))
    enrollment = next(
        item for item in scoped_enrollments
        if item.academic_class.offering.course_id == course_id
    )
    action = AcademicCoordinationAction(
        id=str(uuid4()),
        institution_id=enrollment.institution_id,
        student_id=enrollment.student_id,
        course_id=course_id,
        campus_id=enrollment.academic_class.offering.campus_id,
        issue=payload.issue,
        priority=payload.priority,
        status=payload.status,
        responsible=payload.responsible or getattr(user, "username", "Coordenação acadêmica"),
        deadline=payload.deadline,
        category=payload.category,
        created_by=str(user.id),
    )
    db.add(action)
    _audit_coordination_action(db, user, action, None)
    db.commit()
    db.refresh(action)
    return {
        "message": "Pendência registrada",
        "module": "coordenacao",
        "pending": _coordination_action_response(action),
    }


@router.post("/matriculas/{enrollment_id}/aprovar")
def approve_student_enrollment(
    enrollment_id: str,
    user: Any = Depends(require_module_access("coordenacao")),
    db: Session = Depends(get_db),
):
    enrollment = (
        _accessible_enrollments(db, user)
        .filter(models.Enrollment.id == enrollment_id)
        .with_for_update()
        .first()
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada no escopo da coordenação")
    previous_status = str(enrollment.status)
    if previous_status not in {"pending", "pendente"}:
        raise HTTPException(status_code=409, detail="A matrícula não está pendente de aprovação")
    updated_rows = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.id == enrollment_id,
            models.Enrollment.status == previous_status,
        )
        .update(
            {models.Enrollment.status: "active"},
            synchronize_session=False,
        )
    )
    if updated_rows != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="A matrícula já foi alterada por outra operação")
    _audit_enrollment_approval(
        db,
        user,
        enrollment,
        previous_status,
    )
    db.commit()
    db.refresh(enrollment)
    return {
        "message": "Matrícula aprovada pela coordenação",
        "module": "coordenacao",
        "student_id": enrollment.student_id,
        "status": enrollment.status,
        "enrollment": {
            "id": enrollment.id,
            "student_id": enrollment.student_id,
            "course_name": enrollment.course_name,
            "status": enrollment.status,
        },
        "previous_status": previous_status,
    }


@router.post("/pendencias/{student_id}/resolver")
def resolve_pending_action(
    student_id: str,
    course_id: str | None = None,
    action_id: str | None = None,
    user: Any = Depends(require_module_access("coordenacao")),
    db: Session = Depends(get_db),
):
    query = _accessible_coordination_actions(db, user).filter(
        AcademicCoordinationAction.student_id == student_id
    )
    if course_id is not None:
        query = query.filter(AcademicCoordinationAction.course_id == course_id)
    if action_id is not None:
        query = query.filter(AcademicCoordinationAction.id == action_id)
    matching_actions = query.order_by(
        AcademicCoordinationAction.created_at,
        AcademicCoordinationAction.id,
    ).with_for_update().all()
    if not matching_actions:
        raise HTTPException(status_code=404, detail="Pendência não encontrada no escopo da coordenação")
    if len(matching_actions) > 1:
        raise HTTPException(status_code=409, detail="Informe o ID da pendência para identificá-la")
    pending = matching_actions[0]
    if pending.status == "concluída":
        raise HTTPException(status_code=409, detail="A pendência já foi concluída")
    previous_status = str(pending.status)
    resolved_at = datetime.now(UTC).replace(tzinfo=None)
    updated_rows = (
        db.query(AcademicCoordinationAction)
        .filter(
            AcademicCoordinationAction.id == pending.id,
            AcademicCoordinationAction.status == previous_status,
        )
        .update(
            {
                AcademicCoordinationAction.status: "concluída",
                AcademicCoordinationAction.responsible: getattr(
                    user,
                    "username",
                    "Coordenação",
                ),
                AcademicCoordinationAction.resolved_by: str(user.id),
                AcademicCoordinationAction.resolved_at: resolved_at,
            },
            synchronize_session=False,
        )
    )
    if updated_rows != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="A pendência foi alterada por outra operação")
    db.refresh(pending)
    _audit_coordination_action(db, user, pending, previous_status)
    db.commit()
    db.refresh(pending)
    return {
        "message": "Pendência resolvida",
        "module": "coordenacao",
        "student_id": student_id,
        "course_id": pending.course_id,
        "pending": _coordination_action_response(pending),
    }
