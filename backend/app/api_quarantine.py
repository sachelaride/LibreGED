from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import os

from app.database import get_db
from app import models
from app.auth import get_current_active_user, role_checker
from app.models_ged import GEDDocument, GEDDocumentStatus, DocumentTransitionHistory
from app.schemas_ged import GEDDocumentResponse

from app.document_permissions import exigir_documento, tem_permissao

router = APIRouter(tags=["Administração - Quarentena"])

QuarantineRoles = Depends(role_checker(["admin_global", "admin_instituicao"]))

@router.get("/api/quarantine", response_model=List[GEDDocumentResponse])
def list_quarantined_documents(
    db: Session = Depends(get_db),
    current_user: models.User = QuarantineRoles
):
    query = db.query(GEDDocument).filter(GEDDocument.status == GEDDocumentStatus.QUARENTENA)
    if current_user.role != "admin_global":
        query = query.filter(GEDDocument.institution_id == current_user.institution_id)
        
    documentos = query.all()
    if current_user.role != "admin_global":
        if not current_user.institution_id or current_user.campus_id:
            return []
        documentos = [d for d in documentos if tem_permissao(db, current_user, d.category_id, "consultar")]
    return documentos

@router.post("/api/quarantine/{document_id}/release", response_model=GEDDocumentResponse)
def release_from_quarantine(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = QuarantineRoles
):
    doc = db.query(GEDDocument).filter(GEDDocument.id == document_id, GEDDocument.status == GEDDocumentStatus.QUARENTENA).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado na quarentena")
        
    if current_user.role != "admin_global" and doc.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    exigir_documento(db, current_user, doc, "liberar_quarentena")
    doc.status = GEDDocumentStatus.PENDENTE_VALIDACAO
    
    transition = DocumentTransitionHistory(
        document_id=doc.id,
        from_status=GEDDocumentStatus.QUARENTENA,
        to_status=GEDDocumentStatus.PENDENTE_VALIDACAO,
        changed_by_user_id=current_user.id,
        comments="Arquivo liberado da quarentena manualmente por um administrador."
    )
    db.add(transition)
    
    # Audit log
    from app.main import add_audit
    add_audit(db, "document", doc.id, "quarantine_release", "Administrator released document from quarantine", current_user.id)
    
    db.commit()
    db.refresh(doc)
    return doc

@router.delete("/api/quarantine/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quarantined_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = QuarantineRoles
):
    doc = db.query(GEDDocument).filter(GEDDocument.id == document_id, GEDDocument.status == GEDDocumentStatus.QUARENTENA).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado na quarentena")
        
    if current_user.role != "admin_global" and doc.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
        
    from app.api_document_operations import excluir_documento
    return excluir_documento(document_id, db, current_user)
