from app.curriculo_generator import generate_curriculo_xml
from app.schemas_curriculo import (
    CategoriaItem,
    CriterioIntegralizacaoRotulo,
    CargasHorariasCriterio,
    DadosCurso,
    EtiquetaItem,
    IesEmissora,
    Model,
    UnidadeCurricularItem,
)


def test_generate_curriculo_xml():
    payload = Model.model_construct(
        codigoCurriculo="CUR-001",
        dataCurriculo="2026-01-01",
        minutosRelogioDaHoraAula="60",
        dadosCurso=DadosCurso.model_construct(nomeCurso="Direito"),
        iesEmissora=IesEmissora.model_construct(Nome="IES Teste"),
        etiqueta=[EtiquetaItem.model_construct(codigo="E1", nome="Obrigatória")],
        area=[],
        unidadeCurricular=[
            UnidadeCurricularItem.model_construct(
                tipo="disciplina", codigo="DIR-001", nome="Introdução ao Direito"
            )
        ],
        categoria=[
            CategoriaItem.model_construct(
                codigo="AC", nome="Atividades", atividades=[]
            )
        ],
        criterioIntegralizacaoRotulos=[
            CriterioIntegralizacaoRotulo.model_construct(
                codigo="CH",
                unidadeCurricular="Disciplinas",
                cargasHorariasCriterio=CargasHorariasCriterio.model_construct(
                    cargaHorariaMinima="100", cargaHorariaMaxima="200"
                ),
            )
        ],
    )

    xml_output = generate_curriculo_xml(payload)

    assert "<CurriculoEscolar" in xml_output
    assert '<infCurriculoEscolar versao="1.05"' in xml_output
    assert "<DadosCurso>" in xml_output
    assert "<IesEmissora>" in xml_output
    assert "<NomeCurso>Direito</NomeCurso>" in xml_output
    assert "<infEtiquetas>" in xml_output
    assert "<Etiqueta>" in xml_output
    assert "<infEstruturaCurricular>" in xml_output
    assert "<UnidadeCurricular>" in xml_output
    assert "<infCriteriosIntegralizacao>" in xml_output
    assert "<CriterioIntegralizacaoRotulos>" in xml_output
    assert "<Categoria>" in xml_output
