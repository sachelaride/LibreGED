from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app import models
from app.auth import require_module_access
from app.database import get_db
from app.financial_services import (
    add_financial_audit,
    accessible_contracts_query,
    accessible_invoices_query,
    accessible_reviews_query,
    accessible_students_query,
    serialize_financial_contract,
    serialize_financial_invoice,
    serialize_financial_review,
)
from app.models_financial import (
    FinancialAcademicReview,
    FinancialContract,
    FinancialInvoice,
)
from app.modules.data_store import (
    courses,
    enrollments,
    financial_contracts,
    invoices,
    pending_actions,
    students,
)

router = APIRouter(prefix="/financeiro", tags=["Financeiro"])


def _db_scope_query(db: Session, user: Any):
    return accessible_students_query(db, user)


def _serialize_db_student(student: models.Student) -> dict[str, Any]:
    enrollments_count = len(student.enrollments or [])
    enrollment = student.enrollments[0] if student.enrollments else None
    return {
        "student_id": student.id,
        "person_id": None,
        "full_name": student.full_name,
        "cpf": student.cpf,
        "email": student.email,
        "status": "matriculado" if enrollments_count else "pendente",
        "course_id": enrollment.course_name if enrollment else None,
        "course": enrollment.course_name if enrollment else "Sem curso vinculado",
        "campus": student.campus.name if student.campus else None,
        "enrollment_status": "matriculado" if enrollments_count else "pendente",
        "document_status": "pendente",
        "responsible_financial": "Responsável pendente",
    }


def _serialize_db_enrollment(enrollment: models.Enrollment) -> dict[str, Any]:
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


def _resolve_student_context(db: Session, user: Any, student_id: str):
    student = _db_scope_query(db, user).filter(models.Student.id == student_id).first()
    if student:
        serialized = _serialize_db_student(student)
        enrollment = next(iter(student.enrollments or []), None)
        return serialized, _serialize_db_enrollment(enrollment) if enrollment else None
    if user.role != "admin_global" or user.institution_id or user.campus_id:
        return {}, None
    legacy_student = students.get(student_id)
    if legacy_student:
        legacy_enrollment = next((item for item in enrollments.values() if item.get("student_id") == student_id), None)
        return legacy_student, legacy_enrollment
    return {}, None


class InvoiceInput(BaseModel):
    student_id: str
    responsible_financial_id: str | None = Field(default=None, min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    due_date: date
    status: Literal["pendente"] = "pendente"
    plan: Literal[
        "mensalidade",
        "anuidade_semestre",
        "taxa_matricula",
        "personalizado",
    ] = "anuidade_semestre"
    installments_count: int = Field(default=1, ge=1, le=36)
    issuer: str = Field(default="Secretaria", max_length=120)
    payment_method: str = Field(default="boleto", max_length=40)
    responsible_financial: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_discount_and_installments(self):
        net_amount = self.amount - self.discount
        if self.discount >= self.amount:
            raise ValueError("O desconto deve ser menor que o valor total")
        if net_amount < Decimal(self.installments_count) / Decimal("100"):
            raise ValueError("O valor líquido não cobre o valor mínimo de cada parcela")
        return self


class InvoiceStatusUpdate(BaseModel):
    status: Literal["atrasado", "vencido", "quitado", "cancelado"]


class FinancialReviewResolution(BaseModel):
    resolution_note: str = Field(min_length=2, max_length=2000)

    @field_validator("resolution_note")
    @classmethod
    def normalize_resolution_note(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("A observação deve conter ao menos dois caracteres")
        return normalized


def _get_course_name(course_id: str | None) -> str:
    if not course_id:
        return "Curso não informado"
    course = courses.get(course_id)
    return course.get("name") if course else "Curso não informado"


def _get_student_enrollment(student_id: str):
    return next((item for item in enrollments.values() if item.get("student_id") == student_id), None)


def _build_invoice_view(invoice: dict[str, Any]) -> dict[str, Any]:
    student = students.get(invoice.get("student_id"), {})
    enrollment = _get_student_enrollment(invoice.get("student_id"))
    contract = financial_contracts.get(invoice.get("contract_id"))
    due_date = invoice.get("due_date")
    days_to_due = None
    if due_date:
        try:
            due = datetime.strptime(due_date, "%Y-%m-%d")
            days_to_due = (due.date() - datetime.utcnow().date()).days
        except ValueError:
            days_to_due = None

    return {
        **invoice,
        "student_name": student.get("full_name", "Aluno não identificado"),
        "course_id": invoice.get("course_id") or student.get("course_id"),
        "course_name": _get_course_name(invoice.get("course_id") or student.get("course_id")),
        "matricula_status": enrollment.get("status") if enrollment else "sem_matricula",
        "contract_status": contract.get("status", "indefinido") if contract else "indefinido",
        "responsible_name": student.get("responsible_financial", invoice.get("responsible_financial", "Responsável pendente")),
        "days_to_due": days_to_due,
    }


def _include_legacy_financial_data(user: Any) -> bool:
    return (
        user.role == "admin_global"
        and not user.institution_id
        and not user.campus_id
    )


def _installment_due_date(first_due_date: date, installment_index: int) -> date:
    month_index = first_due_date.month - 1 + installment_index
    year = first_due_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(first_due_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def _split_installment_amounts(
    total_amount: Decimal,
    installments_count: int,
) -> list[Decimal]:
    total_cents = int((total_amount * 100).quantize(Decimal("1")))
    base_cents, remainder_cents = divmod(total_cents, installments_count)
    return [
        Decimal(base_cents + (1 if index < remainder_cents else 0)) / Decimal("100")
        for index in range(installments_count)
    ]


def _invoice_due_date(invoice: dict[str, Any]) -> date | None:
    due_date = invoice.get("due_date")
    if isinstance(due_date, datetime):
        return due_date.date()
    if isinstance(due_date, date):
        return due_date
    if not isinstance(due_date, str) or not due_date:
        return None
    try:
        return date.fromisoformat(due_date)
    except ValueError:
        return None


@router.get("/dashboard")
def financeiro_dashboard(user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
    invoice_records = accessible_invoices_query(db, user).all()
    contract_records = accessible_contracts_query(db, user).all()
    pending_review_count = accessible_reviews_query(db, user).filter(
        FinancialAcademicReview.status == "pendente"
    ).count()
    invoice_values = [serialize_financial_invoice(item) for item in invoice_records]
    contract_values = [serialize_financial_contract(item) for item in contract_records]
    if _include_legacy_financial_data(user):
        persisted_student_ids = {item.student_id for item in invoice_records}
        persisted_contract_student_ids = {item.student_id for item in contract_records}
        invoice_values.extend(
            item for item in invoices.values()
            if item.get("student_id") not in persisted_student_ids
        )
        contract_values.extend(
            item for item in financial_contracts.values()
            if item.get("student_id") not in persisted_contract_student_ids
        )
    total_amount = sum(float(invoice["amount"]) for invoice in invoice_values)
    pending_amount = sum(float(invoice["amount"]) for invoice in invoice_values if invoice["status"] in {"pendente", "atrasado", "vencido"})
    paid_amount = sum(float(invoice["amount"]) for invoice in invoice_values if invoice["status"] == "quitado")
    active_contracts = sum(1 for contract in contract_values if contract.get("status") == "ativo")
    open_invoices = sum(1 for invoice in invoice_values if invoice.get("status") in {"pendente", "atrasado", "vencido"})
    today = date.today()
    due_soon_end = today + timedelta(days=7)
    overdue_invoices = [
        invoice for invoice in invoice_values
        if invoice.get("status") in {"atrasado", "vencido"}
        or (
            invoice.get("status") == "pendente"
            and (due_date := _invoice_due_date(invoice)) is not None
            and due_date < today
        )
    ]
    upcoming_invoices = [
        invoice for invoice in invoice_values
        if invoice.get("status") == "pendente"
        and (due_date := _invoice_due_date(invoice)) is not None
        and today <= due_date <= due_soon_end
    ]
    students_in_default = len({
        invoice["student_id"] for invoice in overdue_invoices
    })

    return {
        "module": "financeiro",
        "title": "Dashboard Financeiro",
        "stats": {
            "boletos_total": len(invoice_values),
            "pendentes": open_invoices,
            "quitados": sum(1 for invoice in invoice_values if invoice["status"] == "quitado"),
            "valor_total": round(total_amount, 2),
            "valor_em_aberto": round(pending_amount, 2),
            "valor_quitado": round(paid_amount, 2),
            "boletos_atrasados": len(overdue_invoices),
            "valor_em_atraso": round(sum(float(item["amount"]) for item in overdue_invoices), 2),
            "contratos_ativos": active_contracts,
            "revisoes_academicas_pendentes": pending_review_count,
            "alunos_em_atraso": students_in_default,
            "vencimentos_proximos": len(upcoming_invoices),
            "valor_vencimentos_proximos": round(
                sum(float(item["amount"]) for item in upcoming_invoices),
                2,
            ),
            "valor_medio": round(total_amount / len(invoice_values), 2) if invoice_values else 0.0,
        },
        "features": [
            "Cobranças",
            "Boletos",
            "Pagamentos",
            "Contratos e planos",
            "Relatórios financeiros",
            "Acompanhamento de inadimplência",
            "Integração com matrícula",
        ],
        "user": getattr(user, "username", None),
    }


@router.get("/boletos")
def list_invoices(user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
    items = [
        serialize_financial_invoice(invoice)
        for invoice in accessible_invoices_query(db, user).all()
    ]
    if _include_legacy_financial_data(user):
        persisted_student_ids = {item["student_id"] for item in items}
        legacy_invoices = (
            invoice for invoice in invoices.values()
            if invoice.get("student_id") not in persisted_student_ids
        )
    else:
        legacy_invoices = ()
    for invoice in legacy_invoices:
        student, enrollment = _resolve_student_context(db, user, invoice.get("student_id"))
        item = _build_invoice_view(invoice)
        if student:
            item["student_name"] = student.get("full_name", item["student_name"])
            item["course_id"] = item["course_id"] or student.get("course_id")
            item["course_name"] = _get_course_name(item["course_id"] or student.get("course_id"))
            item["responsible_name"] = student.get("responsible_financial", item["responsible_name"])
            if enrollment:
                item["matricula_status"] = enrollment.get("status", item["matricula_status"])
        items.append(item)
    return {"module": "financeiro", "items": items}


@router.get("/alunos/{student_id}/responsaveis-financeiros")
def list_student_financial_responsibles(
    student_id: str,
    user: Any = Depends(require_module_access("financeiro")),
    db: Session = Depends(get_db),
):
    student = _db_scope_query(db, user).filter(
        models.Student.id == student_id
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado no escopo financeiro")
    return {
        "module": "financeiro",
        "items": [
            {
                "id": guardian.id,
                "full_name": guardian.full_name,
                "relationship_type": guardian.relationship_type,
            }
            for guardian in student.guardians
        ],
    }


@router.get("/boletos/{invoice_id}")
def get_invoice(invoice_id: str, user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
    record = accessible_invoices_query(db, user).filter(
        FinancialInvoice.id == invoice_id
    ).first()
    if record:
        invoice = serialize_financial_invoice(record)
        invoice["contract"] = serialize_financial_contract(record.contract)
        invoice["enrollment"] = (
            _serialize_db_enrollment(record.enrollment)
            if record.enrollment else None
        )
        return {"module": "financeiro", "invoice": invoice}
    if not _include_legacy_financial_data(user):
        raise HTTPException(status_code=404, detail="Boleto não encontrado")
    invoice = invoices.get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")
    student, enrollment = _resolve_student_context(db, user, invoice["student_id"])
    return {
        "module": "financeiro",
        "invoice": {
            **_build_invoice_view(invoice),
            "student_name": student.get("full_name") if student else None,
            "course_name": _get_course_name((student or {}).get("course_id") or (student or {}).get("course")),
            "contract": financial_contracts.get(invoice.get("contract_id")),
            "enrollment": enrollment,
        },
    }


@router.get("/contratos")
def list_contracts(user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
    items = [
        serialize_financial_contract(contract)
        for contract in accessible_contracts_query(db, user).all()
    ]
    if not _include_legacy_financial_data(user):
        return {"module": "financeiro", "items": items}
    persisted_student_ids = {item["student_id"] for item in items}
    for contract in financial_contracts.values():
        if contract.get("student_id") in persisted_student_ids:
            continue
        student, _ = _resolve_student_context(db, user, contract.get("student_id"))
        student_payload = student or students.get(contract.get("student_id"), {})
        items.append({
            **contract,
            "student_name": student_payload.get("full_name", "Aluno não identificado"),
            "course_name": _get_course_name(contract.get("course_id") or student_payload.get("course_id") or student_payload.get("course")),
            "valor_liquido": round(float(contract.get("total_amount", 0)) - float(contract.get("discount", 0)), 2),
            "installments_count": 2,
        })
    return {"module": "financeiro", "items": items}


@router.get("/revisoes-academicas")
def list_academic_financial_reviews(
    status_filter: Literal["pendente", "resolvida"] | None = None,
    user: Any = Depends(require_module_access("financeiro")),
    db: Session = Depends(get_db),
):
    query = accessible_reviews_query(db, user)
    if status_filter:
        query = query.filter(FinancialAcademicReview.status == status_filter)
    records = query.order_by(
        FinancialAcademicReview.created_at.desc(),
        FinancialAcademicReview.id,
    ).all()
    return {
        "module": "financeiro",
        "items": [serialize_financial_review(item) for item in records],
    }


@router.patch("/revisoes-academicas/{review_id}/resolver")
def resolve_academic_financial_review(
    review_id: str,
    payload: FinancialReviewResolution,
    user: Any = Depends(require_module_access("financeiro")),
    db: Session = Depends(get_db),
):
    review = accessible_reviews_query(db, user).filter(
        FinancialAcademicReview.id == review_id,
    ).with_for_update(of=FinancialAcademicReview).first()
    if review is None:
        raise HTTPException(status_code=404, detail="Revisão financeira não encontrada")
    if review.status != "pendente":
        raise HTTPException(status_code=409, detail="A revisão financeira já foi resolvida")
    review.status = "resolvida"
    review.resolved_by = str(user.id)
    review.resolved_at = datetime.now(UTC).replace(tzinfo=None)
    review.resolution_note = payload.resolution_note.strip()
    add_financial_audit(
        db,
        entity="financial_academic_review",
        entity_id=review.id,
        action="financial_academic_review_resolved",
        details=f"review_type={review.review_type}; status=pendente->resolvida",
        user_id=str(user.id),
    )
    db.commit()
    db.refresh(review)
    return {
        "message": "Revisão financeira concluída",
        "module": "financeiro",
        "review": serialize_financial_review(review),
    }


@router.get("/pendencias")
def list_financial_pending(user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
    pending_items = []
    for item in pending_actions:
        student, _ = _resolve_student_context(db, user, item.get("student_id"))
        if not student:
            continue
        student_payload = student or students.get(item.get("student_id"), {})
        invoice = next((candidate for candidate in invoices.values() if candidate.get("student_id") == item.get("student_id")), None)
        pending_items.append({
            **item,
            "student_name": student_payload.get("full_name", "Aluno não identificado"),
            "course_name": _get_course_name(item.get("course_id") or student_payload.get("course_id") or student_payload.get("course")),
            "valor_pendente": float(invoice["amount"]) if invoice else 0.0,
            "responsible_financial": student_payload.get("responsible_financial", "Responsável pendente"),
        })
    return {"module": "financeiro", "items": pending_items}


@router.post("/boletos")
def create_invoice(payload: InvoiceInput, user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
    student = _db_scope_query(db, user).filter(
        models.Student.id == payload.student_id
    ).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado no escopo financeiro")
    responsible_guardian = None
    if payload.responsible_financial_id:
        responsible_guardian = db.query(models.Guardian).filter(
            models.Guardian.id == payload.responsible_financial_id,
            models.Guardian.student_id == student.id,
        ).first()
        if responsible_guardian is None:
            raise HTTPException(
                status_code=404,
                detail="Responsável financeiro não encontrado para este aluno",
            )
    enrollment = next(
        (
            item for item in student.enrollments
            if item.academic_class_id
            and item.institution_id == student.institution_id
            and (not student.campus_id or item.campus_id == student.campus_id)
            and item.status in {"active", "pending", "matriculado", "pendente", "ativo"}
        ),
        None,
    )
    course = None
    period = None
    if enrollment and enrollment.academic_class:
        offering = enrollment.academic_class.offering
        if (
            enrollment.academic_class.institution_id != student.institution_id
            or offering.institution_id != student.institution_id
            or offering.course.institution_id != student.institution_id
            or offering.campus_id != enrollment.campus_id
        ):
            raise HTTPException(
                status_code=409,
                detail="Matrícula vinculada fora do escopo institucional ou do campus",
            )
        course = offering.course
        period = offering.term.name
    responsible = (
        responsible_guardian.full_name
        if responsible_guardian
        else (payload.responsible_financial or "Responsável pendente")
    )
    net_amount = payload.amount - payload.discount
    contract = FinancialContract(
        id=uuid4().hex,
        institution_id=student.institution_id,
        student_id=student.id,
        responsible_financial_id=(
            responsible_guardian.id if responsible_guardian else None
        ),
        enrollment_id=enrollment.id if enrollment else None,
        course_id=course.id if course else None,
        period=period,
        status="em_validacao",
        plan=payload.plan,
        total_amount=payload.amount,
        discount=payload.discount,
        responsible_financial=responsible,
        created_by=user.id,
    )
    db.add(contract)
    installment_amounts = _split_installment_amounts(
        net_amount,
        payload.installments_count,
    )
    created_invoices = []
    for index, installment_amount in enumerate(installment_amounts):
        invoice = FinancialInvoice(
            id=uuid4().hex,
            institution_id=student.institution_id,
            student_id=student.id,
            responsible_financial_id=(
                responsible_guardian.id if responsible_guardian else None
            ),
            contract=contract,
            enrollment_id=enrollment.id if enrollment else None,
            course_id=course.id if course else None,
            amount=installment_amount,
            due_date=_installment_due_date(payload.due_date, index),
            status="pendente",
            issuer=payload.issuer,
            payment_method=payload.payment_method,
            installment=f"{index + 1}/{payload.installments_count}",
            responsible_financial=responsible,
            created_by=user.id,
        )
        db.add(invoice)
        created_invoices.append(invoice)
        add_financial_audit(
            db,
            entity="financial_invoice",
            entity_id=invoice.id,
            action="financial_invoice_created",
            details=(
                f"contract_id={contract.id}; installment={index + 1}/"
                f"{payload.installments_count}; amount={installment_amount:.2f}; "
                f"due_date={invoice.due_date.isoformat()}; status=pendente"
            ),
            user_id=user.id,
        )
    add_financial_audit(
        db,
        entity="financial_contract",
        entity_id=contract.id,
        action="financial_contract_created",
        details=(
            f"plan={contract.plan}; installments={payload.installments_count}; "
            f"total={payload.amount:.2f}; discount={payload.discount:.2f}; "
            f"net_total={net_amount:.2f}"
        ),
        user_id=user.id,
    )
    db.commit()
    for invoice in created_invoices:
        db.refresh(invoice)
    serialized_installments = [
        serialize_financial_invoice(invoice)
        for invoice in created_invoices
    ]
    return {
        "message": "Contrato e parcelas registrados",
        "module": "financeiro",
        "contract": serialize_financial_contract(contract),
        "invoice": serialized_installments[0],
        "installments": serialized_installments,
    }


@router.patch("/boletos/{invoice_id}/status")
def update_invoice_status(
    invoice_id: str,
    payload: InvoiceStatusUpdate,
    user: Any = Depends(require_module_access("financeiro")),
    db: Session = Depends(get_db),
):
    invoice = accessible_invoices_query(db, user).filter(
        FinancialInvoice.id == invoice_id
    ).with_for_update(of=FinancialInvoice).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    allowed_transitions = {
        "pendente": {"atrasado", "vencido", "quitado", "cancelado"},
        "atrasado": {"vencido", "quitado", "cancelado"},
        "vencido": {"quitado", "cancelado"},
    }
    if payload.status not in allowed_transitions.get(invoice.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Não é permitido alterar cobrança de {invoice.status} para {payload.status}",
        )
    if payload.status in {"atrasado", "vencido"} and invoice.due_date >= date.today():
        raise HTTPException(
            status_code=409,
            detail="A cobrança só pode ser marcada como atrasada após o vencimento",
        )

    previous_status = invoice.status
    invoice.status = payload.status
    invoice.payment_recorded_at = (
        datetime.now(UTC).replace(tzinfo=None)
        if payload.status == "quitado"
        else None
    )
    add_financial_audit(
        db,
        entity="financial_invoice",
        entity_id=invoice.id,
        action="financial_invoice_status_changed",
        details=f"status={previous_status}->{invoice.status}",
        user_id=user.id,
    )
    db.commit()
    db.refresh(invoice)
    return {
        "message": "Status da cobrança atualizado",
        "module": "financeiro",
        "invoice": serialize_financial_invoice(invoice),
    }
