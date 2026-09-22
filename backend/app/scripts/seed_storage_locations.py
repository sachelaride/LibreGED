"""Create the requested local storage locations.

Run from ``backend``:
    ..\\.venv\\Scripts\\python.exe -m app.scripts.seed_storage_locations

The operation is idempotent: existing database rules and directories are
reused, while the ignored source numbers are never created.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.database import SessionLocal
from app import models_ged  # noqa: F401 - registers GED relationships
from app import models_workflow  # noqa: F401 - registers workflow relationships
from app.models_ged import GEDDocumentIndexValue
from app.models_ged_config import DocumentType, DocumentTypeIndex, DocumentTypeVersion, GedIndex
from app.models_storage import StorageRule


IGNORED_NUMBERS = {
    2, 3, 6, 7, 8, 10, 29, 32, 35, 37, 38, 40, 41, 42, 43, 44,
    46, 47, 49, 53, 54, 55, 56, 57, 59,
}

LOCATION_NAMES = {
    1: "APROVEITAMENTO DE ESTUDOS",
    4: "ATIVIDADES COMPLEMENTARES",
    5: "ATO DE DESIGNACAO",
    9: "CONTROLE DE NOTAS",
    11: "CURRÍCULO ESCOLAR",
    12: "DADOS DE EMISSÃO PARA CURRÍCULO ESCOLAR",
    13: "DADOS DE EMISSÃO PARA HISTÓRICO ESCOLAR",
    14: "DADOS IES REGISTRADORA",
    15: "DADOS PARA EMISSÃO DE DIPLOMA",
    16: "DIPLOMA DO ALUNO",
    17: "DIPLOMAS",
    18: "DOCUMENTAÇÃO INDÍGENA",
    19: "DOCUMENTOS ACADÊMICOS",
    20: "DOCUMENTOS ACADÊMICOS SISTEMA",
    21: "DOCUMENTOS ESTAGIÁRIOS MENOR APRENDIZ",
    22: "DOCUMENTOS FIES",
    23: "DOCUMENTOS JURÍDICOS",
    24: "DOCUMENTOS JURÍDICOS PROFESSOR",
    25: "DOCUMENTOS PESSOAIS",
    26: "DOCUMENTOS PESSOAIS PROFESSOR",
    27: "DOCUMENTOS PROUNI",
    28: "DOCUMENTOS VESTIBULAR",
    30: "ESTAGIOS",
    31: "EXAMES",
    33: "FORMULARIOS",
    34: "HISTÓRICO ESCOLAR DO ALUNO",
    36: "LISTA DE DIPLOMAS ANULADOS",
    39: "PLANO DE ENSINO",
    52: "TCC",
    60: "XML DIPLOMADO",
    61: "XML DO CURRÍCULO ESCOLAR",
    62: "XML HISTORICO ESCOLAR",
    63: "XML INSTITUCIONAL",
}

SYSTEM_INDEXES = [
    ("Ano", "Número"),
    ("Ano/Semetre", "Caractere"),
    ("Anotação Anulação", "Caractere"),
    ("CNPJ Mantenedora", "Caractere"),
    ("Codigo Ato", "Caractere"),
    ("Codigo MEC", "Caractere"),
    ("Codigo Siga", "Lista"),
    ("CPF", "Caractere"),
    ("Data Curriculum", "Data"),
    ("Data Colação de Grau", "Data"),
    ("Data da Conclusao do Curso", "Data"),
    ("Data Expedição do Diploma", "Data"),
    ("Data da Portaria", "Data"),
    ("Data Portaria Autorização", "Data"),
    ("Nome", "Caractere"),
    ("Data Inicio", "Data"),
    ("Data Final", "Data"),
    ("RGM", "Caractere"),
    ("Matricula", "Caractere"),
    ("ASSINATURA_TDadosDiploma", "Caractere"),
    ("ASSINATURA_TDadosDiploma_PF", "Caractere"),
    ("ASSINATURA_TDadosDiploma_PJ", "Caractere"),
    ("ASSINATURA_TDadosDiplomaNSF", "Caractere"),
    ("ASSINATURA_TDadosHistorico_PF", "Caractere"),
    ("ASSINATURA_TDadosRegistro", "Caractere"),
    ("ASSINATURA_TDadosRegistroNSF", "Caractere"),
    ("ASSINATURA_TDiploma", "Caractere"),
    ("ASSINATURA_TDocumentacaoAcademicaRegistro", "Caractere"),
]

IMAGE_INDEXES = [
    "CEDULA DE IDENTIDADE", "CIDADE - UF", "CNPJ MANTENEDORA",
    "CÓDIGO DE VALIDAÇÃO", "CODIGO DO ATO", "CÓDIGO MEC", "CODIGO SIGA",
    "CPF", "CPF - MATRICULA - ATO DE DESIGNACAO OU DELEGACAO",
    "CPF DO COLABORADOR", "CURSO", "CURSO E CODIGO E-MEC DO CURSO", "DATA",
    "DATA ANULAÇÃO", "DATA CURRÍCULO", "DATA DA COLACAO DE GRAU",
    "DATA DA CONCLUSAO DO CURSO", "DATA DA EXPEDICAO DO DIPLOMA",
    "DATA DA PORTARIA", "DATA DA PORTARIA DE AUTORIZACAO",
    "DATA DA PUBLICACAO DA PORTARIA NO DOU", "DATA DE EXPEDICAO",
    "DATA DE INGRESSO", "DATA DE INICIO DO CURSO", "DATA DE NASCIMENTO",
    "DATA DE PARTICIPACAO DO CONCLUINTE NO ENADE", "DATA DO REGISTRO",
    "DATA FIM", "DATA FINAL", "DATA INICIAL", "DATA INICIO",
    "DATA MÁXIMA PRÓXIMA ATUALIZAÇÃO", "DEPARTAMENTO", "DIRIGENTE",
    "DISCIPLINA", "DISPENSA", "EXTENSÃO", "FORMA DE INGRESSO",
    "FORMATO DO DOCUMENTO", "GRAU CONFERIDO", "HABILITACAO E CODIGO E-MEC",
    "ID DADOS EMISSÃO DIPLOMA", "IES", "INSTITUICAO",
    "INSTITUICAO E CODIGO E-MEC DA IES", "LOCAL E DATA", "MANTENEDORA",
    "MATRICULA", "MATRICULA - ATO DE DESIGNACAO OU DELEGACAO", "MÊS",
    "MODALIDADE", "MOTIVO ANULAÇÃO", "MOTIVO DO CANCELAMENTO",
    "NACIONALIDADE", "NOME", "NOME DA AUTORIDADE MAXIMA DA IES",
    "NOME LISTA ANULAÇÃO",
    "NOVAS HABILITACOES - SEGUNDA LICENCIATURA - APOSTILAMENTOS - AVERBACOES",
    "NUMERO DA FOLHA",
    "NUMERO DA PORTARIA CONFORME ART 6 DA PORTARIA N 1095 DE 2018",
    "NÚMERO DE SEQUÊNCIA", "NUMERO DE SERIE", "NUMERO DO LIVRO",
    "NUMERO DO PROCESSO DE RECONHECIMENTO OU RENOVACAO DE RECONHECIMENTO",
    "NUMERO DO REGISTRO", "OBSERVACOES", "ORGAO EMISSOR - UF",
    "PENDENTE ASSINATURA", "PORTARIA DE AUTORIZACAO",
    "PORTARIA DE RECONHECIMENTO", "PORTARIA DE RENOVACAO DE RECONHECIMENTO",
    "PROCESSO", "PROFESSOR", "PRONTUARIO", "QUANTIDADE DE DIPLOMAS",
    "RESPONSAVEL PELA DIGITALIZACAO", "RESPONSAVEL PELO REGISTRO", "RGCFU",
    "RGM", "SETOR-FISIO", "SITUAÇÃO", "STATUS ASSINATURA CURRÍCULO",
    "STATUS ASSINATURA HISTÓRICO", "STATUS DO CURRÍCULO", "STATUS DO DIPLOMA",
    "STATUS DO HISTÓRICO", "STATUS DOCUMENTO", "TEMPLATE REPRESENTAÇÃO VISUAL",
    "TIPO ATA", "TIPO DE DOCUMENTAÇÃO ASSOCIADA", "TIPO FISCALIZAÇÃO",
    "TIPO HISTÓRICO", "TITULAÇÃO", "TURMA", "TURNO", "UNIDADE",
    "UNIDADE - CAMPUS",
]

SKIPPED_INDEX_TERMS = ("ODONTO", "MURILO", "ASSUNTOS")

LIST_INDEX_OPTIONS = {
    "CODIGO SIGA": ["GRADUACAO 125.43", "POS LATO 144.43", "POS STRICTO 134.43", "ENSINO MEDIO 445.43"],
    "MODALIDADE": ["PRESENCIAL", "EAD"],
    "MOTIVO ANULAÇÃO": ["ERRO DE FATO", "ERRO DE DIREITO", "DECISÃO JUDICIAL", "REEMISSÃO PARA COMPLEMENTAÇÃO", "REEMISSÃO PARA INCLUSÃO DE DADOS", "REEMISSÃO PARA ANOTAÇÃO"],
    "PENDENTE ASSINATURA": ["PRIMEIRA ASSINATURA", "SEGUNDA ASSINATURA", "TERCEIRA ASSINATURA", "QUARTA ASSINATURA"],
    "SITUAÇÃO": ["ATIVO", "INATIVO"],
    "STATUS ASSINATURA CURRÍCULO": ["AGUARDANDO CNPJ", "AGUARDANDO CPF", "CONCLUÍDA"],
    "STATUS DO CURRÍCULO": ["ATIVO", "INVÁLIDO"],
    "STATUS DO DIPLOMA": ["ATIVO", "ANULADO"],
    "STATUS DO HISTÓRICO": ["ATIVO", "INVÁLIDO"],
    "TIPO ATA": ["ATA AVALIAÇÃO", "ATA MATRÍCULA"],
    "TIPO DE DOCUMENTAÇÃO ASSOCIADA": ["001 - TERMO DE RESPONSABILIDADE", "002 - DOCUMENTO DE IDENTIDADE", "003 - PROVA DE CONCLUSÃO", "004 - HISTÓRICO ESCOLAR", "005 - PROVA DE COLAÇÃO", "006 - COMPROVAÇÃO DE ESCOLARIDADE", "007 - CERTIDÃO DE NASCIMENTO", "008 - CPF", "009 - TÍTULO DE ELEITOR", "010 - ATO DE NATURALIZAÇÃO", "011 - OUTROS", "012 - ATO DE DESIGNAÇÃO", "R01 - BEREVISTA", "R02 - COMPROVANTE RESIDÊNCIA", "R03 - DIPLOMA GRADUAÇÃO", "R04 - HISTÓRICO DA GRADUAÇÃO", "R05 - HISTÓRICO PARCIAL"],
    "TIPO FISCALIZAÇÃO": ["IES REGISTRADORA", "IES EMISSORA"],
    "TIPO HISTÓRICO": ["FINAL", "PARCIAL", "SECOND COPY"],
    "TITULAÇÃO": ["GRADUAÇÃO", "ESPECIALIZAÇÃO", "MESTRADO", "DOUTORADO"],
    "TURMA": ["A", "B", "C", "D", "E", "F", "G", "N", "X"],
}


def seed(root: Path) -> int:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    created = 0
    document_types_created = 0
    try:
        system_index_names = [name.upper() for name, _ in SYSTEM_INDEXES]
        image_index_names = [name.upper() for name in IMAGE_INDEXES]
        all_index_names = system_index_names + image_index_names
        existing = {
            index.name.upper(): index for index in db.query(GedIndex).all()
        }
        system_indices = []
        for name in all_index_names:
            if any(term in name for term in SKIPPED_INDEX_TERMS):
                continue
            index = existing.get(name)
            index_type = {
                index_name.upper(): index_type
                for index_name, index_type in SYSTEM_INDEXES
            }.get(name, "Lista" if name in LIST_INDEX_OPTIONS else "Caractere")
            options = LIST_INDEX_OPTIONS.get(name, [])
            if index is None:
                index = GedIndex(
                    name=name,
                    type=index_type,
                    options=options,
                    mask=None,
                    auto_increment=False,
                    is_active=True,
                )
                db.add(index)
                db.flush()
                existing[name] = index
            else:
                index.name = name
                index.type = index_type
                index.options = options
            system_indices.append(index)

        for index in list(existing.values()):
            if not any(term in index.name.upper() for term in SKIPPED_INDEX_TERMS):
                continue
            has_link = db.query(DocumentTypeIndex).filter_by(index_id=index.id).first()
            has_value = db.query(GEDDocumentIndexValue).filter_by(index_id=index.id).first()
            if not has_link and not has_value:
                db.delete(index)

        for number, name in sorted(LOCATION_NAMES.items()):
            if number in IGNORED_NUMBERS:
                continue

            path = root / name
            path.mkdir(parents=True, exist_ok=True)
            rule_id = f"local-location-{number:02d}"
            rule = db.get(StorageRule, rule_id)
            if rule is None:
                rule = StorageRule(
                    id=rule_id,
                    name=name,
                    storage_type="Local",
                    base_path=str(path),
                    max_files_per_folder=10000,
                    max_gb_per_folder=100.0,
                    is_active=True,
                )
                db.add(rule)
                created += 1
            elif rule.base_path != str(path):
                rule.base_path = str(path)
            db.flush()

            document_type_id = f"local-document-type-{number:02d}"
            document_type = db.get(DocumentType, document_type_id)
            if document_type is None:
                document_type = db.query(DocumentType).filter(
                    DocumentType.name == name
                ).first()

            if document_type is None:
                document_type = DocumentType(
                    id=document_type_id,
                    name=name,
                    is_active=True,
                    group_id="LOCAL",
                    retention_years=5,
                    legal_hold=False,
                    access_policy={},
                    signature_rule={},
                    active_version=1,
                    storage_area_id=rule.id,
                    storage_partition_id=None,
                )
                db.add(document_type)
                db.flush()
                db.add(DocumentTypeVersion(
                    id=f"{document_type_id}-v1",
                    document_type_id=document_type.id,
                    version=1,
                    status="ACTIVE",
                    name=document_type.name,
                    group_id=document_type.group_id,
                    retention_years=document_type.retention_years,
                    legal_hold=document_type.legal_hold,
                    access_policy={},
                    signature_rule={},
                    created_by=None,
                ))
                document_types_created += 1
            else:
                document_type.storage_area_id = rule.id
                document_type.storage_partition_id = None
            for index in system_indices:
                linked = db.query(DocumentTypeIndex).filter_by(
                    document_type_id=document_type.id,
                    index_id=index.id,
                ).first()
                if not linked:
                    db.add(DocumentTypeIndex(
                        document_type_id=document_type.id,
                        index_id=index.id,
                        is_required=False,
                        is_unique=False,
                    ))
        db.commit()
    finally:
        db.close()
    return created, document_types_created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(r"C:\Users\SACHELARIDE\Desktop\LibreGED\teste armazenamento"),
        help="Diretório raiz das pastas locais.",
    )
    args = parser.parse_args()
    created, document_types_created = seed(args.root)
    print(
        f"{len(LOCATION_NAMES)} locais configurados; "
        f"{created} regras novas; "
        f"{document_types_created} tipos documentais novos vinculados; "
        f"{len(SYSTEM_INDEXES)} índices padrão criados."
    )


if __name__ == "__main__":
    main()
