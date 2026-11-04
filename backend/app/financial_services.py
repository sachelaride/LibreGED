from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, false, func, or_
from sqlalchemy.orm import Session, joinedload

from app import models
from app.models_academic_catalog import AcademicCourse
from app.models_financial import (
    FinancialAcademicReview,
    FinancialContract,
    FinancialInvoice,
)


def accessible_students_query(db: Session, user: Any):
    query = db.query(models.Student).options(
        joinedload(models.Student.campus),
        joinedload(models.Student.enrollments),
    )
    institution_id = getattr(user, "institution_id", None)
    if user.role != "admin_global" and not institution_id:
        return query.filter(false())
    if institution_id:
        query = query.filter(models.Student.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        query = query.filter(models.Student.campus_id == campus_id)
    return query


def _accessible_financial_query(db: Session, user: Any, model: Any):
    query = db.query(model).join(
        models.Student,
        model.student_id == models.Student.id,
    ).outerjoin(
        models.Enrollment,
        model.enrollment_id == models.Enrollment.id,
    ).outerjoin(
        AcademicCourse,
        model.course_id == AcademicCourse.id,
    )
    institution_id = getattr(user, "institution_id", None)
    if user.role != "admin_global" and not institution_id:
        return query.filter(false())
    if institution_id:
        query = query.filter(model.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        query = query.filter(
            func.coalesce(
                models.Student.campus_id,
                models.Enrollment.campus_id,
                AcademicCourse.campus_id,
            ) == campus_id
        )
    return query.filter(
        model.institution_id == models.Student.institution_id,
        or_(
            model.enrollment_id.is_(None),
            and_(
                models.Enrollment.student_id == model.student_id,
                models.Enrollment.institution_id == model.institution_id,
            ),
        ),
        or_(
            model.course_id.is_(None),
            AcademicCourse.institution_id == model.institution_id,
        ),
    )


def accessible_invoices_query(db: Session, user: Any):
    return _accessible_financial_query(db, user, FinancialInvoice).options(
        joinedload(FinancialInvoice.student),
        joinedload(FinancialInvoice.course),
        joinedload(FinancialInvoice.enrollment),
        joinedload(FinancialInvoice.contract),
    )


def accessible_contracts_query(db: Session, user: Any):
    return _accessible_financial_query(db, user, FinancialContract).options(
        joinedload(FinancialContract.student),
        joinedload(FinancialContract.course),
        joinedload(FinancialContract.enrollment),
    )


def accessible_reviews_query(db: Session, user: Any):
    query = db.query(FinancialAcademicReview).join(
        models.Student,
        FinancialAcademicReview.student_id == models.Student.id,
    ).join(
        models.Enrollment,
        FinancialAcademicReview.enrollment_id == models.Enrollment.id,
    )
    institution_id = getattr(user, "institution_id", None)
    if user.role != "admin_global" and not institution_id:
        return query.filter(false())
    if institution_id:
        query = query.filter(
            FinancialAcademicReview.institution_id == institution_id
        )
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        query = query.filter(
            func.coalesce(models.Student.campus_id, models.Enrollment.campus_id)
            == campus_id
        )
    return query.filter(
        FinancialAcademicReview.institution_id == models.Student.institution_id,
        FinancialAcademicReview.student_id == models.Enrollment.student_id,
        FinancialAcademicReview.institution_id == models.Enrollment.institution_id,
    )


def serialize_financial_invoice(invoice: FinancialInvoice) -> dict[str, Any]:
    return {
        "invoice_id": invoice.id,
        "student_id": invoice.student_id,
        "responsible_financial_id": invoice.responsible_financial_id,
        "amount": float(invoice.amount),
        "due_date": invoice.due_date.isoformat(),
        "status": invoice.status,
        "payment_recorded_at": (
            invoice.payment_recorded_at.isoformat()
            if invoice.payment_recorded_at else None
        ),
        "issuer": invoice.issuer,
        "payment_method": invoice.payment_method,
        "installment": invoice.installment,
        "contract_id": invoice.contract_id,
        "enrollment_id": invoice.enrollment_id,
        "course_id": invoice.course_id,
        "period": invoice.contract.period,
        "responsible_financial": invoice.responsible_financial,
        "student_name": invoice.student.full_name,
        "course_name": invoice.course.name if invoice.course else None,
        "matricula_status": invoice.enrollment.status if invoice.enrollment else "sem_matricula",
        "contract_status": invoice.contract.status,
        "responsible_name": invoice.responsible_financial,
        "days_to_due": (invoice.due_date - date.today()).days,
    }


def serialize_financial_contract(contract: FinancialContract) -> dict[str, Any]:
    return {
        "contract_id": contract.id,
        "student_id": contract.student_id,
        "responsible_financial_id": contract.responsible_financial_id,
        "enrollment_id": contract.enrollment_id,
        "course_id": contract.course_id,
        "period": contract.period,
        "status": contract.status,
        "plan": contract.plan,
        "total_amount": float(contract.total_amount),
        "discount": float(contract.discount),
        "responsible_financial": contract.responsible_financial,
        "signed_at": contract.signed_at.isoformat() if contract.signed_at else None,
        "student_name": contract.student.full_name,
        "course_name": contract.course.name if contract.course else None,
        "valor_liquido": float(contract.total_amount - contract.discount),
        "installments_count": len(contract.invoices),
    }


def add_financial_audit(
    db: Session,
    *,
    entity: str,
    entity_id: str,
    action: str,
    details: str,
    user_id: str,
) -> None:
    db.flush()
    event_id = uuid4().hex
    last_event = db.query(models.AuditEvent).order_by(
        models.AuditEvent.created_at.desc(),
        models.AuditEvent.id.desc(),
    ).first()
    previous_hash = last_event.hash_signature if last_event else "genesis"
    signature = sha256(
        f"{event_id}:{entity}:{entity_id}:{action}:{details}:{user_id}:{previous_hash}".encode()
    ).hexdigest()
    db.add(models.AuditEvent(
        id=event_id,
        entity=entity,
        entity_id=entity_id,
        action=action,
        details=details,
        user_id=user_id,
        hash_signature=signature,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    ))


def apply_enrollment_financial_policy(
    db: Session,
    enrollment: models.Enrollment,
    new_status: str,
    user_id: str,
) -> int:
    normalized_status = new_status.strip().lower()
    if normalized_status not in {
        "cancelado",
        "cancelada",
        "canceled",
        "trancado",
        "trancada",
    }:
        return 0

    today = date.today()
    future_invoices = db.query(FinancialInvoice).filter(
        FinancialInvoice.enrollment_id == enrollment.id,
        FinancialInvoice.institution_id == enrollment.institution_id,
        FinancialInvoice.status == "pendente",
        FinancialInvoice.due_date > today,
    ).with_for_update().all()
    affected_contracts: set[str] = set()
    for invoice in future_invoices:
        invoice.status = "cancelado"
        affected_contracts.add(invoice.contract_id)
        add_financial_audit(
            db,
            entity="financial_invoice",
            entity_id=invoice.id,
            action="financial_invoice_cancelled_by_academic_change",
            details=(
                f"enrollment_id={enrollment.id}; enrollment_status={normalized_status}; "
                f"rule=future_unpaid_installment_cancelled; due_date={invoice.due_date.isoformat()}"
            ),
            user_id=user_id,
        )

    if normalized_status in {"cancelado", "cancelada", "canceled"}:
        contract_ids = db.query(FinancialContract.id).filter(
            FinancialContract.enrollment_id == enrollment.id,
            FinancialContract.institution_id == enrollment.institution_id,
        ).all()
        affected_contracts.update(contract_id for (contract_id,) in contract_ids)
        for contract_id in affected_contracts:
            contract = db.query(FinancialContract).filter(
                FinancialContract.id == contract_id,
            ).with_for_update().first()
            if contract is None or contract.status == "cancelado":
                continue
            invoice_statuses = {
                status for (status,) in db.query(FinancialInvoice.status).filter(
                    FinancialInvoice.contract_id == contract.id,
                ).all()
            }
            if (
                "cancelado" in invoice_statuses
                and invoice_statuses <= {"quitado", "cancelado"}
            ):
                previous_status = contract.status
                contract.status = "cancelado"
                add_financial_audit(
                    db,
                    entity="financial_contract",
                    entity_id=contract.id,
                    action="financial_contract_cancelled_by_academic_change",
                    details=(
                        f"enrollment_id={enrollment.id}; "
                        f"status={previous_status}->cancelado"
                    ),
                    user_id=user_id,
                )
    return len(future_invoices)


def create_transfer_financial_review(
    db: Session,
    user: Any,
    source: models.Enrollment,
    target: models.Enrollment,
) -> FinancialAcademicReview:
    review = FinancialAcademicReview(
        id=uuid4().hex,
        institution_id=source.institution_id,
        student_id=source.student_id,
        enrollment_id=source.id,
        review_type="transferencia",
        status="pendente",
        details=f"Revisar cobranças e contrato antes de concluir a transferência para {target.id}.",
        created_by=str(user.id),
    )
    db.add(review)
    add_financial_audit(
        db,
        entity="financial_academic_review",
        entity_id=review.id,
        action="financial_transfer_review_requested",
        details=(
            f"source_enrollment_id={source.id}; "
            f"target_enrollment_id={target.id}"
        ),
        user_id=str(user.id),
    )
    return review


def serialize_financial_review(review: FinancialAcademicReview) -> dict[str, Any]:
    return {
        "id": review.id,
        "review_type": review.review_type,
        "status": review.status,
        "details": review.details,
        "institution_id": review.institution_id,
        "student_id": review.student_id,
        "student_name": review.student.full_name,
        "enrollment_id": review.enrollment_id,
        "enrollment_status": review.enrollment.status,
        "created_by": review.created_by,
        "created_at": review.created_at.isoformat(),
        "resolved_by": review.resolved_by,
        "resolved_at": review.resolved_at.isoformat() if review.resolved_at else None,
        "resolution_note": review.resolution_note,
    }
