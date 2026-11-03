from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import models
from app.auth import create_access_token, get_current_active_user
from app.database import SessionLocal
from app.main import app
from app.models_academic_catalog import (
    AcademicClass,
    AcademicCourse,
    AcademicCurriculum,
    AcademicCurriculumDiscipline,
    AcademicCurriculumPrerequisite,
    AcademicDiscipline,
    AcademicOffering,
    AcademicTerm,
)


client = TestClient(app)


@pytest.fixture
def catalog_scope():
    original_override = app.dependency_overrides.get(get_current_active_user)

    def bind_institution(institution_id):
        app.dependency_overrides[get_current_active_user] = lambda: models.User(
            id="test-admin-id",
            username="catalog-test-admin",
            hashed_password="...",
            role="admin_global",
            institution_id=institution_id,
        )

    yield bind_institution
    if original_override:
        app.dependency_overrides[get_current_active_user] = original_override
    else:
        app.dependency_overrides.pop(get_current_active_user, None)


def test_staff_changes_are_audited_without_personal_values(catalog_scope):
    institution_id = "test-institution-id"
    catalog_scope(institution_id)
    headers = {
        "Authorization": f"Bearer {create_access_token({'sub': 'test', 'role': 'admin_global', 'module': 'secretaria'})}"
    }

    created = client.post(
        "/secretaria/academico/profissionais",
        headers=headers,
        json={
            "staff_code": "PROF-HISTORY",
            "full_name": "Profissional de histórico",
            "email": "profissional-history@example.test",
            "staff_type": "professor",
        },
    )
    assert created.status_code == 201, created.text
    staff_id = created.json()["staff"]["id"]

    updated = client.patch(
        f"/secretaria/academico/profissionais/{staff_id}",
        headers=headers,
        json={"status": "inativo"},
    )
    assert updated.status_code == 200, updated.text

    history = client.get(
        f"/secretaria/academico/historico-alteracoes/profissional/{staff_id}",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    events = history.json()["items"]
    assert {event["action"] for event in events} == {
        "academic_staff_created",
        "academic_staff_updated",
    }
    assert "PROF-HISTORY" not in str(events)
    assert "profissional-history@example.test" not in str(events)


def test_coordinator_responsibilities_are_scoped_by_course_campus_and_dates(catalog_scope):
    institution_id = "test-institution-id"
    catalog_scope(institution_id)
    headers = {
        "Authorization": f"Bearer {create_access_token({'sub': 'test', 'role': 'admin_global', 'module': 'secretaria'})}"
    }

    campus_response = client.post(
        "/secretaria/academico/campi",
        headers=headers,
        json={"name": "Campus coordenação"},
    )
    assert campus_response.status_code == 201, campus_response.text
    campus_id = campus_response.json()["campus"]["id"]
    course_response = client.post(
        "/secretaria/academico/cursos",
        headers=headers,
        json={
            "campus_id": campus_id,
            "code": f"COORD-{uuid4().hex[:8]}",
            "name": "Curso com coordenação",
            "degree": "Bacharelado",
            "modality": "presencial",
            "duration_periods": 8,
        },
    )
    assert course_response.status_code == 201, course_response.text
    course_id = course_response.json()["course"]["id"]

    coordinator_response = client.post(
        "/secretaria/academico/profissionais",
        headers=headers,
        json={
            "campus_id": campus_id,
            "staff_code": f"COORD-{uuid4().hex[:8]}",
            "full_name": "Coordenadora responsável",
            "email": f"coord-{uuid4().hex}@example.test",
            "staff_type": "coordenador",
        },
    )
    assert coordinator_response.status_code == 201, coordinator_response.text
    coordinator_id = coordinator_response.json()["staff"]["id"]

    assignment_response = client.post(
        "/secretaria/academico/responsabilidades-coordenacao",
        headers=headers,
        json={
            "coordinator_id": coordinator_id,
            "course_id": course_id,
            "campus_id": campus_id,
            "starts_on": "2027-01-01",
            "ends_on": "2027-12-31",
        },
    )
    assert assignment_response.status_code == 201, assignment_response.text
    assignment_id = assignment_response.json()["assignment"]["id"]
    assignment_list = client.get(
        "/secretaria/academico/responsabilidades-coordenacao",
        headers=headers,
    )
    assert assignment_list.status_code == 200
    assert assignment_list.json()["items"][0]["coordinator_name"] == "Coordenadora responsável"
    assert assignment_list.json()["items"][0]["course_name"] == "Curso com coordenação"

    overlap = client.post(
        "/secretaria/academico/responsabilidades-coordenacao",
        headers=headers,
        json={
            "coordinator_id": coordinator_id,
            "course_id": course_id,
            "campus_id": campus_id,
            "starts_on": "2027-06-01",
            "ends_on": "2028-05-31",
        },
    )
    assert overlap.status_code == 409
    invalid_period = client.patch(
        f"/secretaria/academico/responsabilidades-coordenacao/{assignment_id}",
        headers=headers,
        json={"starts_on": "2028-01-01"},
    )
    assert invalid_period.status_code == 422

    updated = client.patch(
        f"/secretaria/academico/responsabilidades-coordenacao/{assignment_id}",
        headers=headers,
        json={"ends_on": "2028-01-31"},
    )
    assert updated.status_code == 200, updated.text
    history = client.get(
        f"/secretaria/academico/historico-alteracoes/responsabilidade-coordenacao/{assignment_id}",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    assert {item["action"] for item in history.json()["items"]} == {
        "academic_coordinator_assignment_created",
        "academic_coordinator_assignment_updated",
    }


def test_secretaria_can_build_academic_catalog_and_reject_schedule_conflicts(catalog_scope):
    db = SessionLocal()
    institution_id = uuid4().hex
    campus_id = uuid4().hex
    db.add(models.Institution(
        id=institution_id,
        name="Instituição de teste",
        cnpj=f"test-{institution_id[:12]}",
        legal_name="Instituição de teste LTDA",
    ))
    db.flush()
    db.add(models.Campus(id=campus_id, institution_id=institution_id, name="Campus teste"))
    db.commit()
    db.close()
    catalog_scope(institution_id)

    token = create_access_token({"sub": "test", "role": "admin_global", "module": "secretaria"})
    headers = {"Authorization": f"Bearer {token}"}

    campus_response = client.post(
        "/secretaria/academico/campi",
        headers=headers,
        json={"name": "Campus satélite"},
    )
    assert campus_response.status_code == 201, campus_response.text

    course_response = client.post("/secretaria/academico/cursos", headers=headers, json={
        "campus_id": campus_id,
        "code": "ADS-TEST",
        "name": "Tecnologia em Sistemas",
        "degree": "tecnólogo",
        "modality": "presencial",
        "duration_periods": 5,
    })
    assert course_response.status_code == 201, course_response.text
    course_id = course_response.json()["course"]["id"]

    def publication(prefix):
        return {
            "tipo": f"Portaria {prefix}",
            "numero": f"{prefix}-123",
            "data": "2020-01-15",
            "veiculo_publicacao": "Diário Oficial",
            "data_publicacao": "2020-01-20",
            "secao_publicacao": "1",
            "pagina_publicacao": "10",
        }

    address = {
        "logradouro": "Rua da Instituição",
        "numero": "100",
        "bairro": "Centro",
        "codigo_municipio": "2611606",
        "nome_municipio": "Recife",
        "uf": "PE",
        "cep": "50000000",
    }
    institution_profile_payload = {
        "codigo_mec": "12345",
        "endereco": address,
        "credenciamento": publication("Credenciamento"),
        "recredenciamento": publication("Recredenciamento"),
        "renovacao_de_recredenciamento": publication("Renovação"),
        "mantenedora_razao_social": "Mantenedora de Teste LTDA",
        "mantenedora_cnpj": "12.345.678/0001-90",
        "mantenedora_endereco": address,
    }
    empty_institution_profile = client.get(
        "/secretaria/academico/historico/perfil-institucional",
        headers=headers,
    )
    assert empty_institution_profile.status_code == 200
    assert empty_institution_profile.json()["configured"] is False
    assert client.put(
        "/secretaria/academico/historico/perfil-institucional",
        headers=headers,
        json={},
    ).status_code == 422
    institution_profile = client.put(
        "/secretaria/academico/historico/perfil-institucional",
        headers=headers,
        json=institution_profile_payload,
    )
    assert institution_profile.status_code == 200, institution_profile.text
    assert institution_profile.json()["configured"] is True
    assert institution_profile.json()["profile"]["codigo_mec"] == "12345"

    course_profile_payload = {
        "codigo_curso_emec": "67890",
        "autorizacao": {
            "tipo": "Portaria",
            "numero": "AUT-123",
            "data": "2020-01-15",
            "veiculo_publicacao": "Diário Oficial",
            "data_publicacao": "2020-01-20",
        },
        "reconhecimento": publication("Reconhecimento"),
        "renovacao_reconhecimento": publication("Renovação Reconhecimento"),
        "habilitacao": [{
            "nome_habilitacao": "Sistemas de Informação",
            "data_habilitacao": "2021-03-10",
        }],
    }
    catalog_scope(uuid4().hex)
    assert client.get(
        f"/secretaria/academico/cursos/{course_id}/perfil-historico",
        headers=headers,
    ).status_code == 404
    catalog_scope(institution_id)
    empty_course_profile = client.get(
        f"/secretaria/academico/cursos/{course_id}/perfil-historico",
        headers=headers,
    )
    assert empty_course_profile.status_code == 200
    assert empty_course_profile.json()["configured"] is False
    course_profile = client.put(
        f"/secretaria/academico/cursos/{course_id}/perfil-historico",
        headers=headers,
        json=course_profile_payload,
    )
    assert course_profile.status_code == 200, course_profile.text
    assert course_profile.json()["configured"] is True
    assert course_profile.json()["profile"]["habilitacao"][0]["nome_habilitacao"] == "Sistemas de Informação"
    assert client.get(
        f"/secretaria/academico/cursos/{course_id}/perfil-historico",
        headers=headers,
    ).json()["profile"]["codigo_curso_emec"] == "67890"

    discipline_response = client.post("/secretaria/academico/disciplinas", headers=headers, json={
        "code": "ALG-TEST",
        "name": "Algoritmos",
        "workload_hours": 80,
        "credits": 4,
        "syllabus": "Lógica e algoritmos",
    })
    assert discipline_response.status_code == 201, discipline_response.text
    discipline_id = discipline_response.json()["discipline"]["id"]

    term_response = client.post("/secretaria/academico/periodos", headers=headers, json={
        "code": "2027-1",
        "name": "2027.1",
        "starts_on": "2027-02-01",
        "ends_on": "2027-06-30",
    })
    assert term_response.status_code == 201, term_response.text
    term_id = term_response.json()["term"]["id"]
    assert term_response.json()["term"]["starts_on"] == date(2027, 2, 1).isoformat()

    curriculum_response = client.post("/secretaria/academico/matrizes", headers=headers, json={
        "course_id": course_id,
        "version": "2027",
        "effective_from": "2027-02-01",
        "disciplines": [{"discipline_id": discipline_id, "term_number": 1, "is_required": True}],
    })
    assert curriculum_response.status_code == 201, curriculum_response.text
    curriculum_id = curriculum_response.json()["curriculum"]["id"]
    curriculum = client.get("/secretaria/academico/matrizes", headers=headers)
    assert curriculum.status_code == 200
    assert curriculum.json()["items"][0]["disciplines"][0]["discipline_id"] == discipline_id

    staff_response = client.post("/secretaria/academico/profissionais", headers=headers, json={
        "campus_id": campus_id,
        "staff_code": "PROF-TEST",
        "full_name": "Professora de teste",
        "email": f"prof-{institution_id}@example.test",
        "staff_type": "professor",
    })
    assert staff_response.status_code == 201, staff_response.text
    teacher_id = staff_response.json()["staff"]["id"]
    replacement_teacher_response = client.post(
        "/secretaria/academico/profissionais",
        headers=headers,
        json={
            "campus_id": campus_id,
            "staff_code": "PROF-REPLACEMENT",
            "full_name": "Professor substituto de teste",
            "email": f"prof-substitute-{institution_id}@example.test",
            "staff_type": "professor",
        },
    )
    assert replacement_teacher_response.status_code == 201, replacement_teacher_response.text
    replacement_teacher_id = replacement_teacher_response.json()["staff"]["id"]
    teacher_profile_url = f"/secretaria/academico/profissionais/{teacher_id}/dados-historico"
    empty_teacher_profile = client.get(teacher_profile_url, headers=headers)
    assert empty_teacher_profile.status_code == 200, empty_teacher_profile.text
    assert empty_teacher_profile.json()["configured"] is False
    invalid_teacher_profile = client.put(
        teacher_profile_url,
        headers=headers,
        json={
            "titulacao": "Doutorado",
            "cpf": "123.456.789-01",
            "lattes": "http://lattes.cnpq.br/1234567890123456",
        },
    )
    assert invalid_teacher_profile.status_code == 422
    saved_teacher_profile = client.put(
        teacher_profile_url,
        headers=headers,
        json={
            "titulacao": "Mestrado",
            "cpf": "12345678901",
            "lattes": "https://lattes.cnpq.br/1234567890123456",
        },
    )
    assert saved_teacher_profile.status_code == 200, saved_teacher_profile.text
    assert saved_teacher_profile.json()["configured"] is True
    assert saved_teacher_profile.json()["cpf_configured"] is True
    assert "cpf" not in saved_teacher_profile.json()
    reloaded_teacher_profile = client.get(teacher_profile_url, headers=headers)
    assert reloaded_teacher_profile.json()["cpf_configured"] is True
    assert "cpf" not in reloaded_teacher_profile.json()
    staff_list = client.get("/secretaria/academico/profissionais", headers=headers)
    assert staff_list.status_code == 200
    assert "transcript_cpf" not in staff_list.json()["items"][0]
    update_staff = client.patch(
        f"/secretaria/academico/profissionais/{teacher_id}",
        headers=headers,
        json={"status": "inativo"},
    )
    assert update_staff.status_code == 200, update_staff.text
    staff_history = client.get(
        f"/secretaria/academico/historico-alteracoes/profissional/{teacher_id}",
        headers=headers,
    )
    assert staff_history.status_code == 200, staff_history.text
    staff_events = staff_history.json()["items"]
    assert {
        "academic_staff_created",
        "academic_staff_updated",
    } <= {event["action"] for event in staff_events}
    assert "PROF-TEST" not in str(staff_events)
    assert f"prof-{institution_id}@example.test" not in str(staff_events)
    coordinator_response = client.post("/secretaria/academico/profissionais", headers=headers, json={
        "campus_id": campus_id,
        "staff_code": "COORD-TEST",
        "full_name": "Coordenador de teste",
        "email": f"coord-{institution_id}@example.test",
        "staff_type": "coordenador",
    })
    assert coordinator_response.status_code == 201, coordinator_response.text
    coordinator_id = coordinator_response.json()["staff"]["id"]

    room_one_response = client.post("/secretaria/academico/salas", headers=headers, json={
        "campus_id": campus_id,
        "code": "SALA-1",
        "name": "Sala 1",
        "capacity": 40,
    })
    assert room_one_response.status_code == 201, room_one_response.text
    room_one_id = room_one_response.json()["room"]["id"]

    room_two_response = client.post("/secretaria/academico/salas", headers=headers, json={
        "campus_id": campus_id,
        "code": "SALA-2",
        "name": "Sala 2",
        "capacity": 40,
    })
    assert room_two_response.status_code == 201, room_two_response.text
    room_two_id = room_two_response.json()["room"]["id"]

    offering_response = client.post("/secretaria/academico/ofertas", headers=headers, json={
        "course_id": course_id,
        "discipline_id": discipline_id,
        "term_id": term_id,
        "campus_id": campus_id,
        "capacity": 35,
    })
    assert offering_response.status_code == 201, offering_response.text
    offering_id = offering_response.json()["offering"]["id"]
    rejected_inactive_teacher = client.post(
        "/secretaria/academico/turmas",
        headers=headers,
        json={
            "offering_id": offering_id,
            "code": "ADS-2027-1-INACTIVE",
            "teacher_id": teacher_id,
            "capacity": 1,
        },
    )
    assert rejected_inactive_teacher.status_code == 422
    reactivate_teacher = client.patch(
        f"/secretaria/academico/profissionais/{teacher_id}",
        headers=headers,
        json={"status": "ativo"},
    )
    assert reactivate_teacher.status_code == 200, reactivate_teacher.text
    update_offering_response = client.patch(
        f"/secretaria/academico/ofertas/{offering_id}",
        headers=headers,
        json={"capacity": 36},
    )
    assert update_offering_response.status_code == 200, update_offering_response.text
    offering_history = client.get(
        f"/secretaria/academico/historico-alteracoes/oferta/{offering_id}",
        headers=headers,
    )
    assert offering_history.status_code == 200, offering_history.text
    assert {
        event["action"] for event in offering_history.json()["items"]
    } == {"academic_offering_created", "academic_offering_updated"}

    class_response = client.post("/secretaria/academico/turmas", headers=headers, json={
        "offering_id": offering_id,
        "code": "ADS-2027-1-A",
        "teacher_id": teacher_id,
        "coordinator_id": coordinator_id,
        "capacity": 1,
        "status": "ativa",
    })
    assert class_response.status_code == 201, class_response.text
    class_id = class_response.json()["class"]["id"]
    update_class_response = client.patch(
        f"/secretaria/academico/turmas/{class_id}",
        headers=headers,
        json={"teacher_id": replacement_teacher_id},
    )
    assert update_class_response.status_code == 200, update_class_response.text
    class_history = client.get(
        f"/secretaria/academico/historico-alteracoes/turma/{class_id}",
        headers=headers,
    )
    assert class_history.status_code == 200, class_history.text
    class_history_items = class_history.json()["items"]
    assert "academic_class_created" in {event["action"] for event in class_history_items}
    allocation_event = next(
        event for event in class_history_items
        if event["action"] == "faculty_allocation_updated"
    )
    assert replacement_teacher_id in allocation_event["details"]

    unplanned_discipline_response = client.post(
        "/secretaria/academico/disciplinas",
        headers=headers,
        json={
            "code": "EST-TEST",
            "name": "Estatística não prevista na matriz",
            "workload_hours": 60,
            "credits": 3,
        },
    )
    assert unplanned_discipline_response.status_code == 201, unplanned_discipline_response.text
    unplanned_offering_response = client.post(
        "/secretaria/academico/ofertas",
        headers=headers,
        json={
            "course_id": course_id,
            "discipline_id": unplanned_discipline_response.json()["discipline"]["id"],
            "term_id": term_id,
            "campus_id": campus_id,
            "capacity": 10,
        },
    )
    assert unplanned_offering_response.status_code == 201, unplanned_offering_response.text
    unplanned_class_response = client.post(
        "/secretaria/academico/turmas",
        headers=headers,
        json={
            "offering_id": unplanned_offering_response.json()["offering"]["id"],
            "code": "ADS-2027-1-EST",
            "capacity": 10,
            "status": "ativa",
        },
    )
    assert unplanned_class_response.status_code == 201, unplanned_class_response.text
    unplanned_class_id = unplanned_class_response.json()["class"]["id"]

    student_id = uuid4().hex
    with SessionLocal() as db:
        db.add(models.Student(
            id=student_id,
            institution_id=institution_id,
            campus_id=campus_id,
            full_name="Aluna para matrícula",
            birth_date="2005-04-15",
            cpf=f"9{uuid4().int % 10**10:010d}",
            email=f"aluna-{student_id}@example.test",
        ))
        db.commit()

    available_classes = client.get(
        "/secretaria/academico/matriculas/turmas-disponiveis",
        headers=headers,
    )
    assert available_classes.status_code == 200, available_classes.text
    assert available_classes.json()["items"] == [{
        "id": class_id,
        "code": "ADS-2027-1-A",
        "campus_id": campus_id,
        "course_name": "Tecnologia em Sistemas",
        "term_name": "2027.1",
        "term_year": 2027,
        "campus_name": "Campus teste",
        "available_seats": 1,
    }]

    invalid_curriculum_enrollment = client.post("/api/enrollments", json={
        "institution_id": institution_id,
        "student_id": student_id,
        "academic_class_id": unplanned_class_id,
        "status": "active",
    })
    assert invalid_curriculum_enrollment.status_code == 409
    assert "curriculum" in invalid_curriculum_enrollment.json()["detail"].lower()

    enrollment_response = client.post("/api/enrollments", json={
        "institution_id": institution_id,
        "student_id": student_id,
        "academic_class_id": class_id,
        "status": "pending",
    })
    assert enrollment_response.status_code == 200, enrollment_response.text
    assert enrollment_response.json()["academic_class_id"] == class_id
    assert enrollment_response.json()["status"] == "pending"
    assert enrollment_response.json()["course_name"] == "Tecnologia em Sistemas"
    assert enrollment_response.json()["class_name"] == "ADS-2027-1-A"
    assert enrollment_response.json()["year"] == 2027
    student_history = client.get(
        f"/api/students/{student_id}/history",
        headers=headers,
    )
    assert student_history.status_code == 200, student_history.text
    enrollment_history = next(
        item for item in student_history.json()["items"]
        if item["entity_type"] == "enrollment"
        and item["action"] == "created"
    )
    assert enrollment_history["snapshot_available"] is True
    assert enrollment_history["snapshot_complete"] is True
    assert enrollment_history["academic_link"] == {
        "course_id": course_id,
        "course_name": "Tecnologia em Sistemas",
        "curriculum_id": curriculum_id,
        "curriculum_version": "2027",
        "discipline_id": discipline_id,
        "discipline_name": "Algoritmos",
        "class_id": class_id,
        "class_code": "ADS-2027-1-A",
        "term_id": term_id,
        "term_code": "2027-1",
        "term_name": "2027.1",
        "term_starts_on": "2027-02-01",
        "term_ends_on": "2027-06-30",
        "campus_id": campus_id,
    }
    unsupported_contract_update = client.post(
        f"/secretaria/matriculas/{enrollment_response.json()['id']}/status",
        headers=headers,
        json={"status": "active", "contract_status": "em_validacao"},
    )
    assert unsupported_contract_update.status_code == 422
    status_update = client.post(
        f"/secretaria/matriculas/{enrollment_response.json()['id']}/status",
        headers=headers,
        json={"status": "active"},
    )
    assert status_update.status_code == 200, status_update.text
    with SessionLocal() as db:
        updated_enrollment = db.get(
            models.Enrollment,
            enrollment_response.json()["id"],
        )
        assert updated_enrollment.class_name == "ADS-2027-1-A"
    status_history = client.get(
        f"/api/students/{student_id}/history",
        headers=headers,
    )
    status_event = next(
        item for item in status_history.json()["items"]
        if item["entity_type"] == "enrollment"
        and item["action"] == "status_updated"
    )
    assert status_event["state_change"] == {
        "before": {"result": "pending", "status": "pending"},
        "after": {"result": "pending", "status": "active"},
    }
    assert status_event["snapshot_available"] is True
    assert status_event["academic_link"]["class_id"] == class_id

    duplicate_enrollment = client.post("/api/enrollments", json={
        "institution_id": institution_id,
        "student_id": student_id,
        "academic_class_id": class_id,
        "status": "pending",
    })
    assert duplicate_enrollment.status_code == 409
    assert client.get(
        "/secretaria/academico/matriculas/turmas-disponiveis",
        headers=headers,
    ).json()["items"] == []

    schedule_response = client.post(f"/secretaria/academico/turmas/{class_id}/horarios", headers=headers, json={
        "room_id": room_one_id,
        "weekday": 1,
        "starts_at": "08:00:00",
        "ends_at": "10:00:00",
    })
    assert schedule_response.status_code == 201, schedule_response.text
    schedule_id = schedule_response.json()["schedule"]["id"]
    invalid_schedule_update = client.patch(
        f"/secretaria/academico/horarios/{schedule_id}",
        headers=headers,
        json={"ends_at": "07:00:00"},
    )
    assert invalid_schedule_update.status_code == 422
    schedule_update = client.patch(
        f"/secretaria/academico/horarios/{schedule_id}",
        headers=headers,
        json={"ends_at": "10:15:00"},
    )
    assert schedule_update.status_code == 200, schedule_update.text
    schedule_history = client.get(
        f"/secretaria/academico/historico-alteracoes/horario/{schedule_id}",
        headers=headers,
    )
    assert schedule_history.status_code == 200, schedule_history.text
    assert {
        event["action"] for event in schedule_history.json()["items"]
    } == {"academic_schedule_created", "academic_schedule_updated"}

    conflict_class_response = client.post("/secretaria/academico/turmas", headers=headers, json={
        "offering_id": offering_id,
        "code": "ADS-2027-1-B",
        "teacher_id": replacement_teacher_id,
        "capacity": 30,
        "status": "ativa",
    })
    assert conflict_class_response.status_code == 201, conflict_class_response.text
    conflict_class_id = conflict_class_response.json()["class"]["id"]
    conflict_response = client.post(
        f"/secretaria/academico/turmas/{conflict_class_id}/horarios",
        headers=headers,
        json={
            "room_id": room_two_id,
            "weekday": 1,
            "starts_at": "09:00:00",
            "ends_at": "11:00:00",
        },
    )
    assert conflict_response.status_code == 409
    assert "professor" in conflict_response.json()["detail"].lower()

    summary = client.get("/secretaria/academico/resumo", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["summary"]["campi"] == 2
    assert summary.json()["summary"]["cursos"] == 1
    assert summary.json()["summary"]["disciplinas"] == 2
    assert summary.json()["summary"]["periodos"] == 1

    target_class_response = client.post(
        "/secretaria/academico/turmas",
        headers=headers,
        json={
            "offering_id": offering_id,
            "code": "ADS-2027-1-TRANSFER",
            "teacher_id": replacement_teacher_id,
            "capacity": 30,
            "status": "ativa",
        },
    )
    assert target_class_response.status_code == 201, target_class_response.text
    target_class_id = target_class_response.json()["class"]["id"]
    same_class_transfer = client.post(
        f"/secretaria/academico/matriculas/{enrollment_response.json()['id']}/transferir",
        headers=headers,
        json={"target_class_id": class_id},
    )
    assert same_class_transfer.status_code == 409

    transfer_response = client.post(
        f"/secretaria/academico/matriculas/{enrollment_response.json()['id']}/transferir",
        headers=headers,
        json={"target_class_id": target_class_id},
    )
    assert transfer_response.status_code == 200, transfer_response.text
    assert transfer_response.json()["source_enrollment"]["status"] == "transferred"
    assert transfer_response.json()["target_enrollment"]["status"] == "pending"
    assert transfer_response.json()["target_enrollment"]["academic_link"]["class_id"] == target_class_id
    with SessionLocal() as db:
        source_enrollment = db.get(models.Enrollment, enrollment_response.json()["id"])
        target_enrollment = db.get(
            models.Enrollment,
            transfer_response.json()["target_enrollment"]["id"],
        )
        assert source_enrollment.status == "transferred"
        assert target_enrollment.academic_class_id == target_class_id
        assert target_enrollment.student_id == student_id

    transfer_history = client.get(
        f"/api/students/{student_id}/history",
        headers=headers,
    )
    transfer_events = [
        item for item in transfer_history.json()["items"]
        if item["action"] in {"academic_transfer_out", "academic_transfer_in"}
    ]
    assert {item["action"] for item in transfer_events} == {
        "academic_transfer_out",
        "academic_transfer_in",
    }
    assert all(item["snapshot_available"] for item in transfer_events)
    outgoing_event = next(
        item for item in transfer_events
        if item["action"] == "academic_transfer_out"
    )
    assert outgoing_event["state_change"]["before"]["academic_link"]["class_id"] == class_id
    assert outgoing_event["state_change"]["after"]["academic_link"]["class_id"] == target_class_id


def test_secretaria_can_update_academic_catalog_records(catalog_scope):
    db = SessionLocal()
    institution_id = uuid4().hex
    campus_id = uuid4().hex
    db.add(models.Institution(
        id=institution_id,
        name="Instituição atualizável",
        cnpj=f"test-{institution_id[:12]}",
        legal_name="Instituição atualizável LTDA",
    ))
    db.flush()
    db.add(models.Campus(id=campus_id, institution_id=institution_id, name="Campus atualizável"))
    db.commit()
    db.close()
    catalog_scope(institution_id)

    token = create_access_token({"sub": "update-test", "role": "admin_global", "module": "secretaria"})
    headers = {"Authorization": f"Bearer {token}"}

    course = client.post("/secretaria/academico/cursos", headers=headers, json={
        "campus_id": campus_id,
        "code": "ENG-UPDATE",
        "name": "Engenharia",
        "degree": "bacharel",
        "modality": "presencial",
        "duration_periods": 8,
    })
    assert course.status_code == 201, course.text
    course_id = course.json()["course"]["id"]

    discipline = client.post("/secretaria/academico/disciplinas", headers=headers, json={
        "code": "FIS-UPDATE",
        "name": "Física",
        "workload_hours": 80,
        "credits": 4,
        "syllabus": "Mecânica",
    })
    assert discipline.status_code == 201, discipline.text
    discipline_id = discipline.json()["discipline"]["id"]

    term = client.post("/secretaria/academico/periodos", headers=headers, json={
        "code": "2028-1",
        "name": "2028.1",
        "starts_on": "2028-02-01",
        "ends_on": "2028-06-30",
    })
    assert term.status_code == 201, term.text
    term_id = term.json()["term"]["id"]

    professor = client.post("/secretaria/academico/profissionais", headers=headers, json={
        "campus_id": campus_id,
        "staff_code": "PROF-UPDATE",
        "full_name": "Professor atualizável",
        "email": f"prof-up-{uuid4().hex[:8]}@example.test",
        "staff_type": "professor",
    })
    assert professor.status_code == 201, professor.text
    teacher_id = professor.json()["staff"]["id"]

    room = client.post("/secretaria/academico/salas", headers=headers, json={
        "campus_id": campus_id,
        "code": "SALA-UPDATE",
        "name": "Sala atualizável",
        "capacity": 30,
    })
    assert room.status_code == 201, room.text
    room_id = room.json()["room"]["id"]

    offering = client.post("/secretaria/academico/ofertas", headers=headers, json={
        "course_id": course_id,
        "discipline_id": discipline_id,
        "term_id": term_id,
        "campus_id": campus_id,
        "capacity": 25,
    })
    assert offering.status_code == 201, offering.text
    offering_id = offering.json()["offering"]["id"]

    academic_class = client.post("/secretaria/academico/turmas", headers=headers, json={
        "offering_id": offering_id,
        "code": "ENG-2028-1-A",
        "teacher_id": teacher_id,
        "capacity": 25,
        "status": "ativa",
    })
    assert academic_class.status_code == 201, academic_class.text
    class_id = academic_class.json()["class"]["id"]

    updated_course = client.patch(f"/secretaria/academico/cursos/{course_id}", headers=headers, json={
        "name": "Engenharia atualizada",
        "status": "inativo",
    })
    assert updated_course.status_code == 200, updated_course.text
    assert updated_course.json()["course"]["name"] == "Engenharia atualizada"
    assert updated_course.json()["course"]["status"] == "inativo"

    updated_discipline = client.patch(f"/secretaria/academico/disciplinas/{discipline_id}", headers=headers, json={
        "credits": 6,
        "status": "inativo",
    })
    assert updated_discipline.status_code == 200, updated_discipline.text
    assert updated_discipline.json()["discipline"]["credits"] == 6
    assert updated_discipline.json()["discipline"]["status"] == "inativo"

    updated_term = client.patch(f"/secretaria/academico/periodos/{term_id}", headers=headers, json={
        "name": "2028.1 - ajustado",
        "status": "ativo",
    })
    assert updated_term.status_code == 200, updated_term.text
    assert updated_term.json()["term"]["name"] == "2028.1 - ajustado"

    updated_room = client.patch(f"/secretaria/academico/salas/{room_id}", headers=headers, json={
        "capacity": 40,
        "is_active": False,
    })
    assert updated_room.status_code == 200, updated_room.text
    assert updated_room.json()["room"]["capacity"] == 40
    assert updated_room.json()["room"]["is_active"] is False

    updated_offering = client.patch(f"/secretaria/academico/ofertas/{offering_id}", headers=headers, json={
        "capacity": 30,
        "status": "fechada",
    })
    assert updated_offering.status_code == 200, updated_offering.text
    assert updated_offering.json()["offering"]["capacity"] == 30
    assert updated_offering.json()["offering"]["status"] == "fechada"

    updated_class = client.patch(f"/secretaria/academico/turmas/{class_id}", headers=headers, json={
        "capacity": 30,
        "status": "encerrada",
    })
    assert updated_class.status_code == 200, updated_class.text
    assert updated_class.json()["class"]["capacity"] == 30
    assert updated_class.json()["class"]["status"] == "encerrada"


def test_campus_scoped_secretaria_cannot_access_other_campus_catalog():
    db = SessionLocal()
    institution_id = uuid4().hex
    own_campus_id = uuid4().hex
    other_campus_id = uuid4().hex
    username = f"campus-{uuid4().hex}"
    db.add(models.Institution(
        id=institution_id,
        name="Instituição com escopo de campus",
        cnpj=f"test-{institution_id[:12]}",
        legal_name="Instituição com escopo de campus LTDA",
    ))
    db.flush()
    db.add_all([
        models.Campus(id=own_campus_id, institution_id=institution_id, name="Campus autorizado"),
        models.Campus(id=other_campus_id, institution_id=institution_id, name="Campus restrito"),
    ])
    db.commit()
    db.close()

    token = create_access_token({"sub": username, "role": "admin_instituicao", "module": "secretaria"})
    headers = {"Authorization": f"Bearer {token}"}
    previous_override = app.dependency_overrides[get_current_active_user]
    app.dependency_overrides[get_current_active_user] = lambda: models.User(
        id=uuid4().hex,
        username=username,
        hashed_password="not-used",
        role="admin_instituicao",
        institution_id=institution_id,
        campus_id=own_campus_id,
        is_active=True,
    )
    try:
        visible_campuses = client.get("/secretaria/academico/campi", headers=headers)
        assert visible_campuses.status_code == 200
        assert [campus["id"] for campus in visible_campuses.json()["items"]] == [own_campus_id]

        own_course = client.post("/secretaria/academico/cursos", headers=headers, json={
            "code": "OWN",
            "name": "Curso do campus autorizado",
            "degree": "Bacharelado",
            "modality": "presencial",
            "duration_periods": 8,
        })
        assert own_course.status_code == 201, own_course.text
        assert own_course.json()["course"]["campus_id"] == own_campus_id

        forbidden_course = client.post("/secretaria/academico/cursos", headers=headers, json={
            "campus_id": other_campus_id,
            "code": "OTHER",
            "name": "Curso de outro campus",
            "degree": "Bacharelado",
            "modality": "presencial",
            "duration_periods": 8,
        })
        assert forbidden_course.status_code == 403

        visible_courses = client.get("/secretaria/academico/cursos", headers=headers)
        assert visible_courses.status_code == 200
        assert all(course["campus_id"] in (None, own_campus_id) for course in visible_courses.json()["items"])
    finally:
        app.dependency_overrides[get_current_active_user] = previous_override


def test_curriculum_prerequisites_block_enrollment_until_prior_result_is_passed(catalog_scope):
    institution_id = "test-institution-id"
    campus_id = uuid4().hex
    course_id = uuid4().hex
    equivalent_course_id = uuid4().hex
    prerequisite_id = uuid4().hex
    target_discipline_id = uuid4().hex
    later_discipline_id = uuid4().hex
    equivalent_discipline_id = uuid4().hex
    previous_term_id = uuid4().hex
    current_term_id = uuid4().hex
    previous_offering_id = uuid4().hex
    equivalent_offering_id = uuid4().hex
    elective_offering_id = uuid4().hex
    target_offering_id = uuid4().hex
    previous_class_id = uuid4().hex
    equivalent_class_id = uuid4().hex
    elective_class_id = uuid4().hex
    target_class_id = uuid4().hex
    student_id = uuid4().hex
    open_enrollment_student_id = uuid4().hex
    failed_student_id = uuid4().hex
    previous_enrollment_id = uuid4().hex
    equivalent_enrollment_id = uuid4().hex
    elective_enrollment_id = uuid4().hex
    open_enrollment_id = uuid4().hex
    failed_enrollment_id = uuid4().hex
    today = date.today()

    with SessionLocal() as db:
        db.add(models.Campus(
            id=campus_id,
            institution_id=institution_id,
            name=f"Campus pré-requisitos {campus_id[:8]}",
        ))
        db.add(AcademicCourse(
            id=course_id,
            institution_id=institution_id,
            campus_id=campus_id,
            code=f"CUR-{course_id[:8]}",
            name="Curso com pré-requisitos",
            degree="bacharelado",
            modality="presencial",
            duration_periods=4,
            status="ativo",
        ))
        db.add(AcademicCourse(
            id=equivalent_course_id,
            institution_id=institution_id,
            campus_id=campus_id,
            code=f"EQUIV-{equivalent_course_id[:8]}",
            name="Curso da disciplina equivalente",
            degree="bacharelado",
            modality="presencial",
            duration_periods=4,
            status="ativo",
        ))
        db.add_all([
            AcademicDiscipline(
                id=prerequisite_id,
                institution_id=institution_id,
                code=f"PRE-{prerequisite_id[:8]}",
                name="Fundamentos",
                workload_hours=60,
                credits=4,
                status="ativo",
            ),
            AcademicDiscipline(
                id=target_discipline_id,
                institution_id=institution_id,
                code=f"AVC-{target_discipline_id[:8]}",
                name="Avançada",
                workload_hours=60,
                credits=4,
                status="ativo",
            ),
            AcademicDiscipline(
                id=later_discipline_id,
                institution_id=institution_id,
                code=f"POS-{later_discipline_id[:8]}",
                name="Especializada",
                workload_hours=60,
                credits=4,
                status="ativo",
            ),
            AcademicDiscipline(
                id=equivalent_discipline_id,
                institution_id=institution_id,
                code=f"EQUIV-{equivalent_discipline_id[:8]}",
                name="Fundamentos equivalentes",
                workload_hours=60,
                credits=4,
                status="ativo",
            ),
            AcademicTerm(
                id=previous_term_id,
                institution_id=institution_id,
                code=f"ANT-{previous_term_id[:8]}",
                name="Período anterior",
                starts_on=today - timedelta(days=365),
                ends_on=today - timedelta(days=1),
                status="encerrado",
            ),
            AcademicTerm(
                id=current_term_id,
                institution_id=institution_id,
                code=f"ATU-{current_term_id[:8]}",
                name="Período atual",
                starts_on=today,
                ends_on=today + timedelta(days=365),
                status="ativo",
            ),
            models.Student(
                id=student_id,
                institution_id=institution_id,
                campus_id=campus_id,
                full_name="Estudante com pré-requisito",
                birth_date=date(2000, 1, 1),
                cpf=f"8{uuid4().int % 10**10:010d}",
                email=f"{student_id}@example.test",
            ),
            models.Student(
                id=open_enrollment_student_id,
                institution_id=institution_id,
                campus_id=campus_id,
                full_name="Estudante de período aberto",
                birth_date=date(2000, 1, 1),
                cpf=f"7{uuid4().int % 10**10:010d}",
                email=f"{open_enrollment_student_id}@example.test",
            ),
            models.Student(
                id=failed_student_id,
                institution_id=institution_id,
                campus_id=campus_id,
                full_name="Estudante reprovado",
                birth_date=date(2000, 1, 1),
                cpf=f"6{uuid4().int % 10**10:010d}",
                email=f"{failed_student_id}@example.test",
            ),
        ])
        db.flush()
        db.add_all([
            AcademicOffering(
                id=previous_offering_id,
                institution_id=institution_id,
                course_id=course_id,
                discipline_id=prerequisite_id,
                term_id=previous_term_id,
                campus_id=campus_id,
                capacity=20,
                status="fechada",
            ),
            AcademicOffering(
                id=equivalent_offering_id,
                institution_id=institution_id,
                course_id=equivalent_course_id,
                discipline_id=equivalent_discipline_id,
                term_id=previous_term_id,
                campus_id=campus_id,
                capacity=20,
                status="fechada",
            ),
            AcademicOffering(
                id=elective_offering_id,
                institution_id=institution_id,
                course_id=course_id,
                discipline_id=later_discipline_id,
                term_id=previous_term_id,
                campus_id=campus_id,
                capacity=20,
                status="fechada",
            ),
            AcademicOffering(
                id=target_offering_id,
                institution_id=institution_id,
                course_id=course_id,
                discipline_id=target_discipline_id,
                term_id=current_term_id,
                campus_id=campus_id,
                capacity=20,
                status="aberta",
            ),
        ])
        db.flush()
        db.add_all([
            AcademicClass(
                id=previous_class_id,
                institution_id=institution_id,
                offering_id=previous_offering_id,
                code=f"PRE-{previous_class_id[:8]}",
                capacity=20,
                status="encerrada",
            ),
            AcademicClass(
                id=equivalent_class_id,
                institution_id=institution_id,
                offering_id=equivalent_offering_id,
                code=f"EQUIV-{equivalent_class_id[:8]}",
                capacity=20,
                status="encerrada",
            ),
            AcademicClass(
                id=elective_class_id,
                institution_id=institution_id,
                offering_id=elective_offering_id,
                code=f"OPT-{elective_class_id[:8]}",
                capacity=20,
                status="encerrada",
            ),
            AcademicClass(
                id=target_class_id,
                institution_id=institution_id,
                offering_id=target_offering_id,
                code=f"AVC-{target_class_id[:8]}",
                capacity=20,
                status="ativa",
            ),
            models.Enrollment(
                id=previous_enrollment_id,
                institution_id=institution_id,
                student_id=student_id,
                academic_class_id=previous_class_id,
                course_name="Curso com pré-requisitos",
                class_name=f"PRE-{previous_class_id[:8]}",
                year=today.year - 1,
                status="active",
                campus_id=campus_id,
            ),
            models.Enrollment(
                id=open_enrollment_id,
                institution_id=institution_id,
                student_id=open_enrollment_student_id,
                academic_class_id=target_class_id,
                course_name="Curso com pré-requisitos",
                class_name=f"AVC-{target_class_id[:8]}",
                year=today.year,
                status="active",
                campus_id=campus_id,
            ),
            models.Enrollment(
                id=equivalent_enrollment_id,
                institution_id=institution_id,
                student_id=student_id,
                academic_class_id=equivalent_class_id,
                course_name="Curso com pré-requisitos",
                class_name=f"EQUIV-{equivalent_class_id[:8]}",
                year=today.year - 1,
                status="active",
                campus_id=campus_id,
            ),
            models.Enrollment(
                id=elective_enrollment_id,
                institution_id=institution_id,
                student_id=student_id,
                academic_class_id=elective_class_id,
                course_name="Curso com pré-requisitos",
                class_name=f"OPT-{target_class_id[:8]}",
                year=today.year,
                status="active",
                campus_id=campus_id,
            ),
            models.Enrollment(
                id=failed_enrollment_id,
                institution_id=institution_id,
                student_id=failed_student_id,
                academic_class_id=previous_class_id,
                course_name="Curso com pré-requisitos",
                class_name=f"PRE-{previous_class_id[:8]}",
                year=today.year - 1,
                status="active",
                campus_id=campus_id,
            ),
        ])
        db.commit()

    catalog_scope(institution_id)
    token = create_access_token({
        "sub": "test",
        "role": "admin_global",
        "module": "secretaria",
    })
    headers = {"Authorization": f"Bearer {token}"}

    invalid_curriculum = client.post(
        "/secretaria/academico/matrizes",
        headers=headers,
        json={
            "course_id": course_id,
            "version": "2026-invalid",
            "effective_from": (today - timedelta(days=365)).isoformat(),
            "disciplines": [
                {"discipline_id": prerequisite_id, "term_number": 2},
                {
                    "discipline_id": target_discipline_id,
                    "term_number": 2,
                    "prerequisite_discipline_ids": [prerequisite_id],
                },
            ],
        },
    )
    assert invalid_curriculum.status_code == 422

    curriculum = client.post(
        "/secretaria/academico/matrizes",
        headers=headers,
        json={
            "course_id": course_id,
            "version": "2026",
            "effective_from": (today - timedelta(days=365)).isoformat(),
            "disciplines": [
                {"discipline_id": prerequisite_id, "term_number": 1},
                {
                    "discipline_id": target_discipline_id,
                    "term_number": 2,
                    "prerequisite_discipline_ids": [prerequisite_id],
                },
                {"discipline_id": later_discipline_id, "term_number": 3, "is_required": False},
            ],
        },
    )
    assert curriculum.status_code == 201, curriculum.text
    curriculum_id = curriculum.json()["curriculum"]["id"]
    elective_group = client.post(
        f"/secretaria/academico/matrizes/{curriculum_id}/optativas",
        headers=headers,
        json={
            "code": "OPT-TEC",
            "name": "Optativas de tecnologia",
            "minimum_credits": 4,
            "discipline_ids": [later_discipline_id],
        },
    )
    assert elective_group.status_code == 201, elective_group.text
    invalid_elective_group = client.post(
        f"/secretaria/academico/matrizes/{curriculum_id}/optativas",
        headers=headers,
        json={
            "code": "OPT-OBR",
            "name": "Grupo inválido",
            "minimum_credits": 4,
            "discipline_ids": [target_discipline_id],
        },
    )
    assert invalid_elective_group.status_code == 422
    equivalence = client.post(
        f"/secretaria/academico/matrizes/{curriculum_id}/disciplinas/{prerequisite_id}/equivalencias",
        headers=headers,
        json={"equivalent_discipline_id": equivalent_discipline_id},
    )
    assert equivalence.status_code == 201, equivalence.text
    self_equivalence = client.post(
        f"/secretaria/academico/matrizes/{curriculum_id}/disciplinas/{prerequisite_id}/equivalencias",
        headers=headers,
        json={"equivalent_discipline_id": prerequisite_id},
    )
    assert self_equivalence.status_code == 422

    matrix_response = client.get("/secretaria/academico/matrizes", headers=headers)
    assert matrix_response.status_code == 200
    target_matrix_discipline = next(
        item
        for item in matrix_response.json()["items"][0]["disciplines"]
        if item["discipline_id"] == target_discipline_id
    )
    assert target_matrix_discipline["prerequisites"] == [{
        "discipline_id": prerequisite_id,
        "discipline_name": "Fundamentos",
    }]
    prerequisite_matrix_discipline = next(
        item
        for item in matrix_response.json()["items"][0]["disciplines"]
        if item["discipline_id"] == prerequisite_id
    )
    assert prerequisite_matrix_discipline["equivalences"] == [{
        "discipline_id": equivalent_discipline_id,
        "discipline_name": "Fundamentos equivalentes",
    }]
    elective_matrix_group = matrix_response.json()["items"][0]["elective_groups"][0]
    assert elective_matrix_group["minimum_credits"] == 4
    assert elective_matrix_group["discipline_ids"] == [later_discipline_id]

    open_term_result = client.patch(
        f"/api/enrollments/{open_enrollment_id}/result",
        json={"result": "passed"},
    )
    assert open_term_result.status_code == 409
    assert "after the term has ended" in open_term_result.json()["detail"]

    failed_result = client.patch(
        f"/api/enrollments/{failed_enrollment_id}/result",
        json={"result": "failed"},
    )
    assert failed_result.status_code == 200, failed_result.text
    assert failed_result.json()["result"] == "failed"
    failed_student_enrollment = client.post("/api/enrollments", json={
        "institution_id": institution_id,
        "student_id": failed_student_id,
        "academic_class_id": target_class_id,
    })
    assert failed_student_enrollment.status_code == 409

    blocked_enrollment = client.post("/api/enrollments", json={
        "institution_id": institution_id,
        "student_id": student_id,
        "academic_class_id": target_class_id,
    })
    assert blocked_enrollment.status_code == 409
    assert "Fundamentos" in blocked_enrollment.json()["detail"]

    failed_student_recognition = client.post(
        f"/secretaria/academico/alunos/{failed_student_id}/aproveitamentos",
        headers=headers,
        json={
            "course_id": course_id,
            "curriculum_id": curriculum_id,
            "discipline_id": prerequisite_id,
            "source_institution": "Instituição de origem",
            "source_course": "Curso anterior",
            "source_discipline": "Fundamentos cursados",
            "workload_hours": 60,
            "credits": 4,
        },
    )
    assert failed_student_recognition.status_code == 201, failed_student_recognition.text
    failed_student_recognition_id = failed_student_recognition.json()["recognition"]["id"]
    approved_credit = client.patch(
        f"/secretaria/academico/aproveitamentos/{failed_student_recognition_id}/decisao",
        headers=headers,
        json={"status": "approved", "decision_note": "Documentação conferida"},
    )
    assert approved_credit.status_code == 200, approved_credit.text
    credit_unblocked_enrollment = client.post("/api/enrollments", json={
        "institution_id": institution_id,
        "student_id": failed_student_id,
        "academic_class_id": target_class_id,
    })
    assert credit_unblocked_enrollment.status_code == 200, credit_unblocked_enrollment.text

    passed_result = client.patch(
        f"/api/enrollments/{equivalent_enrollment_id}/result",
        json={"result": "passed"},
    )
    assert passed_result.status_code == 200, passed_result.text
    assert passed_result.json()["result"] == "passed"
    initial_progress = client.get(
        f"/secretaria/academico/alunos/{student_id}/progresso",
        headers=headers,
        params={"course_id": course_id},
    )
    assert initial_progress.status_code == 200, initial_progress.text
    initial_progress_data = initial_progress.json()
    completed_equivalent_requirement = next(
        item
        for item in initial_progress_data["required_disciplines"]
        if item["discipline_id"] == prerequisite_id
    )
    assert completed_equivalent_requirement["status"] == "completed"
    assert initial_progress_data["elective_groups"][0]["earned_credits"] == 0
    assert initial_progress_data["eligible_to_complete"] is False

    elective_result = client.patch(
        f"/api/enrollments/{elective_enrollment_id}/result",
        json={"result": "passed"},
    )
    assert elective_result.status_code == 200, elective_result.text
    updated_progress = client.get(
        f"/secretaria/academico/alunos/{student_id}/progresso",
        headers=headers,
        params={"course_id": course_id},
    )
    assert updated_progress.status_code == 200, updated_progress.text
    updated_progress_data = updated_progress.json()
    assert updated_progress_data["elective_groups"][0]["earned_credits"] == 4
    assert updated_progress_data["elective_groups"][0]["status"] == "completed"
    assert updated_progress_data["credits"]["completed_elective"] == 4
    assert passed_result.json()["status"] == "completed"

    target_credit_request = client.post(
        f"/secretaria/academico/alunos/{student_id}/aproveitamentos",
        headers=headers,
        json={
            "course_id": course_id,
            "curriculum_id": curriculum_id,
            "discipline_id": target_discipline_id,
            "source_institution": "Instituição de origem",
            "source_course": "Curso anterior",
            "source_discipline": "Disciplina avançada cursada",
            "workload_hours": 60,
            "credits": 4,
            "request_note": "Solicitação para análise",
        },
    )
    assert target_credit_request.status_code == 201, target_credit_request.text
    target_credit_request_id = target_credit_request.json()["recognition"]["id"]
    pending_credit_progress = client.get(
        f"/secretaria/academico/alunos/{student_id}/progresso",
        headers=headers,
        params={"course_id": course_id},
    )
    assert pending_credit_progress.status_code == 200, pending_credit_progress.text
    pending_target = next(
        item
        for item in pending_credit_progress.json()["required_disciplines"]
        if item["discipline_id"] == target_discipline_id
    )
    assert pending_target["status"] == "pending"
    duplicate_credit_request = client.post(
        f"/secretaria/academico/alunos/{student_id}/aproveitamentos",
        headers=headers,
        json={
            "course_id": course_id,
            "curriculum_id": curriculum_id,
            "discipline_id": target_discipline_id,
            "source_institution": "Instituição de origem",
            "source_course": "Curso anterior",
            "source_discipline": "Disciplina avançada cursada",
            "workload_hours": 60,
            "credits": 4,
        },
    )
    assert duplicate_credit_request.status_code == 409
    rejected_without_reason = client.patch(
        f"/secretaria/academico/aproveitamentos/{target_credit_request_id}/decisao",
        headers=headers,
        json={"status": "rejected"},
    )
    assert rejected_without_reason.status_code == 422
    rejected_credit = client.patch(
        f"/secretaria/academico/aproveitamentos/{target_credit_request_id}/decisao",
        headers=headers,
        json={"status": "rejected", "decision_note": "Ementa insuficiente"},
    )
    assert rejected_credit.status_code == 200, rejected_credit.text
    assert rejected_credit.json()["recognition"]["status"] == "rejected"

    resubmitted_credit = client.post(
        f"/secretaria/academico/alunos/{student_id}/aproveitamentos",
        headers=headers,
        json={
            "course_id": course_id,
            "curriculum_id": curriculum_id,
            "discipline_id": target_discipline_id,
            "source_institution": "Instituição de origem",
            "source_course": "Curso anterior",
            "source_discipline": "Disciplina avançada cursada",
            "workload_hours": 60,
            "credits": 4,
        },
    )
    assert resubmitted_credit.status_code == 201, resubmitted_credit.text
    approved_target_credit = client.patch(
        f"/secretaria/academico/aproveitamentos/{resubmitted_credit.json()['recognition']['id']}/decisao",
        headers=headers,
        json={"status": "approved", "decision_note": "Compatibilidade curricular confirmada"},
    )
    assert approved_target_credit.status_code == 200, approved_target_credit.text
    approved_credit_list = client.get(
        "/secretaria/academico/aproveitamentos",
        headers=headers,
        params={"student_id": student_id, "recognition_status": "approved"},
    )
    assert approved_credit_list.status_code == 200, approved_credit_list.text
    assert len(approved_credit_list.json()["items"]) == 1
    assert approved_credit_list.json()["items"][0]["target_discipline"] == "Avançada"
    recognized_progress = client.get(
        f"/secretaria/academico/alunos/{student_id}/progresso",
        headers=headers,
        params={"course_id": course_id},
    )
    assert recognized_progress.status_code == 200, recognized_progress.text
    recognized_target = next(
        item
        for item in recognized_progress.json()["required_disciplines"]
        if item["discipline_id"] == target_discipline_id
    )
    assert recognized_target["status"] == "completed"
    assert recognized_target["fulfillment"] == "approved_recognition"
    assert recognized_target["recognition"]["source_discipline"] == "Disciplina avançada cursada"
    assert recognized_progress.json()["eligible_to_complete"] is True
    identity_update = client.patch(
        f"/secretaria/academico/alunos/{student_id}/dados-historico",
        headers=headers,
        json={
            "social_name": "Nome social",
            "sex": "F",
            "nationality": "Brasileira",
            "birthplace_municipality_code": "2611606",
            "birthplace_municipality_name": "Recife",
            "birthplace_state": "PE",
            "rg_number": "1234567",
            "rg_issuing_authority": "SDS",
            "rg_state": "PE",
        },
    )
    assert identity_update.status_code == 200, identity_update.text
    assert identity_update.json()["birthplace_municipality_code"] == "2611606"
    assert identity_update.json()["rg_issuing_authority"] == "SDS"
    transcript_entry_url = (
        f"/secretaria/academico/alunos/{student_id}/cursos/{course_id}/dados-ingresso-historico"
    )
    empty_transcript_entry = client.get(transcript_entry_url, headers=headers)
    assert empty_transcript_entry.status_code == 200, empty_transcript_entry.text
    assert empty_transcript_entry.json()["configured"] is False
    invalid_transcript_entry = client.put(
        transcript_entry_url,
        headers=headers,
        json={"entry_date": "2026-02-01", "access_form": "ENEM"},
    )
    assert invalid_transcript_entry.status_code == 422
    saved_transcript_entry = client.put(
        transcript_entry_url,
        headers=headers,
        json={"entry_date": "2026-02-01", "access_form": "Enem"},
    )
    assert saved_transcript_entry.status_code == 200, saved_transcript_entry.text
    assert saved_transcript_entry.json()["entry_date"] == "2026-02-01"
    assert saved_transcript_entry.json()["access_form"] == "Enem"
    academic_history = client.get(
        f"/secretaria/academico/alunos/{student_id}/historico",
        headers=headers,
        params={"course_id": course_id},
    )
    assert academic_history.status_code == 200, academic_history.text
    history_data = academic_history.json()
    recognized_history_item = next(
        item
        for item in history_data["records"]
        if item["type"] == "credit_recognition"
        and item["discipline_id"] == target_discipline_id
    )
    assert recognized_history_item["result"] == "approved"
    assert recognized_history_item["source"].startswith("Disciplina avançada cursada")
    assert recognized_history_item["decision_note"] == "Compatibilidade curricular confirmada"
    assert recognized_history_item["reviewer_id"] == "test-admin-id"
    assert history_data["pending_recognitions"] == []
    assert history_data["official_document_issued"] is False
    assert any("Perfil regulatório da IES" in item for item in history_data["official_history_blockers"])
    assert any("Perfil regulatório do curso" in item for item in history_data["official_history_blockers"])
    assert history_data["official_history_profiles"] == {
        "institution_configured": False,
        "course_configured": False,
        "student_entry_configured": True,
        "teachers_linked": 0,
        "teachers_without_title": 0,
        "disciplines_without_teacher": 2,
    }
    assert not any("Forma de acesso e data de ingresso" in item for item in history_data["official_history_blockers"])
    assert not any("Dados pessoais pendentes" in item for item in history_data["official_history_blockers"])

    eligible_enrollment = client.post("/api/enrollments", json={
        "institution_id": institution_id,
        "student_id": student_id,
        "academic_class_id": target_class_id,
    })
    assert eligible_enrollment.status_code == 200, eligible_enrollment.text


def test_secretaria_can_manage_departments_and_sectors_with_parent_validations(catalog_scope):
    institution_id = uuid4().hex
    campus_id = uuid4().hex
    with SessionLocal() as db:
        db.add(models.Institution(
            id=institution_id,
            name="Instituição de departamentos",
            cnpj=f"test-{institution_id[:12]}",
            legal_name="Instituição de departamentos LTDA",
        ))
        db.flush()
        db.add(models.Campus(
            id=campus_id,
            institution_id=institution_id,
            name="Campus administrativo",
        ))
        db.commit()
    catalog_scope(institution_id)
    token = create_access_token({
        "sub": "departments-test",
        "role": "admin_global",
        "module": "secretaria",
    })
    headers = {"Authorization": f"Bearer {token}"}

    department = client.post(
        "/secretaria/academico/departamentos",
        headers=headers,
        json={
            "campus_id": campus_id,
            "code": "DEP-ADM",
            "name": "Departamento Administrativo",
        },
    )
    assert department.status_code == 201, department.text
    department_id = department.json()["department"]["id"]
    assert client.get(
        "/secretaria/academico/departamentos",
        headers=headers,
    ).json()["items"][0]["id"] == department_id

    duplicate_department = client.post(
        "/secretaria/academico/departamentos",
        headers=headers,
        json={
            "campus_id": campus_id,
            "code": "DEP-ADM",
            "name": "Departamento repetido",
        },
    )
    assert duplicate_department.status_code == 409

    updated_department = client.patch(
        f"/secretaria/academico/departamentos/{department_id}",
        headers=headers,
        json={
            "code": "DEP-ADM-2",
            "name": "Departamento Acadêmico",
            "status": "inativo",
        },
    )
    assert updated_department.status_code == 200, updated_department.text
    assert updated_department.json()["department"]["name"] == "Departamento Acadêmico"

    inactive_parent_sector = client.post(
        "/secretaria/academico/setores",
        headers=headers,
        json={
            "department_id": department_id,
            "code": "SEC-REG",
            "name": "Secretaria de Registro",
        },
    )
    assert inactive_parent_sector.status_code == 409

    client.patch(
        f"/secretaria/academico/departamentos/{department_id}",
        headers=headers,
        json={"status": "ativo"},
    )
    sector = client.post(
        "/secretaria/academico/setores",
        headers=headers,
        json={
            "department_id": department_id,
            "code": "SEC-REG",
            "name": "Secretaria de Registro",
        },
    )
    assert sector.status_code == 201, sector.text
    sector_id = sector.json()["sector"]["id"]
    listed_sector = client.get(
        "/secretaria/academico/setores",
        headers=headers,
    ).json()["items"][0]
    assert listed_sector["department_name"] == "Departamento Acadêmico"
    updated_sector = client.patch(
        f"/secretaria/academico/setores/{sector_id}",
        headers=headers,
        json={"name": "Registro Acadêmico", "status": "inativo"},
    )
    assert updated_sector.status_code == 200, updated_sector.text
    assert updated_sector.json()["sector"]["name"] == "Registro Acadêmico"

    missing_parent = client.post(
        "/secretaria/academico/setores",
        headers=headers,
        json={
            "department_id": uuid4().hex,
            "code": "SEC-X",
            "name": "Setor sem departamento",
        },
    )
    assert missing_parent.status_code == 404


def test_campus_scoped_secretaria_cannot_update_other_campus_sector(catalog_scope):
    institution_id = uuid4().hex
    own_campus_id = uuid4().hex
    other_campus_id = uuid4().hex
    with SessionLocal() as db:
        db.add(models.Institution(
            id=institution_id,
            name="Instituição com setores isolados",
            cnpj=f"test-{institution_id[:12]}",
            legal_name="Instituição com setores isolados LTDA",
        ))
        db.flush()
        db.add_all([
            models.Campus(
                id=own_campus_id,
                institution_id=institution_id,
                name="Campus autorizado",
            ),
            models.Campus(
                id=other_campus_id,
                institution_id=institution_id,
                name="Campus restrito",
            ),
        ])
        db.commit()
    catalog_scope(institution_id)
    token = create_access_token({
        "sub": "campus-sector-test",
        "role": "admin_instituicao",
        "module": "secretaria",
    })
    headers = {"Authorization": f"Bearer {token}"}
    department = client.post(
        "/secretaria/academico/departamentos",
        headers=headers,
        json={
            "campus_id": other_campus_id,
            "code": "DEP-OUTRO",
            "name": "Departamento de outro campus",
        },
    )
    assert department.status_code == 201, department.text
    sector = client.post(
        "/secretaria/academico/setores",
        headers=headers,
        json={
            "department_id": department.json()["department"]["id"],
            "code": "SEC-OUTRO",
            "name": "Setor de outro campus",
        },
    )
    assert sector.status_code == 201, sector.text

    previous_override = app.dependency_overrides[get_current_active_user]
    app.dependency_overrides[get_current_active_user] = lambda: models.User(
        id=uuid4().hex,
        username="campus-sector-user",
        hashed_password="not-used",
        role="admin_instituicao",
        institution_id=institution_id,
        campus_id=own_campus_id,
        is_active=True,
    )
    try:
        visible_departments = client.get(
            "/secretaria/academico/departamentos",
            headers=headers,
        )
        assert visible_departments.status_code == 200
        assert visible_departments.json()["items"] == []

        forbidden_update = client.patch(
            f"/secretaria/academico/setores/{sector.json()['sector']['id']}",
            headers=headers,
            json={"name": "Alteração indevida"},
        )
        assert forbidden_update.status_code == 403
    finally:
        app.dependency_overrides[get_current_active_user] = previous_override
