from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app import models
from app.auth import require_module_access
from app.database import get_db
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
    query = db.query(models.Student).options(
        joinedload(models.Student.campus),
        joinedload(models.Student.enrollments),
    )
    institution_id = getattr(user, "institution_id", None)
    if institution_id:
        query = query.filter(models.Student.institution_id == institution_id)
    campus_id = getattr(user, "campus_id", None)
    if campus_id:
        query = query.filter(models.Student.campus_id == campus_id)
    return query


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
    legacy_student = students.get(student_id)
    if legacy_student:
        legacy_enrollment = next((item for item in enrollments.values() if item.get("student_id") == student_id), None)
        return legacy_student, legacy_enrollment
    return {}, None


class InvoiceInput(BaseModel):
    student_id: str
    amount: float
    due_date: str
    status: str | None = None
    issuer: str | None = None
    payment_method: str | None = None
    installment: str | None = None


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


@router.get("/dashboard")
def financeiro_dashboard(user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
    invoice_values = list(invoices.values())
    scoped_students = _db_scope_query(db, user).all()
    if scoped_students:
        invoice_values = [
            invoice for invoice in invoice_values
            if any(student.id == invoice.get("student_id") for student in scoped_students)
            or invoice.get("student_id") in {student.id for student in scoped_students}
        ] or invoice_values
    total_amount = sum(float(invoice["amount"]) for invoice in invoice_values)
    pending_amount = sum(float(invoice["amount"]) for invoice in invoice_values if invoice["status"] in {"pendente", "atrasado", "vencido"})
    paid_amount = sum(float(invoice["amount"]) for invoice in invoice_values if invoice["status"] == "quitado")
    active_contracts = sum(1 for contract in financial_contracts.values() if contract.get("status") == "ativo")
    open_invoices = sum(1 for invoice in invoice_values if invoice.get("status") in {"pendente", "atrasado", "vencido"})
    students_in_default = len({invoice["student_id"] for invoice in invoice_values if invoice.get("status") in {"pendente", "atrasado", "vencido"}})
    due_soon = sum(1 for invoice in invoice_values if invoice.get("status") in {"pendente", "atrasado"} and invoice.get("due_date"))

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
            "contratos_ativos": active_contracts,
            "alunos_em_atraso": students_in_default,
            "vencimentos_proximos": due_soon,
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
    items = []
    for invoice in invoices.values():
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


@router.get("/boletos/{invoice_id}")
def get_invoice(invoice_id: str, user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
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
    items = []
    for contract in financial_contracts.values():
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


@router.get("/pendencias")
def list_financial_pending(user: Any = Depends(require_module_access("financeiro")), db: Session = Depends(get_db)):
    pending_items = []
    for item in pending_actions:
        student, _ = _resolve_student_context(db, user, item.get("student_id"))
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
    invoice_id = f"INV-{len(invoices) + 1:02d}"
    contract_id = f"CTR-{payload.student_id.split('-')[-1]}-{len(financial_contracts) + 1:02d}"
    student, _ = _resolve_student_context(db, user, payload.student_id)
    student_payload = student or students.get(payload.student_id, {})
    invoice = {
        "invoice_id": invoice_id,
        "student_id": payload.student_id,
        "amount": payload.amount,
        "due_date": payload.due_date,
        "status": payload.status or "pendente",
        "issuer": payload.issuer or "Secretaria",
        "payment_method": payload.payment_method or "boleto",
        "installment": payload.installment or "1/1",
        "contract_id": contract_id,
        "course_id": student_payload.get("course_id", "CUR-DEFAULT") or student_payload.get("course") or "CUR-DEFAULT",
        "responsible_financial": student_payload.get("responsible_financial", "Responsável pendente"),
    }
    invoices[invoice_id] = invoice
    financial_contracts[contract_id] = {
        "contract_id": contract_id,
        "student_id": payload.student_id,
        "course_id": student_payload.get("course_id", "CUR-DEFAULT") or student_payload.get("course") or "CUR-DEFAULT",
        "period": "2026/1",
        "status": "ativo",
        "plan": "anuidade_semestre",
        "total_amount": payload.amount,
        "discount": 0.0,
        "responsible_financial": invoice["responsible_financial"],
        "signed_at": payload.due_date,
    }
    return {"message": "Boleto gerado", "module": "financeiro", "invoice": _build_invoice_view(invoice)}
