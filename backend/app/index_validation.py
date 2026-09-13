"""Validação dos valores de índices antes de persistir um documento GED."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from fastapi import HTTPException

from app.models_ged import GEDDocument, GEDDocumentIndexValue
from app.models_ged_config import DocumentTypeIndex, GedIndex


TIPOS_INDICE = {"texto", "caractere", "data", "número", "numero", "booleano", "lista"}


def validar_configuracao_indice(tipo: str, opcoes: list[str], mascara: str | None,
                                autonumeracao: bool) -> None:
    tipo_normalizado = tipo.strip().lower()
    if tipo_normalizado not in TIPOS_INDICE:
        raise HTTPException(422, "Tipo de índice não suportado.")
    if tipo_normalizado == "lista":
        if not opcoes or any(not isinstance(item, str) or not item.strip() for item in opcoes):
            raise HTTPException(422, "Índice do tipo Lista exige opções de texto não vazias.")
        if len(set(opcoes)) != len(opcoes):
            raise HTTPException(422, "As opções da lista não podem ser duplicadas.")
    elif opcoes:
        raise HTTPException(422, "Opções só podem ser usadas em índices do tipo Lista.")
    if mascara:
        try:
            re.compile(mascara)
        except re.error as erro:
            raise HTTPException(422, "A máscara deve ser uma expressão regular válida.") from erro
    if autonumeracao and tipo_normalizado not in {"texto", "caractere", "número", "numero"}:
        raise HTTPException(422, "Autonumeração exige índice textual ou numérico.")


def _normalizar_valor(indice: GedIndex, valor) -> str:
    if isinstance(valor, (dict, list)) or valor is None:
        raise HTTPException(422, f"Valor inválido para o índice {indice.name}.")
    texto = str(valor).strip()
    if not texto:
        raise HTTPException(422, f"O índice {indice.name} não pode ser vazio.")
    tipo = indice.type.strip().lower()
    if tipo == "data":
        try:
            date.fromisoformat(texto)
        except ValueError as erro:
            raise HTTPException(422, f"O índice {indice.name} exige data no formato AAAA-MM-DD.") from erro
    elif tipo in {"número", "numero"}:
        try:
            Decimal(texto.replace(",", "."))
        except InvalidOperation as erro:
            raise HTTPException(422, f"O índice {indice.name} exige um número.") from erro
    elif tipo == "booleano":
        mapa = {"true": "true", "false": "false", "1": "true", "0": "false",
                "sim": "true", "não": "false", "nao": "false"}
        if texto.lower() not in mapa:
            raise HTTPException(422, f"O índice {indice.name} exige Sim/Não.")
        texto = mapa[texto.lower()]
    elif tipo == "lista" and texto not in (indice.options or []):
        raise HTTPException(422, f"Valor fora das opções permitidas para {indice.name}.")
    if indice.mask and re.fullmatch(indice.mask, texto) is None:
        raise HTTPException(422, f"O índice {indice.name} não atende à máscara configurada.")
    return texto


def validar_valores_indices(db, tipo_documental_id: str, instituicao_id: str,
                            valores_recebidos: object) -> list[tuple[GedIndex, str]]:
    if not isinstance(valores_recebidos, list):
        raise HTTPException(422, "indices_json deve ser uma lista.")
    recebidos = {}
    for item in valores_recebidos:
        if not isinstance(item, dict) or set(item) != {"index_id", "value"}:
            raise HTTPException(422, "Cada índice deve conter somente index_id e value.")
        if item["index_id"] in recebidos:
            raise HTTPException(422, "Índice informado mais de uma vez.")
        recebidos[item["index_id"]] = item["value"]

    vinculos = db.query(DocumentTypeIndex).filter_by(
        document_type_id=tipo_documental_id).all()
    permitidos = {v.index_id: v for v in vinculos}
    extras = set(recebidos) - set(permitidos)
    if extras:
        raise HTTPException(422, "Foi informado um índice não vinculado ao tipo documental.")

    resultado = []
    for vinculo in vinculos:
        indice = db.query(GedIndex).filter_by(id=vinculo.index_id).with_for_update().one()
        if not indice.is_active and vinculo.index_id in recebidos:
            raise HTTPException(422, f"O índice {indice.name} está inativo.")
        valor = recebidos.get(vinculo.index_id)
        if indice.auto_increment and (valor is None or str(valor).strip() == ""):
            existentes = db.query(GEDDocumentIndexValue.value).join(
                GEDDocument, GEDDocument.id == GEDDocumentIndexValue.document_id).filter(
                GEDDocument.category_id == tipo_documental_id,
                GEDDocument.institution_id == instituicao_id,
                GEDDocumentIndexValue.index_id == indice.id).all()
            numeros = [int(v[0]) for v in existentes if str(v[0]).isdigit()]
            valor = str(max(numeros, default=0) + 1)
        if valor is None or str(valor).strip() == "":
            if vinculo.is_required:
                raise HTTPException(422, f"O índice {indice.name} é obrigatório.")
            continue
        normalizado = _normalizar_valor(indice, valor)
        if vinculo.is_unique:
            duplicado = db.query(GEDDocumentIndexValue).join(
                GEDDocument, GEDDocument.id == GEDDocumentIndexValue.document_id).filter(
                GEDDocument.category_id == tipo_documental_id,
                GEDDocument.institution_id == instituicao_id,
                GEDDocumentIndexValue.index_id == indice.id,
                GEDDocumentIndexValue.value == normalizado).first()
            if duplicado:
                raise HTTPException(409, f"Já existe documento com o mesmo valor de {indice.name}.")
        resultado.append((indice, normalizado))
    return resultado
