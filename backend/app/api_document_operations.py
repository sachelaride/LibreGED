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
from app.auth import get_current_active_user, role_checker, verify_document_ownership
from app.models import User, utc_now
from app.models_ged import (
    GEDDocument, GEDDocumentStatus, DocumentTransitionHistory,
    DocumentLegalHold,
)
from app.models_ged_config import DocumentType
from app.document_permissions import exigir_documento, auditar, ACOES, tem_permissao
from app.schemas_ged import (
    GEDDocumentResponse, DocumentSuspensionRequest, DocumentDispositionRequest,
    SecondCopyRequest,
    LegalHoldRequest,
)
from app.storage import STORAGE_ROOT, save_file

router = APIRouter(prefix="/api/documents", tags=["Operações documentais"])


class EdicaoDocumento(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=500)


def obter_documento(db, usuario, identificador, acao):
    documento = db.query(GEDDocument).filter_by(id=identificador).with_for_update().first()
    if documento is None:
        raise HTTPException(404, "Documento não encontrado.")
    verify_document_ownership(usuario, documento)
    if documento.status in (
        GEDDocumentStatus.SUSPENSO,
        GEDDocumentStatus.REVOGADO,
        GEDDocumentStatus.ANULADO,
    ) and acao != "consultar":
        raise HTTPException(409, "Documento indisponível neste estado; regularize-o antes de executar esta operação.")
    exigir_documento(db, usuario, documento, acao)
    return documento


@router.post("/{documento_id}/suspend", response_model=GEDDocumentResponse)
def suspender_documento(
    documento_id: str,
    dados: DocumentSuspensionRequest,
    db: Session = Depends(get_db),
    usuario: User = Depends(role_checker(["admin_global", "admin_instituicao"])),
):
    documento = db.query(GEDDocument).filter_by(id=documento_id).with_for_update().first()
    if documento is None:
        raise HTTPException(404, "Documento não encontrado.")
    verify_document_ownership(usuario, documento)
    if not dados.reason.strip():
        raise HTTPException(422, "Informe o motivo da suspensão.")
    if documento.status == GEDDocumentStatus.SUSPENSO:
        raise HTTPException(409, "Documento já está suspenso.")
    documento.suspended_previous_status = documento.status.value
    documento.suspension_reason = dados.reason.strip()
    anterior = documento.status
    documento.status = GEDDocumentStatus.SUSPENSO
    db.add(DocumentTransitionHistory(
        document_id=documento.id, from_status=anterior,
        to_status=GEDDocumentStatus.SUSPENSO, changed_by_user_id=usuario.id,
        comments=dados.reason.strip(),
    ))
    auditar(db, usuario, "document", documento.id, "suspender", dados.reason.strip())
    db.commit()
    db.refresh(documento)
    return documento


@router.post("/{documento_id}/reactivate", response_model=GEDDocumentResponse)
def reativar_documento(
    documento_id: str,
    db: Session = Depends(get_db),
    usuario: User = Depends(role_checker(["admin_global", "admin_instituicao"])),
):
    documento = db.query(GEDDocument).filter_by(id=documento_id).with_for_update().first()
    if documento is None:
        raise HTTPException(404, "Documento não encontrado.")
    verify_document_ownership(usuario, documento)
    if documento.status != GEDDocumentStatus.SUSPENSO:
        raise HTTPException(409, "Documento não está suspenso.")
    try:
        anterior = GEDDocumentStatus(documento.suspended_previous_status or GEDDocumentStatus.PENDENTE_VALIDACAO.value)
    except ValueError as erro:
        raise HTTPException(409, "Estado anterior inválido; reativação bloqueada.") from erro
    documento.status = anterior
    documento.suspended_previous_status = None
    documento.suspension_reason = None
    db.add(DocumentTransitionHistory(
        document_id=documento.id, from_status=GEDDocumentStatus.SUSPENSO,
        to_status=anterior, changed_by_user_id=usuario.id,
        comments="Documento reativado administrativamente.",
    ))
    auditar(db, usuario, "document", documento.id, "reativar", f"Estado restaurado: {anterior.value}")
    db.commit()
    db.refresh(documento)
    return documento


def _encerrar_documento(documento_id, dados, db, usuario, destino, campo, acao, permitidos):
    documento = db.query(GEDDocument).filter_by(id=documento_id).with_for_update().first()
    if documento is None:
        raise HTTPException(404, "Documento não encontrado.")
    verify_document_ownership(usuario, documento)
    if not dados.reason.strip():
        raise HTTPException(422, "Informe a justificativa.")
    if documento.status not in permitidos:
        raise HTTPException(409, f"O estado {documento.status.value} não permite esta operação.")
    anterior = documento.status
    setattr(documento, campo, dados.reason.strip())
    documento.status = destino
    db.add(DocumentTransitionHistory(
        document_id=documento.id, from_status=anterior, to_status=destino,
        changed_by_user_id=usuario.id, comments=dados.reason.strip(),
    ))
    auditar(db, usuario, "document", documento.id, acao, dados.reason.strip())
    db.commit()
    db.refresh(documento)
    return documento


@router.post("/{documento_id}/revoke", response_model=GEDDocumentResponse)
def revogar_documento(
    documento_id: str,
    dados: DocumentDispositionRequest,
    db: Session = Depends(get_db),
    usuario: User = Depends(role_checker(["admin_global", "admin_instituicao"])),
):
    return _encerrar_documento(
        documento_id, dados, db, usuario, GEDDocumentStatus.REVOGADO,
        "revocation_reason", "revogar",
        (GEDDocumentStatus.VALIDO, GEDDocumentStatus.ASSINADO, GEDDocumentStatus.ARQUIVADO),
    )


@router.post("/{documento_id}/annul", response_model=GEDDocumentResponse)
def anular_documento(
    documento_id: str,
    dados: DocumentDispositionRequest,
    db: Session = Depends(get_db),
    usuario: User = Depends(role_checker(["admin_global", "admin_instituicao"])),
):
    return _encerrar_documento(
        documento_id, dados, db, usuario, GEDDocumentStatus.ANULADO,
        "annulment_reason", "anular",
        tuple(status for status in GEDDocumentStatus if status not in (
            GEDDocumentStatus.SUSPENSO, GEDDocumentStatus.REVOGADO, GEDDocumentStatus.ANULADO,
        )),
    )


@router.post("/{documento_id}/second-copy", response_model=GEDDocumentResponse)
def emitir_segunda_via(
    documento_id: str,
    dados: SecondCopyRequest,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_active_user),
):
    original = obter_documento(db, usuario, documento_id, "segunda_via")
    exigir_permissao(db, usuario, original.category_id, "segunda_via")
    if original.status not in (
        GEDDocumentStatus.VALIDO,
        GEDDocumentStatus.ASSINADO,
        GEDDocumentStatus.ARQUIVADO,
    ):
        raise HTTPException(409, "Somente documentos válidos, assinados ou arquivados podem gerar segunda via.")
    if not dados.reason.strip():
        raise HTTPException(422, "Informe o motivo da emissão da segunda via.")
    caminho = caminho_seguro(original)
    conteudo = caminho.read_bytes()
    nome = f"{uuid4()}{caminho.suffix.lower()}"
    novo_caminho = save_file(nome, conteudo, db=db)
    nova_via = GEDDocument(
        title=dados.title.strip() if dados.title and dados.title.strip() else f"Segunda via - {original.title}",
        file_path=novo_caminho,
        category_id=original.category_id,
        student_id=original.student_id,
        institution_id=original.institution_id,
        campus_id=original.campus_id,
        modality=original.modality,
        uploaded_by_user_id=usuario.id,
        document_purpose="official",
        is_official=True,
        status=GEDDocumentStatus.PENDENTE_VALIDACAO,
        second_copy_of_id=original.id,
    )
    db.add(nova_via)
    db.flush()
    indices_originais = db.query(GEDDocumentIndexValue).filter(
        GEDDocumentIndexValue.document_id == original.id
    ).all()
    for indice in indices_originais:
        db.add(GEDDocumentIndexValue(
            document_id=nova_via.id, index_id=indice.index_id, value=indice.value
        ))
    db.add(DocumentTransitionHistory(
        document_id=nova_via.id, from_status=None,
        to_status=GEDDocumentStatus.PENDENTE_VALIDACAO,
        changed_by_user_id=usuario.id,
        comments=f"Segunda via vinculada a {original.id}: {dados.reason.strip()}",
    ))
    auditar(
        db, usuario, "document", nova_via.id, "segunda_via_emitida",
        f"Documento original: {original.id}. Motivo: {dados.reason.strip()}",
    )
    db.commit()
    db.refresh(nova_via)
    return nova_via


@router.post("/{documento_id}/legal-hold", response_model=GEDDocumentResponse)
def colocar_legal_hold(
    documento_id: str,
    dados: LegalHoldRequest,
    db: Session = Depends(get_db),
    usuario: User = Depends(role_checker(["admin_global", "admin_instituicao"])),
):
    documento = db.query(GEDDocument).filter_by(id=documento_id).with_for_update().first()
    if documento is None:
        raise HTTPException(404, "Documento não encontrado.")
    verify_document_ownership(usuario, documento)
    if not dados.reason.strip() or not dados.authorization_reference.strip():
        raise HTTPException(422, "Motivo e referência da autorização são obrigatórios.")
    ativo = db.query(DocumentLegalHold).filter(
        DocumentLegalHold.document_id == documento.id,
        DocumentLegalHold.released_at.is_(None),
    ).first()
    if ativo:
        raise HTTPException(409, "O documento já possui legal hold ativo.")
    hold = DocumentLegalHold(
        document_id=documento.id,
        reason=dados.reason.strip(),
        authorization_reference=dados.authorization_reference.strip(),
        placed_by_user_id=usuario.id,
    )
    db.add(hold)
    auditar(
        db, usuario, "document", documento.id, "legal_hold_aplicado",
        f"{dados.reason.strip()} ({dados.authorization_reference.strip()})",
    )
    db.commit()
    db.refresh(documento)
    return documento


@router.post("/{documento_id}/legal-hold/release", response_model=GEDDocumentResponse)
def liberar_legal_hold(
    documento_id: str,
    dados: LegalHoldRequest,
    db: Session = Depends(get_db),
    usuario: User = Depends(role_checker(["admin_global"])),
):
    documento = db.query(GEDDocument).filter_by(id=documento_id).with_for_update().first()
    if documento is None:
        raise HTTPException(404, "Documento não encontrado.")
    hold = db.query(DocumentLegalHold).filter(
        DocumentLegalHold.document_id == documento.id,
        DocumentLegalHold.released_at.is_(None),
    ).first()
    if hold is None:
        raise HTTPException(409, "O documento não possui legal hold ativo.")
    if not dados.reason.strip() or not dados.authorization_reference.strip():
        raise HTTPException(422, "Motivo e referência da autorização são obrigatórios.")
    hold.released_by_user_id = usuario.id
    hold.released_at = utc_now()
    hold.release_reason = f"{dados.reason.strip()} ({dados.authorization_reference.strip()})"
    auditar(db, usuario, "document", documento.id, "legal_hold_liberado", hold.release_reason)
    db.commit()
    db.refresh(documento)
    return documento


def validar_exclusao(db, documento):
    tipo = db.get(DocumentType, documento.category_id)
    if tipo is None or tipo.legal_hold:
        raise HTTPException(409, "Exclusão bloqueada: política ausente ou preservação legal ativa.")
    if db.query(DocumentLegalHold).filter(
        DocumentLegalHold.document_id == documento.id,
        DocumentLegalHold.released_at.is_(None),
    ).first():
        raise HTTPException(409, "Exclusão bloqueada: legal hold ativo.")
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
