"""Contrato versionado dos manifestos de ingestão por pasta monitorada."""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


TextoObrigatorio = Annotated[str, Field(strict=True, min_length=1)]


class ManifestoIngestao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: Annotated[int, Field(strict=True, ge=1, le=1)]
    ingestion_id: UUID
    correlation_id: TextoObrigatorio
    document_id: UUID
    institution_id: UUID
    file_name: TextoObrigatorio
    content_type: Literal["application/pdf"]
    sha256: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
    document_type: TextoObrigatorio
    source_system: TextoObrigatorio
    source_event: TextoObrigatorio | None = None
    source_user: TextoObrigatorio | None = None
    created_at: AwareDatetime
    environment: Literal["development", "test", "homologation", "production"]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("correlation_id", "document_type", "source_system", "source_event", "source_user")
    @classmethod
    def validar_texto(cls, valor: str | None) -> str | None:
        if valor is not None and not valor.strip():
            raise ValueError("O campo não pode conter apenas espaços.")
        return valor

    @field_validator("file_name")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        if any(caractere in valor for caractere in '/\\:\x00') or not valor.endswith(".pdf"):
            raise ValueError("Informe apenas o nome do arquivo com extensão .pdf.")
        return valor


def validar_manifesto(dados: object, nome_pdf: str) -> ManifestoIngestao:
    """Recusa contratos desconhecidos e nomes divergentes do par recebido."""
    manifesto = ManifestoIngestao.model_validate(dados)
    if manifesto.file_name != nome_pdf:
        raise ValueError("O nome do PDF difere do informado no manifesto.")
    return manifesto
