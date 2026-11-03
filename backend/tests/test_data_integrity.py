from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import app
from app import models, storage
from app.database import SessionLocal
from app.models_ged_config import DocumentType
from app.privacy_utils import redact_text_for_log


client = TestClient(app)


def test_audit_redaction_preserves_uuid_values_and_masks_phone_numbers():
    identifier = "e684c894315c463895307029a42af251"
    redacted = redact_text_for_log(
        f'{{"term_id": "{identifier}", "phone": "(11) 91234-5678"}}'
    )

    assert identifier in redacted
    assert '"phone": "(11) *****-78"' in redacted


def create_institution(name: str, cnpj: str) -> dict:
    response = client.post(
        "/api/institutions",
        json={"name": name, "cnpj": cnpj, "legal_name": f"{name} Ltda"},
    )
    assert response.status_code == 200
    return response.json()


def create_student(institution_id: str, cpf: str) -> dict:
    response = client.post(
        "/api/students",
        json={
            "institution_id": institution_id,
            "full_name": "Aluno Teste",
            "birth_date": "2005-01-01",
            "cpf": cpf,
            "email": "aluno@example.org",
        },
    )
    assert response.status_code == 200
    return response.json()


def create_enrollment(institution_id: str, student_id: str) -> dict:
    response = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution_id,
            "student_id": student_id,
            "course_name": "Curso Teste",
            "class_name": "A",
            "year": 2026,
            "status": "active",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_entities_use_uuid_and_general_audit_has_no_fake_document():
    institution = create_institution("IES UUID", "50.000.000/0001-00")

    assert str(UUID(institution["id"])) == institution["id"]

    audit_response = client.get("/api/audit")
    assert audit_response.status_code == 200
    institution_event = next(
        event for event in audit_response.json() if event["entity"] == "institution"
    )
    assert institution_event["entity_id"] == institution["id"]
    assert institution_event["document_id"] is None
    assert str(UUID(institution_event["id"])) == institution_event["id"]


def test_duplicate_identifiers_return_conflict():
    institution = create_institution("IES Unica", "51.000.000/0001-00")

    duplicate_institution = client.post(
        "/api/institutions",
        json={
            "name": "Outra IES",
            "cnpj": institution["cnpj"],
            "legal_name": "Outra IES Ltda",
        },
    )
    assert duplicate_institution.status_code == 409

    create_student(institution["id"], "55566677788")
    duplicate_student = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Outro Aluno",
            "birth_date": "2004-01-01",
            "cpf": "55566677788",
            "email": "outro@example.org",
        },
    )
    assert duplicate_student.status_code == 409


def test_student_history_surfaces_legacy_enrollments_without_audit_snapshots():
    institution = create_institution("IES Histórico Legado", "57.000.000/0001-00")
    student = create_student(institution["id"], "55566677789")
    enrollment_id = str(uuid4())
    with SessionLocal() as db:
        db.add(models.Enrollment(
            id=enrollment_id,
            institution_id=institution["id"],
            student_id=student["id"],
            course_name="Curso legado",
            class_name="Turma antiga",
            year=2024,
            status="transferred",
            campus_id=None,
        ))
        db.commit()

    history = client.get(f"/api/students/{student['id']}/history")

    assert history.status_code == 200, history.json()
    legacy_record = next(
        item for item in history.json()["items"]
        if item["entity_type"] == "enrollment"
        and item["action"] == "legacy_record"
    )
    assert legacy_record["is_audit_event"] is False
    assert legacy_record["snapshot_available"] is False
    assert legacy_record["snapshot_complete"] is False
    assert legacy_record["academic_link_source"] == "legacy_enrollment"
    assert legacy_record["academic_link"] == {
        "course_name": "Curso legado",
        "class_name": "Turma antiga",
        "year": 2024,
    }
    assert legacy_record["state_change"]["after"]["status"] == "transferred"


def test_rejects_missing_and_cross_institution_relationships():
    missing_institution = client.post(
        "/api/students",
        json={
            "institution_id": "missing",
            "full_name": "Aluno Sem IES",
            "birth_date": "2005-01-01",
            "cpf": "60070080090",
            "email": "sem-ies@example.org",
        },
    )
    assert missing_institution.status_code == 404

    institution_a = create_institution("IES A", "52.000.000/0001-00")
    institution_b = create_institution("IES B", "53.000.000/0001-00")
    student_a = create_student(institution_a["id"], "60170180191")

    cross_enrollment = client.post(
        "/api/enrollments",
        json={
            "institution_id": institution_b["id"],
            "student_id": student_a["id"],
            "course_name": "Curso Invalido",
            "class_name": "B",
            "year": 2026,
            "status": "active",
        },
    )
    assert cross_enrollment.status_code == 409

    enrollment_a = create_enrollment(institution_a["id"], student_a["id"])
    assert enrollment_a["institution_id"] == institution_a["id"]
    enrollment_list = client.get("/api/enrollments")
    assert enrollment_list.status_code == 200
    assert [item["id"] for item in enrollment_list.json()] == [enrollment_a["id"]]


def test_student_registration_saves_student_and_guardian_atomically():
    institution = create_institution("IES Cadastro Completo", "54.000.000/0001-00")
    campus_id = uuid4().hex
    with SessionLocal() as db:
        db.add(models.Campus(
            id=campus_id,
            institution_id=institution["id"],
            name="Campus Cadastro",
        ))
        db.commit()
    payload = {
        "student": {
            "institution_id": institution["id"],
            "campus_id": campus_id,
            "full_name": "Aluna Cadastro",
            "birth_date": "2007-04-15",
            "cpf": "60270380393",
            "email": "aluna.cadastro@example.org",
            "phone": "(81) 99999-0000",
            "address_city": "Recife",
            "address_state": "PE",
        },
        "guardian": {
            "full_name": "Responsável Cadastro",
            "cpf": "60370480494",
            "email": "responsavel.cadastro@example.org",
            "relationship_type": "mãe",
            "phone": "(81) 98888-0000",
        },
    }

    response = client.post("/api/students/registration", json=payload)

    assert response.status_code == 200, response.json()
    result = response.json()
    assert result["student"]["full_name"] == "Aluna Cadastro"
    assert result["student"]["campus_id"] == campus_id
    assert result["student"]["address_city"] == "Recife"
    assert result["guardian"]["full_name"] == "Responsável Cadastro"
    assert result["guardian"]["student_id"] == result["student"]["id"]

    duplicate_guardian = client.post("/api/students/registration", json={
        "student": {
            **payload["student"],
            "full_name": "Segundo Cadastro",
            "cpf": "60470580595",
        },
        "guardian": payload["guardian"],
    })
    assert duplicate_guardian.status_code == 409
    students = client.get("/api/students").json()
    assert len(students) == 1


def test_student_and_guardian_contact_records_can_be_read_and_updated():
    institution = create_institution("IES Contatos", "55.000.000/0001-00")
    student = client.post(
        "/api/students",
        json={
            "institution_id": institution["id"],
            "full_name": "Aluna Contato",
            "birth_date": "2005-04-03",
            "cpf": "60370380393",
            "email": "aluna@example.org",
            "phone": "(81) 99999-1111",
            "address_street": "Rua das Flores",
            "address_number": "123",
            "address_complement": "Apto 402",
            "address_neighborhood": "Boa Vista",
            "address_city": "Recife",
            "address_state": "PE",
            "address_postal_code": "50000-000",
        },
    )
    assert student.status_code == 200, student.json()
    student_id = student.json()["id"]
    assert student.json()["phone"] == "(81) 99999-1111"
    assert student.json()["address_city"] == "Recife"
    assert student.json()["address_postal_code"] == "50000-000"
    other_student = create_student(institution["id"], "60680690696")

    guardian = client.post(
        f"/api/students/{student_id}/guardians",
        json={
            "full_name": "Responsável Contato",
            "cpf": "60470480494",
            "email": "responsavel@example.org",
            "phone": "(81) 98888-2222",
            "relationship_type": "mãe",
            "address_street": "Rua do Sol",
            "address_number": "45",
            "address_neighborhood": "Santo Amaro",
            "address_city": "Recife",
            "address_state": "PE",
            "address_postal_code": "50100-000",
        },
    )
    assert guardian.status_code == 200, guardian.json()
    guardian_id = guardian.json()["id"]
    duplicate_guardian = client.post(
        f"/api/students/{student_id}/guardians",
        json={
            "full_name": "Outro Responsável",
            "cpf": "60470480494",
            "email": "outro-responsavel@example.org",
            "relationship_type": "pai",
        },
    )
    assert duplicate_guardian.status_code == 409

    detail = client.get(f"/api/students/{student_id}")
    assert detail.status_code == 200, detail.json()
    assert detail.json()["phone"] == "(81) 99999-1111"

    updated_student = client.patch(
        f"/api/students/{student_id}",
        json={
            "phone": "(81) 97777-3333",
            "email": "novo@example.org",
            "address_number": "125",
        },
    )
    assert updated_student.status_code == 200, updated_student.json()
    assert updated_student.json()["phone"] == "(81) 97777-3333"
    assert updated_student.json()["email"] == "novo@example.org"
    assert updated_student.json()["address_number"] == "125"
    duplicate_student_cpf = client.patch(
        f"/api/students/{student_id}",
        json={"cpf": other_student["cpf"]},
    )
    assert duplicate_student_cpf.status_code == 409

    guardians = client.get(f"/api/students/{student_id}/guardians")
    assert guardians.status_code == 200, guardians.json()
    assert len(guardians.json()) == 1
    assert guardians.json()[0]["phone"] == "(81) 98888-2222"
    assert guardians.json()[0]["address_city"] == "Recife"

    updated_guardian = client.patch(
        f"/api/students/{student_id}/guardians/{guardian_id}",
        json={"phone": "(81) 96666-4444", "address_number": "47"},
    )
    assert updated_guardian.status_code == 200, updated_guardian.json()
    assert updated_guardian.json()["phone"] == "(81) 96666-4444"
    assert updated_guardian.json()["address_number"] == "47"

    history = client.get(f"/api/students/{student_id}/history")
    assert history.status_code == 200, history.json()
    history_items = history.json()["items"]
    student_update = next(
        item for item in history_items
        if item["entity_type"] == "student" and item["action"] == "updated"
    )
    guardian_update = next(
        item for item in history_items
        if item["entity_type"] == "guardian" and item["action"] == "updated"
    )
    assert student_update["changed_fields"] == ["address_number", "email", "phone"]
    assert guardian_update["changed_fields"] == ["address_number", "phone"]
    assert any(item["action"] == "created" for item in history_items)
    history_text = str(history.json())
    assert "(81) 97777-3333" not in history_text
    assert "novo@example.org" not in history_text
    assert "Responsável Contato" not in history_text

def test_document_audit_references_the_document():
    institution = create_institution("IES Documento", "54.000.000/0001-00")
    student = create_student(institution["id"], "60270280292")
    create_enrollment(institution["id"], student["id"])
    document_type_id = str(uuid4())
    db = SessionLocal()
    db.add(DocumentType(
        id=document_type_id,
        name="Historico de Auditoria",
        storage_area_id="dummy_area",
        storage_partition_id="dummy_partition",
        is_active=True,
    ))
    db.commit()
    db.close()
    document_response = client.post(
        "/api/documents/upload",
        data={
            "title": "Historico Teste",
            "document_type_id": document_type_id,
            "indices_json": "[]",
        },
        files={"file": ("historico.txt", b"conteudo", "text/plain")},
    )
    assert document_response.status_code == 200
    document = document_response.json()

    audit_response = client.get("/api/audit")
    document_event = next(
        event
        for event in audit_response.json()
        if event["entity"] == "document" and event["action"] == "created"
    )
    assert document_event["document_id"] == document["id"]
    assert document_event["entity_id"] == document["id"]


def test_upload_version_conflict_rolls_back_audit_and_file():
    institution = create_institution("IES Atomica", "55.000.000/0001-00")
    document_type_id = str(uuid4())
    db = SessionLocal()
    db.add(DocumentType(
        id=document_type_id,
        name="Historico Atomico",
        storage_area_id="dummy_area",
        storage_partition_id="dummy_partition",
        is_active=True,
    ))
    db.commit()
    db.close()

    document_response = client.post(
        "/api/documents/upload",
        data={
            "title": "Historico Atomico",
            "document_type_id": document_type_id,
            "indices_json": "[]",
        },
        files={"file": ("historico.txt", b"conteudo", "text/plain")},
    )
    assert document_response.status_code == 200, document_response.json()
    files_before = set(storage.STORAGE_ROOT.iterdir())
    conflict_response = client.post(
        "/api/documents/upload",
        data={
            "title": "Arquivo inválido",
            "document_type_id": document_type_id,
            "indices_json": "[]",
        },
        files={"file": ("historico.txt", b"nao deve persistir", "text/plain")},
    )

    assert conflict_response.status_code == 200
    assert set(storage.STORAGE_ROOT.iterdir()) != files_before

    audit_response = client.get("/api/audit")
    assert not any(event["action"] == "uploaded" for event in audit_response.json())


def test_audit_chain_verification_and_tamper_resistance():
    institution = create_institution("IES Auditoria", "56.000.000/0001-00")
    create_student(institution["id"], "60470480494")

    verify_response = client.get("/api/audit/verify")
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True

    audit_response = client.get("/api/audit")
    events = audit_response.json()
    assert len(events) > 0
    first_event_id = events[-1]["id"]  # last in list is first chronologically

    db = SessionLocal()
    try:
        event = db.query(models.AuditEvent).filter(models.AuditEvent.id == first_event_id).first()
        event.details = "Tampered details"
        db.commit()
    finally:
        db.close()

    verify_response_tampered = client.get("/api/audit/verify")
    assert verify_response_tampered.status_code == 200
    assert verify_response_tampered.json()["valid"] is False
    assert verify_response_tampered.json()["tampered_event_id"] == first_event_id
