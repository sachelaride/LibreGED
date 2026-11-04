from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import models
from app.auth import create_access_token, get_current_active_user
from app.database import SessionLocal
from app.main import app


client = TestClient(app)


def _student_and_account(institution_id: str, *, link: bool = True):
    student_id = uuid4().hex
    user_id = uuid4().hex
    with SessionLocal() as db:
        user = models.User(
            id=user_id,
            username=f"student-{user_id}",
            hashed_password="unused",
            role="aluno",
            institution_id=institution_id,
        )
        student = models.Student(
            id=student_id,
            institution_id=institution_id,
            full_name="Estudante do Portal",
            birth_date="2005-04-03",
            cpf=f"7{uuid4().int % 10**10:010d}",
            email=f"{student_id}@example.test",
            user_id=user_id if link else None,
        )
        db.add_all([user, student])
        db.commit()
    return student_id, user_id


def _headers(user: models.User, module: str = "aluno") -> dict[str, str]:
    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "module": module,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student_user(monkeypatch):
    with SessionLocal() as db:
        institution_id = db.query(models.Institution.id).first()[0]
    student_id, user_id = _student_and_account(institution_id)
    user = models.User(
        id=user_id,
        username=f"student-{user_id}",
        hashed_password="unused",
        role="aluno",
        institution_id=institution_id,
    )
    monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: user)
    return student_id, user, institution_id


@pytest.mark.parametrize(
    "path",
    [
        "/aluno/dashboard",
        "/aluno/boletim",
        "/aluno/documentos",
        "/aluno/historico",
        "/aluno/dossie",
    ],
)
def test_student_portal_get_routes_only_show_linked_student(
    path, student_user
):
    student_id, user, _ = student_user

    own_response = client.get(path, headers=_headers(user))
    assert own_response.status_code == 200, own_response.text
    assert own_response.json()["student_id"] == student_id

    other_response = client.get(
        path,
        params={"student_id": "ALU-1002"},
        headers=_headers(user),
    )
    assert other_response.status_code == 403


def test_student_portal_rejects_unlinked_student_account(monkeypatch):
    with SessionLocal() as db:
        institution_id = db.query(models.Institution.id).first()[0]
    _, user_id = _student_and_account(institution_id, link=False)
    user = models.User(
        id=user_id,
        username=f"student-{user_id}",
        hashed_password="unused",
        role="aluno",
        institution_id=institution_id,
    )
    monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: user)

    response = client.get("/aluno/dashboard", headers=_headers(user))

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Conta de aluno ainda não vinculada ao cadastro acadêmico"
    )


def test_student_cannot_request_enrollment_for_another_student(student_user):
    _, user, _ = student_user

    response = client.post(
        "/aluno/matricula",
        headers=_headers(user),
        json={
            "student_id": "ALU-1002",
            "course": "Curso",
            "semester": "2026/2",
        },
    )

    assert response.status_code == 403
    dossier_response = client.post(
        "/aluno/dossie",
        headers=_headers(user),
        json={"student_id": "ALU-1002"},
    )
    assert dossier_response.status_code == 403


def test_institutional_portal_access_remains_scoped_to_institution(monkeypatch):
    with SessionLocal() as db:
        institution_id = db.query(models.Institution.id).first()[0]
        foreign_institution = models.Institution(
            id=uuid4().hex,
            name="Outra instituição",
            cnpj=f"6{uuid4().int % 10**13:013d}",
            legal_name="Outra instituição",
        )
        db.add(foreign_institution)
        db.flush()
        foreign_student = models.Student(
            id=uuid4().hex,
            institution_id=foreign_institution.id,
            full_name="Estudante de outra instituição",
            birth_date="2004-01-01",
            cpf=f"5{uuid4().int % 10**10:010d}",
            email=f"{uuid4().hex}@example.test",
        )
        db.add(foreign_student)
        foreign_student_id = foreign_student.id
        db.commit()

    user = models.User(
        id=uuid4().hex,
        username="institutional-student-support",
        hashed_password="unused",
        role="admin_instituicao",
        institution_id=institution_id,
    )
    monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: user)
    own_student_id, _ = _student_and_account(institution_id)

    own_response = client.get(
        "/aluno/dashboard",
        params={"student_id": own_student_id},
        headers=_headers(user),
    )
    foreign_response = client.get(
        "/aluno/dashboard",
        params={"student_id": foreign_student_id},
        headers=_headers(user),
    )
    legacy_demo_response = client.get(
        "/aluno/dashboard",
        headers=_headers(user),
    )

    assert own_response.status_code == 200, own_response.text
    assert foreign_response.status_code == 404
    assert legacy_demo_response.status_code == 404


def test_secretaria_can_link_an_account_and_the_student_can_access_the_portal(
    monkeypatch,
):
    with SessionLocal() as db:
        institution_id = db.query(models.Institution.id).first()[0]
        student_id = uuid4().hex
        user_id = uuid4().hex
        db.add_all([
            models.Student(
                id=student_id,
                institution_id=institution_id,
                full_name="Estudante para vínculo",
                birth_date="2005-04-03",
                cpf=f"4{uuid4().int % 10**10:010d}",
                email=f"{student_id}@example.test",
            ),
            models.User(
                id=user_id,
                username=f"student-link-{user_id}",
                hashed_password="unused",
                role="aluno",
                institution_id=institution_id,
            ),
        ])
        db.commit()

    secretary = models.User(
        id="test-admin-id",
        username="secretaria-test",
        hashed_password="unused",
        role="admin_global",
        institution_id=institution_id,
    )
    monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: secretary)
    response = client.put(
        f"/secretaria/academico/alunos/{student_id}/conta",
        headers=_headers(secretary, "secretaria"),
        json={"user_id": user_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == user_id
    with SessionLocal() as db:
        audit_event = db.query(models.AuditEvent).filter_by(
            entity="student_account_link",
            entity_id=student_id,
            action="student_account_link_updated",
        ).first()
        assert audit_event is not None

    student_user = models.User(
        id=user_id,
        username=f"student-link-{user_id}",
        hashed_password="unused",
        role="aluno",
        institution_id=institution_id,
    )
    monkeypatch.setitem(
        app.dependency_overrides,
        get_current_active_user,
        lambda: student_user,
    )
    portal_response = client.get("/aluno/dashboard", headers=_headers(student_user))

    assert portal_response.status_code == 200, portal_response.text
    assert portal_response.json()["student_id"] == student_id
    assert portal_response.json()["student_name"] == "Estudante para vínculo"


def test_secretaria_cannot_link_user_from_another_institution(monkeypatch):
    with SessionLocal() as db:
        institution_id = db.query(models.Institution.id).first()[0]
        foreign_institution = models.Institution(
            id=uuid4().hex,
            name="Instituição externa",
            cnpj=f"3{uuid4().int % 10**13:013d}",
            legal_name="Instituição externa",
        )
        db.add(foreign_institution)
        db.flush()
        student = models.Student(
            id=uuid4().hex,
            institution_id=institution_id,
            full_name="Estudante protegido",
            birth_date="2005-04-03",
            cpf=f"2{uuid4().int % 10**10:010d}",
            email="student-protected@example.test",
        )
        account = models.User(
            id=uuid4().hex,
            username=f"foreign-student-{uuid4().hex}",
            hashed_password="unused",
            role="aluno",
            institution_id=foreign_institution.id,
        )
        db.add_all([student, account])
        db.commit()
        student_id = student.id
        account_id = account.id

    secretary = models.User(
        id="test-admin-id",
        username="secretaria-test",
        hashed_password="unused",
        role="admin_global",
        institution_id=institution_id,
    )
    monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: secretary)

    response = client.put(
        f"/secretaria/academico/alunos/{student_id}/conta",
        headers=_headers(secretary, "secretaria"),
        json={"user_id": account_id},
    )

    assert response.status_code == 422


def test_student_account_cannot_be_linked_to_two_academic_records(monkeypatch):
    with SessionLocal() as db:
        institution_id = db.query(models.Institution.id).first()[0]
        account = models.User(
            id=uuid4().hex,
            username=f"unique-student-{uuid4().hex}",
            hashed_password="unused",
            role="aluno",
            institution_id=institution_id,
        )
        students_to_link = [
            models.Student(
                id=uuid4().hex,
                institution_id=institution_id,
                full_name=f"Estudante {index}",
                birth_date="2005-04-03",
                cpf=f"1{uuid4().int % 10**10:010d}",
                email=f"{uuid4().hex}@example.test",
            )
            for index in range(2)
        ]
        db.add_all([account, *students_to_link])
        db.commit()
        account_id = account.id
        first_student_id, second_student_id = [student.id for student in students_to_link]

    secretary = models.User(
        id="test-admin-id",
        username="secretaria-test",
        hashed_password="unused",
        role="admin_global",
        institution_id=institution_id,
    )
    monkeypatch.setitem(app.dependency_overrides, get_current_active_user, lambda: secretary)
    headers = _headers(secretary, "secretaria")
    first_link = client.put(
        f"/secretaria/academico/alunos/{first_student_id}/conta",
        headers=headers,
        json={"user_id": account_id},
    )
    second_link = client.put(
        f"/secretaria/academico/alunos/{second_student_id}/conta",
        headers=headers,
        json={"user_id": account_id},
    )
    available_accounts = client.get(
        f"/secretaria/academico/alunos/{second_student_id}/usuarios-vinculaveis",
        headers=headers,
    )

    assert first_link.status_code == 200, first_link.text
    assert second_link.status_code == 409
    assert account_id not in {item["id"] for item in available_accounts.json()["items"]}
