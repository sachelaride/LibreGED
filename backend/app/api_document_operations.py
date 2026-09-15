"""Operações documentais protegidas pelos privilégios concedidos no admin."""
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, utc_now
from app.models_ged import GEDDocument, GEDDocumentStatus, DocumentTransitionHistory
from app.models_ged_config import DocumentType
from app.document_permissions import exigir_documento, auditar, ACOES, tem_permissao
from app.schemas_ged import GEDDocumentResponse
from app.storage import STORAGE_ROOT

router = APIRouter(prefix="/api/documents", tags=["Operações documentais"])


class EdicaoDocumento(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=500)


def obter_documento(db, usuario, identificador, acao):
    documento = db.query(GEDDocument).filter_by(id=identificador).with_for_update().first()
    if documento is None:
        raise HTTPException(404, "Documento não encontrado.")
    exigir_documento(db, usuario, documento, acao)
    return documento


def validar_exclusao(db, documento):
    tipo = db.get(DocumentType, documento.category_id)
    if tipo is None or tipo.legal_hold:
        raise HTTPException(409, "Exclusão bloqueada: política ausente ou preservação legal ativa.")
    if documento.status not in (GEDDocumentStatus.RASCUNHO, GEDDocumentStatus.REJEITADO, GEDDocumentStatus.QUARENTENA):
        raise HTTPException(409, "Este estado documental não permite exclusão direta.")
    if documento.created_at + timedelta(days=365 * tipo.retention_years) > utc_now():
        raise HTTPException(409, "O prazo de retenção do documento ainda não terminou.")


def caminho_seguro(documento):
    caminho = Path(documento.file_path).resolve()
    if not caminho.is_relative_to(STORAGE_ROOT.resolve()):
        raise HTTPException(409, "O arquivo não pertence ao armazenamento local configurado.")
    if not caminho.is_file():
        raise HTTPException(404, "Arquivo não encontrado.")
    return caminho


@router.get("/{documento_id}/permissions")
def permissoes_documento(documento_id: str, db: Session = Depends(get_db), usuario: User = Depends(get_current_active_user)):
    documento = obter_documento(db, usuario, documento_id, "consultar")
    return {acao: tem_permissao(db, usuario, documento.category_id, acao) for acao in ACOES}


@router.get("/{documento_id}/details", response_model=GEDDocumentResponse)
def consultar_documento(documento_id: str, db: Session = Depends(get_db), usuario: User = Depends(get_current_active_user)):
    return obter_documento(db, usuario, documento_id, "consultar")


@router.put("/{documento_id}", response_model=GEDDocumentResponse)
def editar_documento(documento_id: str, dados: EdicaoDocumento, db: Session = Depends(get_db), usuario: User = Depends(get_current_active_user)):
    documento = obter_documento(db, usuario, documento_id, "editar")
    if documento.status in (GEDDocumentStatus.ASSINADO, GEDDocumentStatus.ARQUIVADO):
        raise HTTPException(409, "Documento assinado ou arquivado não permite edição direta.")
    auditar(db, usuario, "document", documento_id, "editar", f"Título anterior: {documento.title}; novo: {dados.title}")
    documento.title = dados.title
    db.commit()
    return documento


@router.post("/{documento_id}/archive", response_model=GEDDocumentResponse)
def arquivar_documento(documento_id: str, db: Session = Depends(get_db), usuario: User = Depends(get_current_active_user)):
    documento = obter_documento(db, usuario, documento_id, "arquivar")
    if documento.status not in (GEDDocumentStatus.VALIDO, GEDDocumentStatus.ASSINADO):
        raise HTTPException(409, "Somente documentos válidos ou assinados podem ser arquivados.")
    autor = db.get(User, usuario.id)
    db.add(DocumentTransitionHistory(document_id=documento.id, from_status=documento.status,
        to_status=GEDDocumentStatus.ARQUIVADO, changed_by_user_id=autor.id if autor else None,
        comments="Arquivamento autorizado por privilégio documental."))
    documento.status = GEDDocumentStatus.ARQUIVADO
    auditar(db, usuario, "document", documento_id, "arquivar", "Documento arquivado.")
    db.commit()
    return documento


@router.get("/{documento_id}/download")
def baixar_documento(documento_id: str, db: Session = Depends(get_db), usuario: User = Depends(get_current_active_user)):
    documento = obter_documento(db, usuario, documento_id, "download")
    if documento.status == GEDDocumentStatus.QUARENTENA:
        raise HTTPException(409, "Arquivo em quarentena não pode ser baixado.")
    caminho = caminho_seguro(documento)
    auditar(db, usuario, "document", documento_id, "download", "Download autorizado.")
    db.commit()
    return FileResponse(caminho, filename=caminho.name, media_type="application/octet-stream")


@router.delete("/{documento_id}", status_code=204)
def excluir_documento(documento_id: str, db: Session = Depends(get_db), usuario: User = Depends(get_current_active_user)):
    documento = obter_documento(db, usuario, documento_id, "excluir")
    validar_exclusao(db, documento)
    caminho = caminho_seguro(documento)
    temporario = caminho.with_name(f".exclusao-{documento_id}-{uuid4().hex}.pending")
    auditar(db, usuario, "document", documento_id, "excluir", "Exclusão autorizada após retenção.")
    db.delete(documento)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Documento vinculado a outros registros; exclusão bloqueada.")
    try:
        caminho.rename(temporario)
        db.commit()
    except Exception:
        db.rollback()
        if temporario.exists():
            temporario.rename(caminho)
        raise
    # Após o commit, falhas de limpeza preservam o arquivo pendente para operação.
    temporario.unlink(missing_ok=True)
