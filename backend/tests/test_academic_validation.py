from app.academic_validator import ValidationRequest, validate_documents
from app.schemas_curriculo import (
    CargasHorariasCriterio,
    CriterioIntegralizacaoRotulo,
    DadosCurso as CurriculoDadosCurso,
    Model as CurriculoPayload,
)
from app.schemas_diploma import (
    DadosDiploma,
    DadosCurso as DiplomaDadosCurso,
    Diplomado,
    Model as DiplomaPayload,
)
from app.schemas_historico import (
    Aluno,
    CargaHorariaCursoIntegralizada,
    DadosCurso as HistoricoDadosCurso,
    DocumentoHistoricoEscolarFinal,
    HistoricoEscolar,
    Model as HistoricoPayload,
)


def create_payloads():
    diploma = DiplomaPayload.model_construct(
        id="DIP-001",
        dadosDiploma=DadosDiploma.model_construct(
            diplomado=Diplomado.model_construct(cpf="12345678900"),
            dadosCurso=DiplomaDadosCurso.model_construct(codigoCursoEMEC="1001"),
        ),
    )
    historico = HistoricoPayload.model_construct(
        id="HIST-001",
        documentoHistoricoEscolarFinal=DocumentoHistoricoEscolarFinal.model_construct(
            aluno=Aluno.model_construct(cpf="00000000000"),
            dadosCurso=HistoricoDadosCurso.model_construct(codigoCursoEMEC="9999"),
            historicoEscolar=HistoricoEscolar.model_construct(
                cargaHorariaCursoIntegralizada=CargaHorariaCursoIntegralizada.model_construct(
                    horaRelogio="100"
                )
            ),
        ),
    )
    curriculo = CurriculoPayload.model_construct(
        dadosCurso=CurriculoDadosCurso.model_construct(codigoCursoEMEC="9999"),
        criterioIntegralizacaoRotulos=[
            CriterioIntegralizacaoRotulo.model_construct(
                cargasHorariasCriterio=CargasHorariasCriterio.model_construct(
                    cargaHorariaMinima="200"
                )
            )
        ],
    )
    return diploma, historico, curriculo


def test_academic_validation_reports_inconsistencies():
    diploma, historico, curriculo = create_payloads()
    errors = validate_documents(ValidationRequest(
        diploma=diploma, historico=historico, curriculo=curriculo
    ))

    assert any("CPF" in error for error in errors)
    assert any("Curso e-MEC" in error for error in errors)
    assert any("Carga horária" in error for error in errors)


def test_academic_validation_accepts_consistent_documents():
    diploma, historico, curriculo = create_payloads()
    historico.documentoHistoricoEscolarFinal.aluno.cpf = "12345678900"
    historico.documentoHistoricoEscolarFinal.dadosCurso.codigoCursoEMEC = "1001"
    curriculo.dadosCurso.codigoCursoEMEC = "1001"
    historico.documentoHistoricoEscolarFinal.historicoEscolar.cargaHorariaCursoIntegralizada.horaRelogio = "999"

    errors = validate_documents(ValidationRequest(
        diploma=diploma, historico=historico, curriculo=curriculo
    ))

    assert errors == []
