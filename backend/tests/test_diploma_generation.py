from app.diploma_generator import generate_academica_xml, generate_diploma_xml
from app.schemas_diploma import (
    DadosDiploma,
    DadosPrivadosDiplomado,
    Diplomado,
    FiliacaoItem,
    Model,
    TermoResponsabilidade,
)


def create_payload():
    return Model.model_construct(
        id="DIP-001",
        dadosDiploma=DadosDiploma.model_construct(
            diplomado=Diplomado.model_construct(nome="Maria Silva"),
        ),
        dadosRegistro=None,
        dadosPrivadosDiplomado=DadosPrivadosDiplomado.model_construct(
            filiacao=[FiliacaoItem.model_construct(nome="Responsável")],
            historicoEscolar=None,
        ),
        termoResponsabilidade=TermoResponsabilidade.model_construct(
            Nome="Reitor", CPF="12345678900", Cargo="Reitor"
        ),
    )


def test_generate_diploma_xml():
    xml_output = generate_diploma_xml(create_payload())

    assert "<Diploma" in xml_output
    assert '<infDiploma versao="1.05"' in xml_output
    assert "<Diplomado>" in xml_output
    assert "<Nome>Maria Silva</Nome>" in xml_output
    assert "<DadosPrivadosDiplomado>" not in xml_output


def test_generate_academica_xml():
    xml_output = generate_academica_xml(create_payload())

    assert "<DocumentacaoAcademicaRegistro" in xml_output
    assert '<RegistroReq versao="1.05"' in xml_output
    assert "<DadosPrivadosDiplomado>" in xml_output
    assert "<TermoResponsabilidadeEmissora>" in xml_output
