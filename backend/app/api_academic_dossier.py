from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app import models
from app.auth import get_current_active_user
from app.models_academic_dossier import AcademicDossier, DossierDocument, AcademicValidation
from app.models_ged import GEDDocument
from app.schemas_academic_dossier import (
    AcademicDossierCreate, AcademicDossierResponse,
    DossierDocumentCreate, AcademicValidationResponse
)

router = APIRouter(tags=["GED - Vida Acadêmica (Dossiê e Validações)"])

@router.post("/api/dossiers", response_model=AcademicDossierResponse)
def create_dossier(
    payload: AcademicDossierCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    student = db.query(models.Student).filter(models.Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == payload.enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    dossier = AcademicDossier(
        id=str(uuid.uuid4()),
        student_id=payload.student_id,
        enrollment_id=payload.enrollment_id,
        dossier_type=payload.dossier_type,
        group_id=payload.group_id or (str(uuid.uuid4()) if payload.dossier_type == "partial_history" else None),
        status="open"
    )
    db.add(dossier)
    db.commit()
    db.refresh(dossier)
    return dossier


@router.get("/api/dossiers", response_model=List[AcademicDossierResponse])
def get_dossiers(
    student_id: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(AcademicDossier)
    if student_id:
        query = query.filter(AcademicDossier.student_id == student_id)

    # Security: filter by institution
    if current_user.role != "admin_global":
        query = query.join(models.Student).filter(models.Student.institution_id == current_user.institution_id)

    return query.all()


@router.post("/api/dossiers/{dossier_id}/documents", response_model=AcademicDossierResponse)
def add_document_to_dossier(
    dossier_id: str,
    payload: DossierDocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    dossier = db.query(AcademicDossier).filter(AcademicDossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    if (
        current_user.role != "admin_global"
        and dossier.student.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=403, detail="Dossiê fora da instituição do usuário.")

    document = db.query(GEDDocument).filter(GEDDocument.id == payload.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    exigir_documento(db, current_user, document, "editar")

    dossier_doc = DossierDocument(
        id=str(uuid.uuid4()),
        dossier_id=dossier_id,
        document_id=payload.document_id,
        document_type_code=payload.document_type_code,
        file_hash=payload.file_hash,
        version_number=payload.version_number
    )
    db.add(dossier_doc)
    db.commit()
    db.refresh(dossier)
    return dossier


@router.post("/api/dossiers/{dossier_id}/validate", response_model=AcademicDossierResponse)
def validate_dossier(
    dossier_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    dossier = db.query(AcademicDossier).filter(AcademicDossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")

    # Clear previous validations
    db.query(AcademicValidation).filter(AcademicValidation.dossier_id == dossier_id).delete()

    # Run validations
    rules = []

    # Rule 1: Student has CPF
    has_cpf = bool(dossier.student.cpf)
    rules.append(AcademicValidation(
        id=str(uuid.uuid4()), dossier_id=dossier_id, rule_name="Student has CPF",
        status="passed" if has_cpf else "failed",
        message="CPF is present" if has_cpf else "Student CPF is missing"
    ))

    # Rule 2: Enrollment is graduated (for diploma)
    if dossier.dossier_type in ("diploma", "partial_history"):
        if dossier.dossier_type == "partial_history" and not dossier.group_id:
            dossier.group_id = str(uuid.uuid4())
        is_grad = dossier.enrollment.status == "graduated"
        if dossier.dossier_type == "diploma":
            rules.append(AcademicValidation(
                id=str(uuid.uuid4()), dossier_id=dossier_id, rule_name="Enrollment Status is Graduated",
                status="passed" if is_grad else "failed",
                message="Enrollment is graduated" if is_grad else f"Status is {dossier.enrollment.status}"
            ))

        # Rule 3: Has required documents
        doc_types = [d.document_type_code for d in dossier.documents]
        required = ["RG", "HISTORICO_PARCIAL"] if dossier.dossier_type == "partial_history" else ["RG", "HISTORICO"]
        for req in required:
            has_doc = req in doc_types
            rules.append(AcademicValidation(
                id=str(uuid.uuid4()), dossier_id=dossier_id, rule_name=f"Has {req} document",
                status="passed" if has_doc else "failed",
                message=f"{req} is present" if has_doc else f"Missing {req} document"
            ))

    # Add all validation rules to DB
    for r in rules:
        db.add(r)

    # Update dossier status
    all_passed = all(r.status == "passed" for r in rules)
    dossier.status = "approved" if all_passed else "in_validation"

    db.commit()
    db.refresh(dossier)
    return dossier


import io
import zipfile
import uuid
import os
from fastapi.responses import StreamingResponse
from app.pdf_utils import convert_html_to_pdf_libreoffice
from app.rvdd_generator import generate_rvdd_html
from app.storage import load_file
from app.document_permissions import exigir_documento

@router.post("/api/dossiers/{dossier_id}/close", response_model=AcademicDossierResponse)
def close_dossier(
    dossier_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    from app.models_ged import GEDDocumentStatus, DocumentTransitionHistory

    dossier = db.query(AcademicDossier).filter(AcademicDossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    if (
        current_user.role != "admin_global"
        and dossier.student.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=403, detail="Dossiê fora da instituição do usuário.")

    dossier.status = "closed"

    for d in dossier.documents:
        ged_doc = db.query(GEDDocument).filter(GEDDocument.id == d.document_id).first()
        if ged_doc and ged_doc.status not in (GEDDocumentStatus.ANULADO, GEDDocumentStatus.REVOGADO, GEDDocumentStatus.ARQUIVADO):
            exigir_documento(db, current_user, ged_doc, "arquivar")
            old_status = ged_doc.status
            ged_doc.status = GEDDocumentStatus.ARQUIVADO
            transition = DocumentTransitionHistory(
                document_id=ged_doc.id,
                from_status=old_status,
                to_status=GEDDocumentStatus.ARQUIVADO,
                comments="Dossiê acadêmico fechado e arquivado",
                changed_by_user_id=current_user.id
            )
            db.add(transition)

    db.commit()
    db.refresh(dossier)
    return dossier

@router.get("/api/dossiers/{dossier_id}/export")
async def export_dossier(
    dossier_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    dossier = db.query(AcademicDossier).filter(AcademicDossier.id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    if (
        current_user.role != "admin_global"
        and dossier.student.institution_id != current_user.institution_id
    ):
        raise HTTPException(status_code=403, detail="Dossiê fora da instituição do usuário.")
    for dossier_document in dossier.documents:
        ged_doc = db.query(GEDDocument).filter(
            GEDDocument.id == dossier_document.document_id
        ).first()
        if ged_doc:
            exigir_documento(db, current_user, ged_doc, "exportar")

    # Generate RVDD (Mocking real data source)
    rvdd_html = generate_rvdd_html(dossier.id, dossier.student.full_name, dossier.enrollment.course_name)

    # Convert RVDD HTML to PDF via LibreOffice
    rvdd_pdf_bytes = await convert_html_to_pdf_libreoffice(rvdd_html)

    # We create a ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Manifest
        manifest = f"Dossier ID: {dossier.id}\nStudent: {dossier.student.full_name}\nStatus: {dossier.status}\n"
        manifest += "\nDocuments:\n"
        for d in dossier.documents:
            manifest += f"- {d.document_type_code} (Version: {d.version_number}, Hash: {d.file_hash})\n"
        manifest += f"- RVDD (Generated automatically at {dossier.updated_at})\n"
        zip_file.writestr("manifest.txt", manifest)

        # 2. Add actual documents
        for d in dossier.documents:
            ged_doc = db.query(GEDDocument).filter(GEDDocument.id == d.document_id).first()
            if not ged_doc:
                raise HTTPException(status_code=409, detail=f"Documento {d.document_id} não está disponível.")
            try:
                file_data = load_file(ged_doc.file_path)
            except OSError as exc:
                raise HTTPException(
                    status_code=409,
                    detail=f"Arquivo físico do documento {d.document_id} não está disponível.",
                ) from exc
            extension = os.path.splitext(ged_doc.file_path)[1].lower() or ".bin"
            zip_file.writestr(
                f"{d.document_type_code}_{d.version_number}{extension}",
                file_data,
            )

        # 3. Add generated RVDD PDF
        zip_file.writestr("RVDD_Final.pdf", rvdd_pdf_bytes)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=dossier_{dossier.id}.zip"}
    )
