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


def _resolve_student(student_id: str | None) -> str:
    if student_id and student_id in students:
        return student_id
    return "ALU-1001"


@router.get("/dashboard")
def aluno_dashboard(student_id: str | None = Query(default=None), user: Any = Depends(require_module_access("aluno"))):
    resolved_student_id = _resolve_student(student_id)
    detail = get_student_detail(resolved_student_id)
    enrollment = detail.get("enrollment") if detail else None
    student_grades = grades.get(resolved_student_id, {})
    values = list(student_grades.values())
    total_disciplines = len(values)
    average = round(sum(values) / max(1, total_disciplines), 2) if values else 0.0
    pending_documents = sum(1 for doc in documents.values() if doc.get("student_id") == resolved_student_id and doc.get("status") == "pendente")
    return {
        "module": "aluno",
        "title": "Portal do Aluno",
        "student_id": resolved_student_id,
        "student_name": students.get(resolved_student_id, {}).get("full_name", "Aluno"),
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
def boletim(student_id: str | None = Query(default=None), user: Any = Depends(require_module_access("aluno"))):
    resolved_student_id = _resolve_student(student_id)
    grades_for_student = grades.get(resolved_student_id, {})
    student = students.get(resolved_student_id, {})
    if not grades_for_student:
        return {"module": "aluno", "student_id": resolved_student_id, "student_name": student.get("full_name"), "grades": {}}
    values = list(grades_for_student.values())
    return {
        "module": "aluno",
        "student_id": resolved_student_id,
        "student_name": student.get("full_name"),
        "course_name": student.get("course"),
        "average": round(sum(values) / len(values), 2),
        "status": student.get("enrollment_status", "matriculado"),
        "grades": grades_for_student,
    }


@router.get("/documentos")
def documentos(student_id: str | None = Query(default=None), user: Any = Depends(require_module_access("aluno"))):
    resolved_student_id = _resolve_student(student_id)
    return {
        "module": "aluno",
        "student_id": resolved_student_id,
        "items": [doc for doc in documents.values() if doc.get("student_id") == resolved_student_id],
    }


@router.get("/historico")
def historico(student_id: str | None = Query(default=None), user: Any = Depends(require_module_access("aluno"))):
    resolved_student_id = _resolve_student(student_id)
    detail = get_student_detail(resolved_student_id)
    return {
        "module": "aluno",
        "student_id": resolved_student_id,
        "student_name": students.get(resolved_student_id, {}).get("full_name"),
        "journey": detail.get("journey", []) if detail else [],
        "documents": detail.get("documents", []) if detail else [],
        "finances": detail.get("finances", []) if detail else [],
    }


@router.post("/matricula")
def request_enrollment(payload: EnrollmentRequest, user: Any = Depends(require_module_access("aluno"))):
    if not payload.student_id:
        raise HTTPException(status_code=400, detail="Código do aluno obrigatório")
    detail = get_student_detail(payload.student_id)
    return {
        "message": "Solicitação de matrícula enviada",
        "module": "aluno",
        "request": {
            "student_id": payload.student_id,
            "course": payload.course,
            "semester": payload.semester,
            "status": payload.status or "pendente",
            "student_profile": detail.get("student") if detail else None,
            "enrollment": detail.get("enrollment") if detail else None,
        },
    }


@router.get("/dossie")
def get_student_dossier(student_id: str | None = Query(default=None), user: Any = Depends(require_module_access("aluno")), db: Session = Depends(get_db)):
    resolved_student_id = _resolve_student(student_id)
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
    student = db.query(models.Student).filter(models.Student.id == payload.student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    enrollment = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.student_id == payload.student_id)
        .order_by(models.Enrollment.created_at.desc())
        .first()
    )
    if not enrollment and payload.enrollment_id:
        enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == payload.enrollment_id).first()
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

    document = db.query(models_ged.GEDDocument).filter(models_ged.GEDDocument.id == payload.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento GED não encontrado")

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
