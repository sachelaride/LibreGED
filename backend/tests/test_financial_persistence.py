from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app import models
from app.auth import create_access_token, get_current_active_user
from app.database import SessionLocal
from app.main import app
from app.models_academic_catalog import (
    AcademicClass,
    AcademicCourse,
    AcademicDiscipline,
    AcademicOffering,
    AcademicTerm,
)
from app.models_financial import FinancialContract, FinancialInvoice


client = TestClient(app)


def _headers(module: str = "financeiro") -> dict[str, str]:
    token = create_access_token({
        "sub": "finance-test",
        "role": "admin_global",
        "module": module,
    })
    return {"Authorization": f"Bearer {token}"}


def _create_student() -> str:
    student_id = uuid4().hex
    with SessionLocal() as db:
        institution = db.query(models.Institution).first()
        db.add(models.Student(
            id=student_id,
            institution_id=institution.id,
            full_name="Estudante Financeiro",
            birth_date="2001-02-03",
            cpf=f"9{uuid4().int % 10**10:010d}",
            email=f"finance-{student_id}@example.test",
        ))
        db.commit()
    return student_id


def _create_guardian(student_id: str, name: str) -> str:
    guardian_id = uuid4().hex
    with SessionLocal() as db:
        db.add(models.Guardian(
            id=guardian_id,
            student_id=student_id,
            full_name=name,
            cpf=f"8{uuid4().int % 10**10:010d}",
            email=f"guardian-{guardian_id}@example.test",
            relationship_type="responsável financeiro",
        ))
        db.commit()
    return guardian_id


def _create_enrolled_student() -> tuple[str, str, str]:
    student_id = uuid4().hex
    enrollment_id = uuid4().hex
    campus_id = uuid4().hex
    course_id = uuid4().hex
    discipline_id = uuid4().hex
    term_id = uuid4().hex
    offering_id = uuid4().hex
    class_id = uuid4().hex
    with SessionLocal() as db:
        institution = db.query(models.Institution).first()
        db.add(models.Campus(
            id=campus_id,
            institution_id=institution.id,
            name="Campus Financeiro",
        ))
        db.add(AcademicCourse(
            id=course_id,
            institution_id=institution.id,
            campus_id=campus_id,
            code=f"FIN-{course_id[:8]}",
            name="Curso Financeiro",
            degree="Bacharelado",
            modality="presencial",
            duration_periods=8,
            status="ativo",
        ))
        db.add(AcademicDiscipline(
            id=discipline_id,
            institution_id=institution.id,
            code=f"DISC-{discipline_id[:8]}",
            name="Disciplina Financeira",
            workload_hours=60,
            credits=4,
            status="ativo",
        ))
        db.add(AcademicTerm(
            id=term_id,
            institution_id=institution.id,
            code=f"FIN-{term_id[:8]}",
            name="2026.2",
            starts_on=date.today(),
            ends_on=date.today() + timedelta(days=180),
            status="ativo",
        ))
        db.add(AcademicOffering(
            id=offering_id,
            institution_id=institution.id,
            course_id=course_id,
            discipline_id=discipline_id,
            term_id=term_id,
            campus_id=campus_id,
            capacity=30,
            status="aberta",
        ))
        db.add(AcademicClass(
            id=class_id,
            institution_id=institution.id,
            offering_id=offering_id,
            code=f"FIN-{class_id[:8]}",
            capacity=30,
            status="ativa",
        ))
        db.add(models.Student(
            id=student_id,
            institution_id=institution.id,
            campus_id=campus_id,
            full_name="Estudante com Matrícula",
            birth_date="2001-02-03",
            cpf=f"9{uuid4().int % 10**10:010d}",
            email=f"finance-{student_id}@example.test",
        ))
        db.add(models.Enrollment(
            id=enrollment_id,
            institution_id=institution.id,
            student_id=student_id,
            academic_class_id=class_id,
            course_name="Curso Financeiro",
            class_name=f"FIN-{class_id[:8]}",
            year=date.today().year,
            status="active",
            campus_id=campus_id,
        ))
        db.commit()
    return student_id, enrollment_id, course_id


def test_finance_invoice_and_contract_are_persisted_and_visible_to_finance():
    student_id = _create_student()

    created = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "1000.01",
            "discount": "100.00",
            "plan": "mensalidade",
            "installments_count": 3,
            "due_date": "2027-01-31",
        },
    )
    assert created.status_code == 200, created.text
    invoice = created.json()["invoice"]
    assert invoice["student_id"] == student_id
    assert invoice["amount"] == 300.01
    assert invoice["status"] == "pendente"
    assert invoice["matricula_status"] == "sem_matricula"
    assert invoice["contract_status"] == "em_validacao"
    installments = created.json()["installments"]
    assert len(installments) == 3
    assert [item["installment"] for item in installments] == ["1/3", "2/3", "3/3"]
    assert [item["amount"] for item in installments] == [300.01, 300.0, 300.0]
    assert [item["due_date"] for item in installments] == [
        "2027-01-31",
        "2027-02-28",
        "2027-03-31",
    ]

    listed_invoices = client.get("/financeiro/boletos", headers=_headers())
    assert listed_invoices.status_code == 200, listed_invoices.text
    assert {
        item["invoice_id"] for item in listed_invoices.json()["items"]
    } == {item["invoice_id"] for item in installments}

    details = client.get(
        f"/financeiro/boletos/{invoice['invoice_id']}",
        headers=_headers(),
    )
    assert details.status_code == 200, details.text
    assert details.json()["invoice"]["contract"]["contract_id"] == invoice["contract_id"]

    listed_contracts = client.get("/financeiro/contratos", headers=_headers())
    assert listed_contracts.status_code == 200, listed_contracts.text
    assert len(listed_contracts.json()["items"]) == 1
    assert listed_contracts.json()["items"][0]["contract_id"] == invoice["contract_id"]
    assert listed_contracts.json()["items"][0]["discount"] == 100
    assert listed_contracts.json()["items"][0]["installments_count"] == 3

    with SessionLocal() as db:
        assert db.get(FinancialInvoice, invoice["invoice_id"]) is not None
        contract = db.get(FinancialContract, invoice["contract_id"])
        assert contract is not None
        assert contract.student_id == student_id
        creation_audit = db.query(models.AuditEvent).filter(
            models.AuditEvent.entity == "financial_invoice",
            models.AuditEvent.entity_id == invoice["invoice_id"],
        ).one()
        assert creation_audit.action == "financial_invoice_created"
        assert creation_audit.user_id == "test-admin-id"

    invalid_status = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "1250.75",
            "due_date": "2027-01-15",
            "status": "invalido",
        },
    )
    assert invalid_status.status_code == 422
    paid_at_creation = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "1250.75",
            "due_date": "2027-01-15",
            "status": "quitado",
        },
    )
    assert paid_at_creation.status_code == 422
    invalid_discount = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "100.00",
            "discount": "100.00",
            "due_date": "2027-01-15",
        },
    )
    assert invalid_discount.status_code == 422
    unrepresentable_schedule = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "0.02",
            "installments_count": 3,
            "due_date": "2027-01-15",
        },
    )
    assert unrepresentable_schedule.status_code == 422

    premature_overdue = client.patch(
        f"/financeiro/boletos/{invoice['invoice_id']}/status",
        headers=_headers(),
        json={"status": "atrasado"},
    )
    assert premature_overdue.status_code == 409

    payment = client.patch(
        f"/financeiro/boletos/{invoice['invoice_id']}/status",
        headers=_headers(),
        json={"status": "quitado"},
    )
    assert payment.status_code == 200, payment.text
    assert payment.json()["invoice"]["status"] == "quitado"
    assert payment.json()["invoice"]["payment_recorded_at"]

    repeated_payment = client.patch(
        f"/financeiro/boletos/{invoice['invoice_id']}/status",
        headers=_headers(),
        json={"status": "cancelado"},
    )
    assert repeated_payment.status_code == 409
    with SessionLocal() as db:
        audit_events = db.query(models.AuditEvent).filter(
            models.AuditEvent.entity == "financial_invoice",
            models.AuditEvent.entity_id == invoice["invoice_id"],
        ).order_by(models.AuditEvent.created_at).all()
        assert [event.action for event in audit_events] == [
            "financial_invoice_created",
            "financial_invoice_status_changed",
        ]
        assert "pendente->quitado" in audit_events[-1].details


def test_invoice_links_financial_responsible_only_from_the_students_guardians():
    student_id = _create_student()
    guardian_id = _create_guardian(student_id, "Responsável do Aluno")
    other_student_id = _create_student()
    other_guardian_id = _create_guardian(other_student_id, "Outro Responsável")

    responsible_list = client.get(
        f"/financeiro/alunos/{student_id}/responsaveis-financeiros",
        headers=_headers(),
    )
    assert responsible_list.status_code == 200, responsible_list.text
    assert responsible_list.json()["items"] == [{
        "id": guardian_id,
        "full_name": "Responsável do Aluno",
        "relationship_type": "responsável financeiro",
    }]

    rejected = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "responsible_financial_id": other_guardian_id,
            "amount": "250.00",
            "due_date": "2027-01-15",
        },
    )
    assert rejected.status_code == 404

    created = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "responsible_financial_id": guardian_id,
            "amount": "250.00",
            "due_date": "2027-01-15",
        },
    )
    assert created.status_code == 200, created.text
    invoice = created.json()["invoice"]
    assert invoice["responsible_financial_id"] == guardian_id
    assert invoice["responsible_financial"] == "Responsável do Aluno"
    assert created.json()["contract"]["responsible_financial_id"] == guardian_id

    with SessionLocal() as db:
        assert db.get(FinancialInvoice, invoice["invoice_id"]).responsible_financial_id == guardian_id
        assert db.get(
            FinancialContract,
            created.json()["contract"]["contract_id"],
        ).responsible_financial_id == guardian_id


def test_invoice_links_to_the_students_current_academic_enrollment():
    student_id, enrollment_id, course_id = _create_enrolled_student()
    created = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "850.00",
            "due_date": "2027-01-15",
        },
    )
    assert created.status_code == 200, created.text
    invoice = created.json()["invoice"]
    assert invoice["enrollment_id"] == enrollment_id
    assert invoice["course_id"] == course_id
    assert invoice["period"] == "2026.2"

    with SessionLocal() as db:
        persisted = db.get(FinancialInvoice, invoice["invoice_id"])
        contract = db.get(FinancialContract, invoice["contract_id"])
        assert persisted.enrollment_id == enrollment_id
        assert persisted.course_id == course_id
        assert contract.enrollment_id == enrollment_id
        assert contract.course_id == course_id


def test_financial_dashboard_separates_overdue_and_upcoming_invoices():
    student_id = _create_student()
    before_response = client.get("/financeiro/dashboard", headers=_headers())
    assert before_response.status_code == 200, before_response.text
    before = before_response.json()["stats"]

    invoice_ids = []
    for amount in ("100.00", "200.00", "300.00"):
        created = client.post(
            "/financeiro/boletos",
            headers=_headers(),
            json={
                "student_id": student_id,
                "amount": amount,
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
            },
        )
        assert created.status_code == 200, created.text
        invoice_ids.append(created.json()["invoice"]["invoice_id"])

    with SessionLocal() as db:
        overdue, upcoming, distant = (
            db.get(FinancialInvoice, invoice_id) for invoice_id in invoice_ids
        )
        overdue.due_date = date.today() - timedelta(days=1)
        upcoming.due_date = date.today() + timedelta(days=7)
        distant.due_date = date.today() + timedelta(days=8)
        db.commit()

    after_response = client.get("/financeiro/dashboard", headers=_headers())
    assert after_response.status_code == 200, after_response.text
    after = after_response.json()["stats"]
    assert after["boletos_atrasados"] - before["boletos_atrasados"] == 1
    assert after["valor_em_atraso"] - before["valor_em_atraso"] == 100
    assert after["alunos_em_atraso"] - before["alunos_em_atraso"] == 1
    assert after["vencimentos_proximos"] - before["vencimentos_proximos"] == 1
    assert (
        after["valor_vencimentos_proximos"]
        - before["valor_vencimentos_proximos"]
        == 200
    )


def test_cancelling_enrollment_cancels_future_unpaid_installments():
    student_id, enrollment_id, _course_id = _create_enrolled_student()
    created = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "900.00",
            "installments_count": 3,
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert created.status_code == 200, created.text
    invoice_ids = {
        item["invoice_id"] for item in created.json()["installments"]
    }

    cancelled = client.post(
        f"/secretaria/matriculas/{enrollment_id}/status",
        headers=_headers("secretaria"),
        json={"status": "cancelado"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["financial_effects"] == {
        "cancelled_future_installments": 3,
    }
    with SessionLocal() as db:
        invoices_after = db.query(FinancialInvoice).filter(
            FinancialInvoice.id.in_(invoice_ids),
        ).all()
        assert {item.status for item in invoices_after} == {"cancelado"}
        contract = db.get(FinancialContract, created.json()["contract"]["contract_id"])
        assert contract.status == "cancelado"
        audit_count = db.query(models.AuditEvent).filter(
            models.AuditEvent.action == "financial_invoice_cancelled_by_academic_change",
            models.AuditEvent.entity_id.in_(invoice_ids),
        ).count()
        assert audit_count == 3


def test_leaving_enrollment_preserves_paid_and_overdue_and_cancels_future_unpaid():
    student_id, enrollment_id, _course_id = _create_enrolled_student()
    created = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "1200.00",
            "installments_count": 3,
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert created.status_code == 200, created.text
    installments = created.json()["installments"]
    with SessionLocal() as db:
        overdue = db.get(FinancialInvoice, installments[0]["invoice_id"])
        paid = db.get(FinancialInvoice, installments[1]["invoice_id"])
        overdue.due_date = date.today() - timedelta(days=1)
        overdue.status = "vencido"
        paid.status = "quitado"
        paid.payment_recorded_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()

    leave = client.post(
        f"/secretaria/matriculas/{enrollment_id}/status",
        headers=_headers("secretaria"),
        json={"status": "trancado"},
    )
    assert leave.status_code == 200, leave.text
    assert leave.json()["financial_effects"] == {
        "cancelled_future_installments": 1,
    }
    with SessionLocal() as db:
        assert db.get(FinancialInvoice, installments[0]["invoice_id"]).status == "vencido"
        assert db.get(FinancialInvoice, installments[1]["invoice_id"]).status == "quitado"
        assert db.get(FinancialInvoice, installments[2]["invoice_id"]).status == "cancelado"
        contract = db.get(FinancialContract, created.json()["contract"]["contract_id"])
        assert contract.status == "em_validacao"


def test_cancelling_enrollment_does_not_cancel_fully_paid_contract():
    student_id, enrollment_id, _course_id = _create_enrolled_student()
    created = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "500.00",
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert created.status_code == 200, created.text
    invoice = created.json()["invoice"]
    with SessionLocal() as db:
        paid_invoice = db.get(FinancialInvoice, invoice["invoice_id"])
        paid_invoice.status = "quitado"
        paid_invoice.payment_recorded_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()

    cancelled = client.post(
        f"/secretaria/matriculas/{enrollment_id}/status",
        headers=_headers("secretaria"),
        json={"status": "cancelado"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["financial_effects"] == {
        "cancelled_future_installments": 0,
    }
    with SessionLocal() as db:
        contract = db.get(FinancialContract, invoice["contract_id"])
        assert contract.status == "em_validacao"


def test_finance_routes_do_not_expose_records_outside_user_institution():
    student_id = _create_student()
    _create_guardian(student_id, "Responsável protegido")
    created = client.post(
        "/financeiro/boletos",
        headers=_headers(),
        json={
            "student_id": student_id,
            "amount": "100.00",
            "due_date": "2027-01-15",
        },
    )
    assert created.status_code == 200, created.text

    previous_override = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: models.User(
        id="finance-scoped-user",
        username="finance-scoped-user",
        hashed_password="not-used",
        role="admin_instituicao",
        institution_id="another-institution",
        is_active=True,
    )
    scoped_headers = {
        "Authorization": "Bearer " + create_access_token({
            "sub": "finance-scoped-user",
            "role": "admin_instituicao",
            "module": "financeiro",
        })
    }
    try:
        listed = client.get("/financeiro/boletos", headers=scoped_headers)
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"] == []

        hidden_guardians = client.get(
            f"/financeiro/alunos/{student_id}/responsaveis-financeiros",
            headers=scoped_headers,
        )
        assert hidden_guardians.status_code == 404

        rejected = client.post(
            "/financeiro/boletos",
            headers=scoped_headers,
            json={
                "student_id": student_id,
                "amount": "100.00",
                "due_date": "2027-01-15",
            },
        )
        assert rejected.status_code == 404

        review_list = client.get(
            "/financeiro/revisoes-academicas",
            headers=scoped_headers,
        )
        assert review_list.status_code == 200, review_list.text
        assert review_list.json()["items"] == []
    finally:
        if previous_override:
            app.dependency_overrides[get_current_active_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_active_user, None)
