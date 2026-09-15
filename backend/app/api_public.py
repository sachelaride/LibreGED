"""Public, data-minimized document verification."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models_ged import GEDDocument, GEDDocumentStatus

router = APIRouter(prefix="/api/public", tags=["Consulta pública"])


class PublicDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_code: str
    title: str
    status: GEDDocumentStatus
    document_purpose: str
    is_official: bool
    created_at: datetime
    verification_url: str


@router.get("/documents/{public_code}", response_model=PublicDocumentResponse)
def consultar_documento_publico(public_code: str, db: Session = Depends(get_db)):
    if len(public_code) < 20 or len(public_code) > 100:
        raise HTTPException(404, "Documento não encontrado.")
    documento = db.query(GEDDocument).filter(
        GEDDocument.public_code == public_code
    ).first()
    if documento is None or documento.status in (
        GEDDocumentStatus.RASCUNHO,
        GEDDocumentStatus.PENDENTE_VALIDACAO,
        GEDDocumentStatus.QUARENTENA,
        GEDDocumentStatus.REJEITADO,
    ):
        raise HTTPException(404, "Documento não encontrado ou ainda não publicado.")
    return PublicDocumentResponse(
        public_code=documento.public_code,
        title=documento.title,
        status=documento.status,
        document_purpose=documento.document_purpose,
        is_official=documento.is_official,
        created_at=documento.created_at,
        verification_url=f"/api/public/documents/{documento.public_code}",
    )
