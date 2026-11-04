from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, models_academic_dossier, models_ged
from app.auth import require_module_access
from app.database import get_db
from app.modules.data_store import documents, enrollments, get_student_detail, grades, students

router = APIRouter(prefix="/aluno", tags=["Aluno"])


class BoletimRequest(BaseModel):
    student_id: str


class EnrollmentRequest(BaseModel):
    student_id: str
    course: str
    semester: str
    status: str | None = None


class DossierCreate(BaseModel):
    student_id: str
    enrollment_id: str | None = None
    dossier_type: str = "diploma"
    group_id: str | None = None


class DossierDocumentLink(BaseModel):
    document_id: str
    document_type_code: str = "RG"
    file_hash: str = "hash-pendente"
    version_number: int = 1


def _resolve_student(db: Session, user: Any, requested_student_id: str | None) -> str:
    if user.role == "aluno":
        if not user.institution_id:
            raise HTTPException(status_code=403, detail="Conta de aluno sem instituição vinculada")
        student = db.query(models.Student).filter(
            models.Student.user_id == user.id,
            models.Student.institution_id == user.institution_id,
        ).first()
        if student is None:
            raise HTTPException(status_code=403, detail="Conta de aluno ainda não vinculada ao cadastro acadêmico")
        if user.campus_id and student.campus_id != user.campus_id:
            raise HTTPException(status_code=403, detail="Cadastro acadêmico fora do campus da conta")
        if requested_student_id and requested_student_id != student.id:
            raise HTTPException(status_code=403, detail="Acesso restrito ao próprio cadastro acadêmico")
        return student.id

    resolved_student_id = requested_student_id or "ALU-1001"
    student = db.get(models.Student, resolved_student_id)
    if student is not None:
        if user.role != "admin_global":
            if not user.institution_id:
                raise HTTPException(status_code=403, detail="Usuário sem instituição vinculada")
            if student.institution_id != user.institution_id:
                raise HTTPException(status_code=404, detail="Aluno não encontrado")
            if user.campus_id and student.campus_id != user.campus_id:
                raise HTTPException(status_code=404, detail="Aluno não encontrado")
        return student.id
    if user.role == "admin_global" and resolved_student_id in students:
        return resolved_student_id
    if (
        user.role == "admin_global"
        and requested_student_id is None
        and "ALU-1001" in students
    ):
        return "ALU-1001"
    raise HTTPException(status_code=404, detail="Aluno não encontrado")


@router.get("/dashboard")
def aluno_dashboard(
    student_id: str | None = Query(default=None),
    user: Any = Depends(require_module_access("aluno")),
    db: Session = Depends(get_db),
):
    resolved_student_id = _resolve_student(db, user, student_id)
    detail = get_student_detail(resolved_student_id)
    enrollment = detail.get("enrollment") if detail else None
    student_record = db.get(models.Student, resolved_student_id)
    student_grades = grades.get(resolved_student_id, {})
    values = list(student_grades.values())
    total_disciplines = len(values)
    average = round(sum(values) / max(1, total_disciplines), 2) if values else 0.0
    pending_documents = sum(1 for doc in documents.values() if doc.get("student_id") == resolved_student_id and doc.get("status") == "pendente")
    return {
        "module": "aluno",
        "title": "Portal do Aluno",
        "student_id": resolved_student_id,
        "student_name": (
            student_record.full_name if student_record
            else students.get(resolved_student_id, {}).get("full_name", "Aluno")
        ),
        "stats": {
            "documentos_disponiveis": sum(1 for doc in documents.values() if doc.get("student_id") == resolved_student_id),
            "disciplinas": total_disciplines,
            "media_geral": average,
            "matriculas_ativas": 1 if enrollment and enrollment.get("status") == "matriculado" else 0,
            "matriculas_pendentes": 1 if enrollment and enrollment.get("status") == "pendente" else 0,
            "documentos_pendentes": pending_documents,
            "status_matricula": enrollment.get("status") if enrollment else "sem_matricula",
        },
        "features": [
            "Boletim",
            "Documentos",
            "Matrícula",
            "Histórico e compromissos",
            "Acompanhamento de desempenho",
            "Financeiro do curso",
        ],
        "user": getattr(user, "username", None),
    }


@router.get("/boletim")
def boletim(
    student_id: str | None = Query(default=None),
    user: Any = Depends(require_module_access("aluno")),
    db: Session = Depends(get_db),
):
    resolved_student_id = _resolve_student(db, user, student_id)
    grades_for_student = grades.get(resolved_student_id, {})
    student = students.get(resolved_student_id, {})
    student_record = db.get(models.Student, resolved_student_id)
    student_name = student_record.full_name if student_record else student.get("full_name")
    if not grades_for_student:
        return {"module": "aluno", "student_id": resolved_student_id, "student_name": student_name, "grades": {}}
    values = list(grades_for_student.values())
    return {
        "module": "aluno",
        "student_id": resolved_student_id,
        "student_name": student_name,
        "course_name": student.get("course"),
        "average": round(sum(values) / len(values), 2),
        "status": student.get("enrollment_status", "matriculado"),
        "grades": grades_for_student,
    }


@router.get("/documentos")
def documentos(
    student_id: str | None = Query(default=None),
    user: Any = Depends(require_module_access("aluno")),
    db: Session = Depends(get_db),
):
    resolved_student_id = _resolve_student(db, user, student_id)
    persisted_documents = db.query(models_ged.GEDDocument).filter(
        models_ged.GEDDocument.student_id == resolved_student_id
    ).all()
    persisted_items = [{
        "id": document.id,
        "student_id": document.student_id,
        "title": document.title,
        "document_type": document.category.name if document.category else "Acadêmico",
        "status": document.status.value if hasattr(document.status, "value") else str(document.status),
    } for document in persisted_documents]
    legacy_items = [
        doc for doc in documents.values()
        if doc.get("student_id") == resolved_student_id
    ]
    persisted_ids = {item["id"] for item in persisted_items}
    return {
        "module": "aluno",
        "student_id": resolved_student_id,
        "items": persisted_items + [
            item for item in legacy_items if item.get("id") not in persisted_ids
        ],
    }


@router.get("/historico")
def historico(
    student_id: str | None = Query(default=None),
    user: Any = Depends(require_module_access("aluno")),
    db: Session = Depends(get_db),
):
    resolved_student_id = _resolve_student(db, user, student_id)
    detail = get_student_detail(resolved_student_id)
    student_record = db.get(models.Student, resolved_student_id)
    return {
        "module": "aluno",
        "student_id": resolved_student_id,
        "student_name": (
            student_record.full_name if student_record
            else students.get(resolved_student_id, {}).get("full_name")
        ),
        "journey": detail.get("journey", []) if detail else [],
        "documents": detail.get("documents", []) if detail else [],
        "finances": detail.get("finances", []) if detail else [],
    }


@router.post("/matricula")
def request_enrollment(
    payload: EnrollmentRequest,
    user: Any = Depends(require_module_access("aluno")),
    db: Session = Depends(get_db),
):
    if not payload.student_id:
        raise HTTPException(status_code=400, detail="Código do aluno obrigatório")
    resolved_student_id = _resolve_student(db, user, payload.student_id)
    detail = get_student_detail(resolved_student_id)
    student_record = db.get(models.Student, resolved_student_id)
    return {
        "message": "Solicitação de matrícula enviada",
        "module": "aluno",
        "request": {
            "student_id": resolved_student_id,
            "course": payload.course,
            "semester": payload.semester,
            "status": payload.status or "pendente",
            "student_profile": (
                detail.get("student") if detail
                else {"id": student_record.id, "full_name": student_record.full_name}
                if student_record else None
            ),
            "enrollment": detail.get("enrollment") if detail else None,
        },
    }


@router.get("/dossie")
def get_student_dossier(student_id: str | None = Query(default=None), user: Any = Depends(require_module_access("aluno")), db: Session = Depends(get_db)):
    resolved_student_id = _resolve_student(db, user, student_id)
    student = db.query(models.Student).filter(models.Student.id == resolved_student_id).first()
    if student is None:
        legacy_student = students.get(resolved_student_id)
        if not legacy_student:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        return {
            "module": "aluno",
            "student_id": resolved_student_id,
            "student_name": legacy_student.get("full_name"),
            "dossiers": [],
            "documents": [doc for doc in documents.values() if doc.get("student_id") == resolved_student_id],
        }

    dossiers = db.query(models_academic_dossier.AcademicDossier).filter(models_academic_dossier.AcademicDossier.student_id == student.id).all()
    items = []
    for dossier in dossiers:
        doc_items = db.query(models_academic_dossier.DossierDocument).filter(models_academic_dossier.DossierDocument.dossier_id == dossier.id).all()
        items.append({
            "dossier_id": dossier.id,
            "dossier_type": dossier.dossier_type,
            "status": dossier.status,
            "student_id": dossier.student_id,
            "enrollment_id": dossier.enrollment_id,
            "documents": [
                {
                    "document_id": doc.document_id,
                    "document_type_code": doc.document_type_code,
                    "version_number": doc.version_number,
                }
                for doc in doc_items
            ],
        })

    return {
        "module": "aluno",
        "student_id": resolved_student_id,
        "student_name": student.full_name,
        "dossiers": items,
        "documents": [
            {
                "document_id": doc.id,
                "title": doc.title,
                "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
                "document_type": doc.category.name if doc.category else "Acadêmico",
            }
            for doc in db.query(models_ged.GEDDocument).filter(models_ged.GEDDocument.student_id == student.id).all()
        ],
    }


@router.post("/dossie")
def create_student_dossier(payload: DossierCreate, user: Any = Depends(require_module_access("aluno")), db: Session = Depends(get_db)):
    resolved_student_id = _resolve_student(db, user, payload.student_id)
    student = db.query(models.Student).filter(models.Student.id == resolved_student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    enrollment_query = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student.id,
        models.Enrollment.institution_id == student.institution_id,
    )
    if payload.enrollment_id:
        enrollment = db.query(models.Enrollment).filter(
            models.Enrollment.id == payload.enrollment_id,
            models.Enrollment.student_id == student.id,
            models.Enrollment.institution_id == student.institution_id,
        ).first()
    else:
        enrollment = enrollment_query.order_by(
            models.Enrollment.created_at.desc()
        ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada para o aluno")

    dossier = models_academic_dossier.AcademicDossier(
        id=str(uuid4()),
        student_id=student.id,
        enrollment_id=enrollment.id,
        dossier_type=payload.dossier_type,
        group_id=payload.group_id or str(uuid4()),
        status="open",
    )
    db.add(dossier)
    db.commit()
    db.refresh(dossier)
    return {"message": "Dossiê acadêmico criado", "module": "aluno", "dossier": {
        "dossier_id": dossier.id,
        "student_id": dossier.student_id,
        "enrollment_id": dossier.enrollment_id,
        "status": dossier.status,
        "dossier_type": dossier.dossier_type,
    }}


@router.post("/dossie/{dossier_id}/documentos")
def link_document_to_student_dossier(dossier_id: str, payload: DossierDocumentLink, user: Any = Depends(require_module_access("aluno")), db: Session = Depends(get_db)):
    dossier = db.query(models_academic_dossier.AcademicDossier).filter(models_academic_dossier.AcademicDossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossiê não encontrado")
    _resolve_student(db, user, dossier.student_id)

    document = db.query(models_ged.GEDDocument).filter(models_ged.GEDDocument.id == payload.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento GED não encontrado")
    if document.student_id != dossier.student_id:
        raise HTTPException(status_code=409, detail="Documento não pertence ao aluno do dossiê")

    relationship = models_academic_dossier.DossierDocument(
        id=str(uuid4()),
        dossier_id=dossier.id,
        document_id=document.id,
        document_type_code=payload.document_type_code,
        file_hash=payload.file_hash,
        version_number=payload.version_number,
    )
    db.add(relationship)
    db.commit()
    return {
        "message": "Documento ligado ao dossiê acadêmico",
        "module": "aluno",
        "dossier_id": dossier.id,
        "document_id": document.id,
        "document_type_code": payload.document_type_code,
    }
