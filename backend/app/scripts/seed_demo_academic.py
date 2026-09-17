r"""Create/remove a disposable academic GED demonstration dataset.

Run from backend:
    ..\.venv\Scripts\python.exe -m app.scripts.seed_demo_academic
    ..\.venv\Scripts\python.exe -m app.scripts.seed_demo_academic --remove
"""

from __future__ import annotations

import argparse
import json
import shutil
import uuid
from pathlib import Path

from app import auth, models
from app.database import SessionLocal
from app.models_ged import DocumentCategory, GEDAcademicPhase, GEDDocument, GEDDocumentStatus
from app.models_ged_config import (
    DocumentType,
    DocumentTypeIndex,
    DocumentTypeVersion,
    GedIndex,
    UserDocumentType,
)
from app.models_storage import StorageRule
from app.storage import STORAGE_ROOT
from app import models_workflow  # noqa: F401 - registers workflow tables for SQLAlchemy metadata

PREFIX = "DEMO-ACADEMICO"
INSTITUTION_ID = f"{PREFIX.lower()}-instituicao"
CAMPUS_ID = f"{PREFIX.lower()}-campus"
STUDENT_ID = f"{PREFIX.lower()}-aluno"
USER_ID = f"{PREFIX.lower()}-usuario"
USERNAME = "demo.academico"
PASSWORD = "Demo@123456"
COURSE = "Pedagogia"


def uid() -> str:
    return str(uuid.uuid4())


def get_or_create(db, model, identifier: str, **values):
    row = db.get(model, identifier)
    if row is None:
        row = model(id=identifier, **values)
        db.add(row)
        db.flush()
    return row


def seed(db: object) -> None:
    institution = get_or_create(
        db,
        models.Institution,
        INSTITUTION_ID,
        name=f"{PREFIX} Universidade Demonstracao",
        cnpj="00.000.000/DEMO-01",
        legal_name=f"{PREFIX} Universidade Demonstracao Ltda",
    )
    get_or_create(
        db,
        models.InstitutionSettings,
        f"{PREFIX.lower()}-settings",
        institution_id=institution.id,
    )
    campus = get_or_create(
        db,
        models.Campus,
        CAMPUS_ID,
        institution_id=institution.id,
        name=f"{PREFIX} Campus Central",
    )
    user = get_or_create(
        db,
        models.User,
        USER_ID,
        username=USERNAME,
        hashed_password=auth.get_password_hash(PASSWORD),
        role="admin_instituicao",
        institution_id=institution.id,
        campus_id=campus.id,
    )
    student = get_or_create(
        db,
        models.Student,
        STUDENT_ID,
        institution_id=institution.id,
        campus_id=campus.id,
        full_name="Ana Beatriz Demonstracao",
        birth_date="2002-04-15",
        cpf="99999999999",
        email="ana.demo@example.invalid",
    )
    enrollment = db.query(models.Enrollment).filter_by(student_id=student.id, course_name=COURSE).first()
    if enrollment is None:
        db.add(models.Enrollment(
            id=uid(),
            institution_id=institution.id,
            student_id=student.id,
            campus_id=campus.id,
            course_name=COURSE,
            class_name="2024.1",
            year=2024,
            status="active",
        ))

    storage = get_or_create(
        db,
        StorageRule,
        f"{PREFIX.lower()}-storage",
        name=f"{PREFIX} Storage Local",
        storage_type="Local",
        base_path="demo_academico",
        max_files_per_folder=10000,
        max_gb_per_folder=10.0,
        enable_duplication=True,
        secondary_storage_type="Azure",
        secondary_base_path="demo-academico-backup",
        is_active=True,
    )

    index_specs = [
        ("DEMO CPF", "Caractere", "###.###.###-##"),
        ("DEMO Nome do aluno", "Caractere", None),
        ("DEMO RGM", "Caractere", None),
        ("DEMO Curso", "Caractere", None),
        ("DEMO Semestre", "Lista", None),
    ]
    indices = {}
    for name, type_, mask in index_specs:
        index = db.query(GedIndex).filter_by(name=name).first()
        if index is None:
            index = GedIndex(id=uid(), name=name, type=type_, mask=mask, options=[], is_active=True)
            db.add(index)
            db.flush()
        indices[name] = index

    type_specs = [
        ("DEMO Matrícula - 2024.1", "matricula-2024-1", GEDAcademicPhase.MATRICULA, 5),
        ("DEMO Notas - 2024.1", "notas-2024-1", GEDAcademicPhase.CURSO, 5),
        ("DEMO Ficha acadêmica - 2024.1", "ficha-academica-2024-1", GEDAcademicPhase.CURSO, 10),
        ("DEMO Histórico parcial - 2024.1", "historico-2024-1", GEDAcademicPhase.CURSO, 10),
        ("DEMO Notas - 2024.2", "notas-2024-2", GEDAcademicPhase.CURSO, 5),
        ("DEMO Ficha acadêmica - 2024.2", "ficha-academica-2024-2", GEDAcademicPhase.CURSO, 10),
        ("DEMO Histórico final", "historico-final", GEDAcademicPhase.FORMATURA, 20),
        ("DEMO Diploma", "diploma", GEDAcademicPhase.DIPLOMACAO, 50),
    ]
    type_indices = {
        "matricula": ["DEMO CPF", "DEMO Nome do aluno", "DEMO RGM", "DEMO Curso"],
        "notas": ["DEMO CPF", "DEMO RGM", "DEMO Semestre"],
        "ficha": ["DEMO CPF", "DEMO RGM", "DEMO Curso", "DEMO Semestre"],
        "historico": ["DEMO CPF", "DEMO RGM", "DEMO Curso", "DEMO Semestre"],
        "diploma": ["DEMO CPF", "DEMO Nome do aluno", "DEMO RGM", "DEMO Curso"],
    }
    document_types = {}
    for name, partition, phase, retention in type_specs:
        doc_type = db.query(DocumentType).filter_by(name=name).first()
        if doc_type is None:
            doc_type = DocumentType(
                id=uid(), name=name, group_id=f"{PREFIX.lower()}-academico",
                retention_years=retention, legal_hold=False, active_version=1,
                storage_area_id=storage.id, storage_partition_id=partition,
            )
            db.add(doc_type)
            db.flush()
            db.add(DocumentTypeVersion(
                id=uid(), document_type_id=doc_type.id, version=1, status="ACTIVE",
                name=name, group_id=doc_type.group_id, retention_years=retention,
                legal_hold=False, access_policy={}, signature_rule={}, created_by=user.id,
            ))
            key = "matricula" if "Matrícula" in name else "notas" if "Notas" in name else "ficha" if "Ficha" in name else "historico" if "Histórico" in name else "diploma"
            for index_name in type_indices[key]:
                db.add(DocumentTypeIndex(
                    id=uid(), document_type_id=doc_type.id, index_id=indices[index_name].id,
                    is_required=True, is_unique=False,
                ))
        document_types[name] = (doc_type, phase)

    db.flush()
    demo_root = STORAGE_ROOT / "demo_academico"
    docs = [
        ("DEMO Matrícula - 2024.1", "matricula-2024-1", "matricula.txt", "MATRICULA", "2024.1"),
        ("DEMO Notas - 2024.1", "notas-2024-1", "notas-2024-1.txt", "CURSO", "2024.1"),
        ("DEMO Ficha acadêmica - 2024.1", "ficha-academica-2024-1", "ficha-2024-1.txt", "CURSO", "2024.1"),
        ("DEMO Histórico parcial - 2024.1", "historico-2024-1", "historico-2024-1.txt", "CURSO", "2024.1"),
        ("DEMO Notas - 2024.2", "notas-2024-2", "notas-2024-2.txt", "CURSO", "2024.2"),
        ("DEMO Ficha acadêmica - 2024.2", "ficha-academica-2024-2", "ficha-2024-2.txt", "CURSO", "2024.2"),
        ("DEMO Histórico final", "historico-final", "historico-final.txt", "FORMATURA", "2024"),
        ("DEMO Diploma", "diploma", "diploma.txt", "DIPLOMACAO", "2025"),
    ]
    for category_number, (type_name, partition, filename, phase_name, semester) in enumerate(docs, start=1):
        category = db.query(DocumentCategory).filter_by(name=type_name).first()
        if category is None:
            category = DocumentCategory(id=uid(), index_code=f"{PREFIX}-{category_number}", name=type_name)
            db.add(category)
            db.flush()
        path = demo_root / partition / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"{PREFIX}\nAluno: {student.full_name}\nCPF: {student.cpf}\n"
            f"Curso: {COURSE}\nSemestre: {semester}\nTipo: {type_name}\n",
            encoding="utf-8",
        )
        existing = db.query(GEDDocument).filter_by(title=type_name, student_id=student.id).first()
        if existing is None:
            db.add(GEDDocument(
                id=uid(), title=type_name, file_path=str(path.resolve()),
                status=GEDDocumentStatus.VALIDO, academic_phase=GEDAcademicPhase[phase_name],
                extracted_metadata=json.dumps({
                    "demo": True, "cpf": student.cpf, "nome": student.full_name,
                    "rgm": "DEMO-RGM-2024", "curso": COURSE, "semestre": semester,
                }, ensure_ascii=False), category_id=category.id, student_id=student.id,
                institution_id=institution.id, campus_id=campus.id,
                uploaded_by_user_id=user.id, document_purpose="academic_demo",
                is_official=False,
            ))

    db.commit()
    print(f"Seed concluído. Usuário: {USERNAME} | Senha: {PASSWORD}")
    print(f"Storage de demonstração: {demo_root.resolve()}")


def remove(db: object) -> None:
    demo_type_ids = [
        row.id for row in db.query(DocumentType.id).filter(DocumentType.name.like(f"{PREFIX}%")).all()
    ]
    student = db.get(models.Student, STUDENT_ID)
    if student:
        db.query(GEDDocument).filter_by(student_id=student.id).delete(synchronize_session=False)
    db.query(models.Enrollment).filter_by(student_id=STUDENT_ID).delete(synchronize_session=False)
    if student:
        db.delete(student)
    if demo_type_ids:
        db.query(DocumentTypeIndex).filter(DocumentTypeIndex.document_type_id.in_(demo_type_ids)).delete(synchronize_session=False)
        db.query(DocumentTypeVersion).filter(DocumentTypeVersion.document_type_id.in_(demo_type_ids)).delete(synchronize_session=False)
        db.query(UserDocumentType).filter(UserDocumentType.document_type_id.in_(demo_type_ids)).delete(synchronize_session=False)
    db.query(DocumentType).filter(DocumentType.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    db.query(DocumentCategory).filter(DocumentCategory.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    db.query(GedIndex).filter(GedIndex.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    db.query(StorageRule).filter(StorageRule.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    db.query(models.InstitutionSettings).filter_by(institution_id=INSTITUTION_ID).delete(synchronize_session=False)
    db.query(models.User).filter_by(id=USER_ID).delete(synchronize_session=False)
    db.query(models.Campus).filter_by(id=CAMPUS_ID).delete(synchronize_session=False)
    db.query(models.Institution).filter_by(id=INSTITUTION_ID).delete(synchronize_session=False)
    db.commit()
    shutil.rmtree(STORAGE_ROOT / "demo_academico", ignore_errors=True)
    print("Dados e diretórios DEMO-ACADEMICO removidos.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", action="store_true", help="remove somente os dados DEMO-ACADEMICO")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        remove(db) if args.remove else seed(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
