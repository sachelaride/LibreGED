from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app import models
from app.auth import create_access_token, get_current_active_user
from app.database import SessionLocal
from app.main import app
from app.models_academic_catalog import (
    AcademicCoordinatorAssignment,
    AcademicClass,
    AcademicCoordinationAction,
    AcademicCourse,
    AcademicCreditRecognition,
    AcademicCurriculum,
    AcademicCurriculumDiscipline,
    AcademicDiscipline,
    AcademicOffering,
    AcademicStaff,
    AcademicTerm,
)


client = TestClient(app)


def _headers(role: str = "academico") -> dict[str, str]:
    token = create_access_token({
        "sub": "coordinator-test",
        "role": role,
        "module": "coordenacao",
    })
    return {"Authorization": f"Bearer {token}"}


def _create_request_scope():
    with SessionLocal() as db:
        institution = db.query(models.Institution).first()
        campus_id = uuid4().hex
        user_id = uuid4().hex
        staff_id = uuid4().hex
        course_id = uuid4().hex
        unrelated_course_id = uuid4().hex
        discipline_id = uuid4().hex
        unrelated_discipline_id = uuid4().hex
        curriculum_id = uuid4().hex
        curriculum_discipline_id = uuid4().hex
        student_id = uuid4().hex
        recognition_id = uuid4().hex
        term_id = uuid4().hex
        offering_id = uuid4().hex
        unrelated_offering_id = uuid4().hex
        class_id = uuid4().hex
        unrelated_class_id = uuid4().hex
        enrollment_id = uuid4().hex
        unrelated_enrollment_id = uuid4().hex
        db.add(models.Campus(
            id=campus_id,
            institution_id=institution.id,
            name="Campus coordenação",
        ))
        db.add(models.User(
            id=user_id,
            username="coordinator-test",
            hashed_password="not-used",
            role="academico",
            institution_id=institution.id,
            campus_id=campus_id,
            is_active=True,
        ))
        db.add(AcademicStaff(
            id=staff_id,
            institution_id=institution.id,
            campus_id=campus_id,
            user_id=user_id,
            staff_code="COORD-TEST",
            full_name="Coordenador de teste",
            email="coordenador-test@example.test",
            staff_type="coordenador",
            status="ativo",
        ))
        db.add(AcademicCourse(
            id=course_id,
            institution_id=institution.id,
            campus_id=campus_id,
            code="CUR-COORD",
            name="Curso para decisão",
            degree="Bacharelado",
            modality="presencial",
            duration_periods=8,
            status="ativo",
        ))
        db.add(AcademicCourse(
            id=unrelated_course_id,
            institution_id=institution.id,
            campus_id=campus_id,
            code="CUR-OUTRO",
            name="Curso sem atribuição",
            degree="Bacharelado",
            modality="presencial",
            duration_periods=8,
            status="ativo",
        ))
        db.add(AcademicDiscipline(
            id=discipline_id,
            institution_id=institution.id,
            code="DISC-COORD",
            name="Disciplina de destino",
            workload_hours=60,
            credits=4,
            status="ativo",
        ))
        db.add(AcademicDiscipline(
            id=unrelated_discipline_id,
            institution_id=institution.id,
            code="DISC-OUTRA",
            name="Disciplina sem atribuição",
            workload_hours=60,
            credits=4,
            status="ativo",
        ))
        db.add(AcademicTerm(
            id=term_id,
            institution_id=institution.id,
            code=f"TERM-{term_id[:8]}",
            name="Período de teste",
            starts_on=date.today() - timedelta(days=1),
            ends_on=date.today() + timedelta(days=180),
            status="aberto",
        ))
        db.flush()
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
        db.flush()
        db.add(AcademicClass(
            id=class_id,
            institution_id=institution.id,
            offering_id=offering_id,
            code=f"TUR-{class_id[:8]}",
            capacity=30,
            status="ativa",
        ))
        db.add(AcademicOffering(
            id=unrelated_offering_id,
            institution_id=institution.id,
            course_id=unrelated_course_id,
            discipline_id=unrelated_discipline_id,
            term_id=term_id,
            campus_id=campus_id,
            capacity=30,
            status="aberta",
        ))
        db.flush()
        db.add(AcademicClass(
            id=unrelated_class_id,
            institution_id=institution.id,
            offering_id=unrelated_offering_id,
            code=f"OUTRO-{unrelated_class_id[:8]}",
            capacity=30,
            status="ativa",
        ))
        db.add(AcademicCurriculum(
            id=curriculum_id,
            institution_id=institution.id,
            course_id=course_id,
            version="2026",
            effective_from=date(2026, 1, 1),
            status="ativa",
        ))
        db.flush()
        db.add(AcademicCurriculumDiscipline(
            id=curriculum_discipline_id,
            curriculum_id=curriculum_id,
            discipline_id=discipline_id,
            term_number=1,
            is_required=True,
        ))
        db.add(models.Student(
            id=student_id,
            institution_id=institution.id,
            campus_id=campus_id,
            full_name="Estudante da solicitação",
            birth_date="2005-01-01",
            cpf=f"7{uuid4().int % 10**10:010d}",
            email=f"student-{student_id}@example.test",
        ))
        db.add(AcademicCoordinatorAssignment(
            id=uuid4().hex,
            institution_id=institution.id,
            coordinator_id=staff_id,
            course_id=course_id,
            campus_id=campus_id,
            starts_on=date.today() - timedelta(days=1),
            ends_on=date.today() + timedelta(days=30),
        ))
        db.flush()
        db.add(AcademicCreditRecognition(
            id=recognition_id,
            institution_id=institution.id,
            student_id=student_id,
            course_id=course_id,
            curriculum_discipline_id=curriculum_discipline_id,
            source_institution="Instituição de origem",
            source_course="Curso anterior",
            source_discipline="Disciplina cursada",
            workload_hours=60,
            credits=4,
            request_note="Solicito análise",
            status="pending",
        ))
        db.add(models.Enrollment(
            id=enrollment_id,
            institution_id=institution.id,
            student_id=student_id,
            academic_class_id=class_id,
            course_name="Curso para decisão",
            class_name=f"TUR-{class_id[:8]}",
            year=date.today().year,
            status="pendente",
            campus_id=campus_id,
        ))
        db.add(models.Enrollment(
            id=unrelated_enrollment_id,
            institution_id=institution.id,
            student_id=student_id,
            academic_class_id=unrelated_class_id,
            course_name="Curso sem atribuição",
            class_name=f"OUTRO-{unrelated_class_id[:8]}",
            year=date.today().year,
            status="active",
            campus_id=campus_id,
        ))
        db.commit()
        return institution.id, user_id, campus_id, recognition_id, enrollment_id


def test_coordinator_can_decide_pending_credit_request_within_current_assignment():
    institution_id, user_id, campus_id, recognition_id, _enrollment_id = _create_request_scope()
    coordinator_user = models.User(
        id=user_id,
        username="coordinator-test",
        hashed_password="not-used",
        role="academico",
        institution_id=institution_id,
        campus_id=campus_id,
        is_active=True,
    )
    previous_override = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: coordinator_user
    headers = _headers()
    try:
        academic_students = client.get("/coordenacao/alunos", headers=headers)
        assert academic_students.status_code == 200, academic_students.text
        assert len(academic_students.json()["items"]) == 1
        academic_student = academic_students.json()["items"][0]
        assert academic_student["student_id"]
        assert academic_student["course"] == "Curso para decisão"
        assert academic_student["discipline"] == "Disciplina de destino"
        assert academic_student["class"].startswith("TUR-")

        student_integration = client.get(
            f"/coordenacao/matriculas/{academic_student['student_id']}/integracao",
            headers=headers,
        )
        assert student_integration.status_code == 200, student_integration.text
        scoped_academic_links = student_integration.json()["academic_enrollments"]
        assert len(scoped_academic_links) == 1
        assert scoped_academic_links[0]["course_id"] == academic_student["course_id"]
        assert len(student_integration.json()["student"]["matriculas"]) == 1

        dashboard = client.get("/coordenacao/dashboard", headers=headers)
        assert dashboard.status_code == 200, dashboard.text
        assert dashboard.json()["stats"]["cursos_ativos"] == 1
        assert dashboard.json()["stats"]["turmas_ativas"] == 1
        assert dashboard.json()["stats"]["matriculas_pendentes"] == 1
        assert [course["id"] for course in dashboard.json()["courses"]] == [
            academic_student["course_id"]
        ]

        requests = client.get("/coordenacao/solicitacoes-aproveitamento", headers=headers)
        assert requests.status_code == 200, requests.text
        assert [item["id"] for item in requests.json()["items"]] == [recognition_id]
        assert requests.json()["items"][0]["target_discipline"] == "Disciplina de destino"

        decision = client.patch(
            f"/coordenacao/solicitacoes-aproveitamento/{recognition_id}/decisao",
            headers=headers,
            json={"status": "approved", "decision_note": "Carga horária e conteúdo compatíveis."},
        )
        assert decision.status_code == 200, decision.text
        assert decision.json()["decision"]["status"] == "approved"
        assert decision.json()["decision"]["reviewer_id"] == user_id

        repeated_decision = client.patch(
            f"/coordenacao/solicitacoes-aproveitamento/{recognition_id}/decisao",
            headers=headers,
            json={"status": "rejected"},
        )
        assert repeated_decision.status_code == 409

        approved_requests = client.get(
            "/coordenacao/solicitacoes-aproveitamento?status_filter=approved",
            headers=headers,
        )
        assert [item["id"] for item in approved_requests.json()["items"]] == [recognition_id]

        with SessionLocal() as db:
            audit = db.query(models.AuditEvent).filter_by(
                entity="academic_credit_recognition",
                entity_id=recognition_id,
                action="coordinator_decision",
            ).first()
            assert audit is not None
    finally:
        if previous_override:
            app.dependency_overrides[get_current_active_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_active_user, None)


def test_coordinator_without_assigned_courses_cannot_read_or_decide_request():
    institution_id, coordinator_id, _campus_id, recognition_id, enrollment_id = _create_request_scope()
    unassigned_user_id = uuid4().hex
    with SessionLocal() as db:
        db.add(models.User(
            id=unassigned_user_id,
            username="unassigned-coordinator",
            hashed_password="not-used",
            role="academico",
            institution_id=institution_id,
            is_active=True,
        ))
        db.commit()

    unassigned_user = models.User(
        id=unassigned_user_id,
        username="unassigned-coordinator",
        hashed_password="not-used",
        role="academico",
        institution_id=institution_id,
        campus_id=None,
        is_active=True,
    )
    previous_override = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: unassigned_user
    headers = _headers()
    try:
        requests = client.get("/coordenacao/solicitacoes-aproveitamento", headers=headers)
        assert requests.status_code == 200, requests.text
        assert requests.json()["items"] == []

        academic_students = client.get("/coordenacao/alunos", headers=headers)
        assert academic_students.status_code == 200, academic_students.text
        assert academic_students.json()["items"] == []
        assert client.get("/coordenacao/pendencias", headers=headers).json()["items"] == []

        pending_enrollments = client.get("/coordenacao/matriculas-pendentes", headers=headers)
        assert pending_enrollments.status_code == 200, pending_enrollments.text
        assert pending_enrollments.json()["items"] == []

        decision = client.patch(
            f"/coordenacao/solicitacoes-aproveitamento/{recognition_id}/decisao",
            headers=headers,
            json={"status": "rejected"},
        )
        assert decision.status_code == 404

        approval = client.post(
            f"/coordenacao/matriculas/{enrollment_id}/aprovar",
            headers=headers,
        )
        assert approval.status_code == 404
        with SessionLocal() as db:
            enrollment = db.query(models.Enrollment).filter_by(id=enrollment_id).one()
            student_id = enrollment.student_id
            course_id = enrollment.academic_class.offering.course_id
            db.add(AcademicCoordinationAction(
                id=uuid4().hex,
                institution_id=enrollment.institution_id,
                student_id=student_id,
                course_id=course_id,
                campus_id=enrollment.campus_id,
                issue="Pendência de curso sem atribuição",
                priority="alta",
                status="em andamento",
                responsible="Coordenação",
                category="Teste",
                created_by=coordinator_id,
            ))
            db.commit()
        assert client.get(
            "/coordenacao/pendencias",
            headers=headers,
        ).json()["items"] == []
        assert client.post(
            f"/coordenacao/pendencias/{student_id}/resolver",
            headers=headers,
            params={"course_id": course_id},
        ).status_code == 404
        pending_creation = client.post(
            "/coordenacao/pendencias",
            headers=headers,
            json={
                "student_id": student_id,
                "issue": "Ação fora do escopo de curso",
            },
        )
        assert pending_creation.status_code == 404
    finally:
        if previous_override:
            app.dependency_overrides[get_current_active_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_active_user, None)


def test_coordinator_pending_action_is_linked_to_assigned_course():
    institution_id, user_id, campus_id, _recognition_id, _enrollment_id = _create_request_scope()
    coordinator_user = models.User(
        id=user_id,
        username="coordinator-test",
        hashed_password="not-used",
        role="academico",
        institution_id=institution_id,
        campus_id=campus_id,
        is_active=True,
    )
    with SessionLocal() as db:
        student = db.query(models.Student).filter_by(full_name="Estudante da solicitação").one()
        student_id = student.id
        course_id = db.query(AcademicCourse.id).filter_by(name="Curso para decisão").scalar()

    previous_override = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: coordinator_user
    headers = _headers()
    try:
        created = client.post(
            "/coordenacao/pendencias",
            headers=headers,
            json={
                "student_id": student_id,
                "course_id": course_id,
                "issue": "Analisar documentação",
            },
        )
        assert created.status_code == 200, created.text
        action = created.json()["pending"]
        action_id = action["id"]
        assert action["course_id"] == course_id
        assert action["course_name"] == "Curso para decisão"
        assert action["student_name"] == "Estudante da solicitação"
        assert action["created_by"] == user_id

        pending_list = client.get("/coordenacao/pendencias", headers=headers)
        assert pending_list.status_code == 200, pending_list.text
        matching = next(
            item for item in pending_list.json()["items"]
            if item["id"] == action_id
        )
        assert matching["course_name"] == "Curso para decisão"

        detail = client.get(
            f"/coordenacao/pendencias/{student_id}",
            headers=headers,
            params={"course_id": course_id, "action_id": action_id},
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["pending"]["id"] == action_id

        resolved = client.post(
            f"/coordenacao/pendencias/{student_id}/resolver",
            headers=headers,
            params={"course_id": course_id, "action_id": action_id},
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["pending"]["status"] == "concluída"
        assert resolved.json()["pending"]["responsible"] == "coordinator-test"
        assert resolved.json()["pending"]["resolved_by"] == user_id

        repeated_resolution = client.post(
            f"/coordenacao/pendencias/{student_id}/resolver",
            headers=headers,
            params={"action_id": action_id},
        )
        assert repeated_resolution.status_code == 409

        with SessionLocal() as db:
            persisted_action = db.query(AcademicCoordinationAction).filter_by(
                id=action_id
            ).one()
            assert persisted_action.status == "concluída"
            assert persisted_action.resolved_by == user_id
            events = db.query(models.AuditEvent).filter_by(
                entity="academic_coordination_action",
                entity_id=action_id,
            ).all()
            assert {event.action for event in events} == {"created", "resolved"}
            assert len(events) == 2
            assert all(event.user_id == user_id for event in events)
    finally:
        if previous_override:
            app.dependency_overrides[get_current_active_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_active_user, None)


def test_coordinator_approves_only_pending_enrollments_in_scope_and_audits_decision():
    institution_id, user_id, campus_id, _recognition_id, enrollment_id = _create_request_scope()
    coordinator_user = models.User(
        id=user_id,
        username="coordinator-test",
        hashed_password="not-used",
        role="academico",
        institution_id=institution_id,
        campus_id=campus_id,
        is_active=True,
    )
    active_enrollment_id = uuid4().hex
    unlinked_enrollment_id = uuid4().hex
    with SessionLocal() as db:
        pending = db.query(models.Enrollment).filter_by(id=enrollment_id).one()
        db.add(models.Enrollment(
            id=active_enrollment_id,
            institution_id=pending.institution_id,
            student_id=pending.student_id,
            academic_class_id=pending.academic_class_id,
            course_name=pending.course_name,
            class_name=pending.class_name,
            year=pending.year,
            status="active",
            campus_id=pending.campus_id,
        ))
        db.add(models.Enrollment(
            id=unlinked_enrollment_id,
            institution_id=pending.institution_id,
            student_id=pending.student_id,
            course_name=pending.course_name,
            class_name="Sem turma",
            year=pending.year,
            status="pendente",
            campus_id=pending.campus_id,
        ))
        db.commit()

    previous_override = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: coordinator_user
    headers = _headers()
    try:
        pending_items = client.get("/coordenacao/matriculas-pendentes", headers=headers)
        assert pending_items.status_code == 200, pending_items.text
        items = pending_items.json()["items"]
        assert [item["id"] for item in items] == [enrollment_id]
        assert items[0]["student_name"] == "Estudante da solicitação"
        assert items[0]["course_name"] == "Curso para decisão"

        approved = client.post(
            f"/coordenacao/matriculas/{enrollment_id}/aprovar",
            headers=headers,
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["previous_status"] == "pendente"
        assert approved.json()["status"] == "active"

        repeated = client.post(
            f"/coordenacao/matriculas/{enrollment_id}/aprovar",
            headers=headers,
        )
        assert repeated.status_code == 409
        assert client.post(
            f"/coordenacao/matriculas/{active_enrollment_id}/aprovar",
            headers=headers,
        ).status_code == 409
        assert client.post(
            f"/coordenacao/matriculas/{unlinked_enrollment_id}/aprovar",
            headers=headers,
        ).status_code == 404

        with SessionLocal() as db:
            enrollment = db.query(models.Enrollment).filter_by(id=enrollment_id).one()
            audit = db.query(models.AuditEvent).filter_by(
                entity="enrollment",
                entity_id=enrollment_id,
                action="coordinator_approved",
            ).one()
            assert enrollment.status == "active"
            assert audit.user_id == user_id
            assert '"before": "pendente"' in audit.details
            assert '"after": "active"' in audit.details
    finally:
        if previous_override:
            app.dependency_overrides[get_current_active_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_active_user, None)


def test_secretaria_can_link_account_to_coordinator_for_review_access():
    institution_id = "test-institution-id"
    account_id = uuid4().hex
    with SessionLocal() as db:
        db.add(models.User(
            id=account_id,
            username=f"coord-{account_id[:8]}",
            hashed_password="not-used",
            role="academico",
            institution_id=institution_id,
            is_active=True,
        ))
        db.commit()
    secretary = models.User(
        id="test-admin-id",
        username="admin_test",
        hashed_password="not-used",
        role="admin_global",
        institution_id=institution_id,
        is_active=True,
    )
    previous_override = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: secretary
    token = create_access_token({
        "sub": "coordinator-secretary-test",
        "role": "admin_global",
        "module": "secretaria",
    })
    try:
        created = client.post(
            "/secretaria/academico/profissionais",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "staff_code": "COORD-LINK",
                "full_name": "Coordenador vinculado",
                "email": f"coord-{account_id}@example.test",
                "staff_type": "coordenador",
                "user_id": account_id,
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["staff"]["user_id"] == account_id
    finally:
        if previous_override:
            app.dependency_overrides[get_current_active_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_active_user, None)
