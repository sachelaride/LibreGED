from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import app
from app import models, storage
from app.database import SessionLocal


client = TestClient(app)


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
    invalid_document = client.post(
        "/api/documents",
        json={
            "institution_id": institution_b["id"],
            "student_id": student_a["id"],
            "enrollment_id": enrollment_a["id"],
            "document_type": "historico",
            "title": "Documento Invalido",
            "status": "pending",
        },
    )
    assert invalid_document.status_code == 409


def test_document_audit_references_the_document():
    institution = create_institution("IES Documento", "54.000.000/0001-00")
    student = create_student(institution["id"], "60270280292")
    enrollment = create_enrollment(institution["id"], student["id"])
    document_response = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "enrollment_id": enrollment["id"],
            "document_type": "historico",
            "title": "Historico Teste",
            "status": "pending",
        },
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
    student = create_student(institution["id"], "60370380393")
    enrollment = create_enrollment(institution["id"], student["id"])
    document_response = client.post(
        "/api/documents",
        json={
            "institution_id": institution["id"],
            "student_id": student["id"],
            "enrollment_id": enrollment["id"],
            "document_type": "historico",
            "title": "Historico Atomico",
            "status": "pending",
        },
    )
    document = document_response.json()

    db = SessionLocal()
    try:
        db.add(
            models.DocumentVersion(
                id=str(uuid4()),
                document_id=document["id"],
                version_number=2,
                file_name="reservada.txt",
                stored_path=str(storage.STORAGE_ROOT / "reservada.txt"),
                checksum="0" * 64,
            )
        )
        db.commit()
    finally:
        db.close()

    files_before = set(storage.STORAGE_ROOT.iterdir())
    conflict_response = client.post(
        f"/api/documents/{document['id']}/upload",
        files={"file": ("historico.txt", b"nao deve persistir", "text/plain")},
    )

    assert conflict_response.status_code == 409
    assert conflict_response.json() == {"detail": "document version already exists"}
    assert set(storage.STORAGE_ROOT.iterdir()) == files_before

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
