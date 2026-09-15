"""Privilégios por usuário e tipo documental, com bloqueio por padrão."""
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.models_ged_config import (
    DocumentType, UserDocumentType, PermissionGroupMember,
    PermissionGroup, PermissionGroupDocumentType,
)

AcaoDocumental = Literal['consultar', 'cadastrar', 'editar', 'arquivar', 'excluir', 'download', 'assinar', 'iniciar_fluxo', 'executar_fluxo', 'liberar_quarentena', 'editar_indices', 'exportar', 'imprimir', 'comentar']
ACOES = {
    'consultar': 'Visualizar e pesquisar', 'cadastrar': 'Cadastrar documento',
    'editar': 'Editar documento', 'arquivar': 'Arquivar documento',
    'excluir': 'Excluir documento', 'download': 'Baixar arquivo',
    'assinar': 'Assinar documento', 'iniciar_fluxo': 'Iniciar fluxo',
    'executar_fluxo': 'Executar fluxo', 'liberar_quarentena': 'Liberar quarentena',
    'editar_indices': 'Editar índices', 'exportar': 'Exportar documento',
    'imprimir': 'Imprimir', 'comentar': 'Comentar',
}


class VinculoDocumental(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_type_id: str
    permissions: list[AcaoDocumental] = Field(default_factory=list)
    denied_permissions: list[AcaoDocumental] = Field(default_factory=list)


class PermissoesUsuario(BaseModel):
    model_config = ConfigDict(extra='forbid')
    vinculos: list[VinculoDocumental] = Field(default_factory=list, max_length=1000)


def tem_permissao(db, usuario, tipo_id, acao):
    if acao not in ACOES:
        return False
    if usuario.role == 'admin_global':
        return True
    tipo = db.get(DocumentType, tipo_id)
    if tipo is None:
        return False
    if not tipo.is_active and acao not in ('consultar', 'download'):
        return False
    vinculos = db.query(UserDocumentType).filter_by(
        user_id=usuario.id, document_type_id=tipo_id).all()
    if any(acao in (v.denied_permissions or []) for v in vinculos):
        return False
    if any(acao in (v.permissions or []) for v in vinculos):
        return True

    group_ids = [membership.group_id for membership in db.query(PermissionGroupMember).filter_by(user_id=usuario.id).all()]
    inherited_ids = set(group_ids)
    pending = list(group_ids)
    while pending:
        parent_ids = [
            parent_id for parent_id, in db.query(PermissionGroup.parent_group_id).filter(
                PermissionGroup.id.in_(pending),
                PermissionGroup.parent_group_id.is_not(None),
            ).all()
        ]
        pending = [group_id for group_id in parent_ids if group_id not in inherited_ids]
        inherited_ids.update(pending)
    if not inherited_ids:
        return False
    group_links = db.query(PermissionGroupDocumentType).filter(
        PermissionGroupDocumentType.group_id.in_(inherited_ids),
        PermissionGroupDocumentType.document_type_id == tipo_id,
    ).all()
    if any(acao in (link.denied_permissions or []) for link in group_links):
        return False
    return any(acao in (link.permissions or []) for link in group_links)


def exigir_permissao(db, usuario, tipo_id, acao):
    if not tem_permissao(db, usuario, tipo_id, acao):
        raise HTTPException(403, 'Operação não permitida para este tipo documental.')


def exigir_documento(db, usuario, documento, acao):
    if usuario.role != 'admin_global':
        if not usuario.institution_id or documento.institution_id != usuario.institution_id:
            raise HTTPException(403, 'Documento fora da instituição do usuário.')
        if usuario.campus_id:
            if not documento.campus_id:
                raise HTTPException(403, 'Não é possível confirmar o campus deste documento.')
            if documento.campus_id != usuario.campus_id:
                raise HTTPException(403, 'Documento fora do campus do usuário.')
    exigir_permissao(db, usuario, documento.category_id, acao)


def auditar(db, usuario, entidade, identificador, acao, detalhes):
    from app.main import add_audit
    from app.models import User
    with db.no_autoflush:
        autor = db.get(User, usuario.id)
        add_audit(db, entidade, identificador, acao, detalhes, autor.id if autor else None)
