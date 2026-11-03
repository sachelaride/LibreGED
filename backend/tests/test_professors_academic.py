from datetime import date
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
    AcademicStaff,
    AcademicTerm,
)


client = TestClient(app)


def _headers(role: str = "academico", module: str = "professores") -> dict[str, str]:
    token = create_access_token({
        "sub": "professor-test",
        "role": role,
        "module": module,
    })
    return {"Authorization": f"Bearer {token}"}


def _create_teacher_class() -> tuple[str, str, str, str, str, str]:
    with SessionLocal() as db:
        institution = db.query(models.Institution).first()
        campus_id = uuid4().hex
        teacher_user_id = uuid4().hex
        staff_id = uuid4().hex
        course_id = uuid4().hex
        discipline_id = uuid4().hex
        term_id = uuid4().hex
        offering_id = uuid4().hex
        class_id = uuid4().hex
        unassigned_class_id = uuid4().hex
        student_id = uuid4().hex
        enrollment_id = uuid4().hex
        db.add(models.Campus(
            id=campus_id,
            institution_id=institution.id,
            name="Campus docente",
        ))
        db.add(models.User(
            id=teacher_user_id,
            username="professor-test",
            hashed_password="not-used",
            role="academico",
            institution_id=institution.id,
            campus_id=campus_id,
        ))
        db.add(AcademicStaff(
            id=staff_id,
            institution_id=institution.id,
            campus_id=campus_id,
            user_id=teacher_user_id,
            staff_code="DOC-TEST",
            full_name="Docente de teste",
            email="docente-test@example.test",
            staff_type="professor",
            status="ativo",
        ))
        db.add(AcademicCourse(
            id=course_id,
            institution_id=institution.id,
            campus_id=campus_id,
            code="CUR-TEST",
            name="Curso de teste",
            degree="Bacharelado",
            modality="presencial",
            duration_periods=8,
            status="ativo",
        ))
        db.add(AcademicDiscipline(
            id=discipline_id,
            institution_id=institution.id,
            code="DISC-TEST",
            name="Disciplina de teste",
            workload_hours=60,
            credits=4,
            status="ativo",
        ))
        db.add(AcademicTerm(
            id=term_id,
            institution_id=institution.id,
            code="2026-1",
            name="2026.1",
            starts_on=date(2026, 2, 1),
            ends_on=date(2026, 6, 30),
            status="ativo",
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
            code="TUR-TEST",
            teacher_id=staff_id,
            capacity=30,
            status="ativa",
        ))
        db.add(AcademicClass(
            id=unassigned_class_id,
            institution_id=institution.id,
            offering_id=offering_id,
            code="TUR-SEM-DOCENTE",
            teacher_id=None,
            capacity=30,
            status="ativa",
        ))
        db.add(models.Student(
            id=student_id,
            institution_id=institution.id,
            campus_id=campus_id,
            full_name="Estudante de teste",
            birth_date="2005-01-01",
            cpf=f"8{uuid4().int % 10**10:010d}",
            email=f"aluno-{student_id}@example.test",
        ))
        db.flush()
        db.add(models.Enrollment(
            id=enrollment_id,
            institution_id=institution.id,
            student_id=student_id,
            academic_class_id=class_id,
            course_name="Curso de teste",
            class_name="TUR-TEST",
            year=2026,
            status="active",
        ))
        db.commit()
        return institution.id, teacher_user_id, campus_id, class_id, unassigned_class_id, enrollment_id


def test_teacher_can_manage_assessments_grades_and_attendance_only_for_assigned_class():
    institution_id, teacher_user_id, campus_id, class_id, unassigned_class_id, enrollment_id = _create_teacher_class()
    teacher = models.User(
        id=teacher_user_id,
        username="professor-test",
        hashed_password="not-used",
        role="academico",
        institution_id=institution_id,
        campus_id=campus_id,
        is_active=True,
    )
    previous_override = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: teacher
    headers = _headers()
    try:
        classes = client.get("/professores/turmas", headers=headers)
        assert classes.status_code == 200, classes.text
        assert [item["id"] for item in classes.json()["items"]] == [class_id]

        roster = client.get(f"/professores/turmas/{class_id}/alunos", headers=headers)
        assert roster.status_code == 200, roster.text
        assert roster.json()["items"][0]["enrollment_id"] == enrollment_id

        assessment_response = client.post(
            f"/professores/turmas/{class_id}/avaliacoes",
            headers=headers,
            json={
                "name": "Prova 1",
                "description": "Avaliação inicial",
                "max_score": 10,
                "due_date": "2026-04-15",
            },
        )
        assert assessment_response.status_code == 201, assessment_response.text
        assessment_id = assessment_response.json()["item"]["id"]

        listed_assessments = client.get(
            f"/professores/avaliacoes?class_id={class_id}",
            headers=headers,
        )
        assert [item["id"] for item in listed_assessments.json()["items"]] == [assessment_id]

        invalid_grade = client.put(
            f"/professores/avaliacoes/{assessment_id}/notas/{enrollment_id}",
            headers=headers,
            json={"score": 11},
        )
        assert invalid_grade.status_code == 422

        grade_response = client.put(
            f"/professores/avaliacoes/{assessment_id}/notas/{enrollment_id}",
            headers=headers,
            json={"score": 8.5, "comment": "Bom desempenho"},
        )
        assert grade_response.status_code == 200, grade_response.text
        grade_id = grade_response.json()["grade"]["id"]
        updated_grade = client.put(
            f"/professores/avaliacoes/{assessment_id}/notas/{enrollment_id}",
            headers=headers,
            json={"score": 9, "comment": None},
        )
        assert updated_grade.json()["grade"]["id"] == grade_id

        grades = client.get(f"/professores/avaliacoes/{assessment_id}/notas", headers=headers)
        assert grades.status_code == 200, grades.text
        assert grades.json()["items"][0]["score"] == 9
        dashboard = client.get("/professores/dashboard", headers=headers)
        assert dashboard.status_code == 200, dashboard.text
        assert dashboard.json()["stats"]["media_geral"] == 9

        unrelated_enrollment_grade = client.put(
            f"/professores/avaliacoes/{assessment_id}/notas/{uuid4().hex}",
            headers=headers,
            json={"score": 5},
        )
        assert unrelated_enrollment_grade.status_code == 404

        too_low_max_score = client.patch(
            f"/professores/avaliacoes/{assessment_id}",
            headers=headers,
            json={"max_score": 8},
        )
        assert too_low_max_score.status_code == 409
        updated_assessment = client.patch(
            f"/professores/avaliacoes/{assessment_id}",
            headers=headers,
            json={"name": "Prova 1 revisada"},
        )
        assert updated_assessment.status_code == 200
        assert updated_assessment.json()["item"]["name"] == "Prova 1 revisada"

        attendance_date = "2026-04-10"
        attendance_response = client.put(
            f"/professores/turmas/{class_id}/frequencia/{enrollment_id}?attendance_date={attendance_date}",
            headers=headers,
            json={"status": "present"},
        )
        assert attendance_response.status_code == 200, attendance_response.text
        attendance_id = attendance_response.json()["attendance"]["id"]
        attendance_items = client.get(
            f"/professores/turmas/{class_id}/frequencia?attendance_date={attendance_date}",
            headers=headers,
        )
        assert attendance_items.json()["items"][0]["status"] == "present"
        assert attendance_items.json()["items"][0]["attendance_id"] == attendance_id

        unauthorized_class = client.get(
            f"/professores/turmas/{unassigned_class_id}",
            headers=headers,
        )
        assert unauthorized_class.status_code == 404

        cannot_delete_assessment_with_grades = client.delete(
            f"/professores/avaliacoes/{assessment_id}",
            headers=headers,
        )
        assert cannot_delete_assessment_with_grades.status_code == 409

        deleted_grade = client.delete(
            f"/professores/avaliacoes/{assessment_id}/notas/{enrollment_id}",
            headers=headers,
        )
        assert deleted_grade.status_code == 204
        deleted_attendance = client.delete(
            f"/professores/turmas/{class_id}/frequencia/{enrollment_id}?attendance_date={attendance_date}",
            headers=headers,
        )
        assert deleted_attendance.status_code == 204
        deleted_assessment = client.delete(f"/professores/avaliacoes/{assessment_id}", headers=headers)
        assert deleted_assessment.status_code == 204
    finally:
        if previous_override:
            app.dependency_overrides[get_current_active_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_active_user, None)


def test_secretaria_can_link_and_unlink_a_teacher_login():
    institution_id = "test-institution-id"
    account_id = uuid4().hex
    with SessionLocal() as db:
        institution = db.get(models.Institution, institution_id)
        db.add(models.User(
            id=account_id,
            username=f"teacher-{account_id[:8]}",
            hashed_password="not-used",
            role="academico",
            institution_id=institution.id,
            is_active=True,
        ))
        db.commit()

    admin = models.User(
        id="test-admin-id",
        username="admin_test",
        hashed_password="not-used",
        role="admin_global",
        institution_id=institution_id,
        is_active=True,
    )
    previous_override = app.dependency_overrides.get(get_current_active_user)
    app.dependency_overrides[get_current_active_user] = lambda: admin
    headers = _headers(role="admin_global", module="secretaria")
    try:
        created = client.post(
            "/secretaria/academico/profissionais",
            headers=headers,
            json={
                "staff_code": "DOC-LINK",
                "full_name": "Docente vinculado",
                "email": f"doc-{account_id}@example.test",
                "staff_type": "professor",
                "user_id": account_id,
            },
        )
        assert created.status_code == 201, created.text
        staff_id = created.json()["staff"]["id"]
        assert created.json()["staff"]["user_id"] == account_id

        accounts = client.get(
            f"/secretaria/academico/usuarios-vinculaveis?staff_id={staff_id}",
            headers=headers,
        )
        assert accounts.status_code == 200, accounts.text
        assert [item["id"] for item in accounts.json()["items"]] == [account_id]

        unlinked = client.patch(
            f"/secretaria/academico/profissionais/{staff_id}",
            headers=headers,
            json={"user_id": None},
        )
        assert unlinked.status_code == 200, unlinked.text
        assert unlinked.json()["staff"]["user_id"] is None
    finally:
        if previous_override:
            app.dependency_overrides[get_current_active_user] = previous_override
        else:
            app.dependency_overrides.pop(get_current_active_user, None)
