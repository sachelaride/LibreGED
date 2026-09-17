from app.historico_generator import generate_historico_xml
from app.schemas_historico import (
    Aluno,
    DocumentoHistoricoEscolarFinal,
    Model,
)


def test_generate_historico_xml():
    payload = Model.model_construct(
        id="HIST-001",
        documentoHistoricoEscolarFinal=DocumentoHistoricoEscolarFinal.model_construct(
            aluno=Aluno.model_construct(nome="João Silva")
        ),
    )

    xml_output = generate_historico_xml(payload)

    assert "<DocumentoHistoricoEscolarFinal" in xml_output
    assert 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' in xml_output
    assert '<infHistoricoEscolar versao="1.05">' in xml_output
    assert "<Aluno>" in xml_output
    assert "<Nome>João Silva</Nome>" in xml_output
