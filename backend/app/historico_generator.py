import xml.etree.ElementTree as ET
from .schemas_historico import Model as HistoricoPayload

def dict_to_xml(data, root=None):
    if root is None:
        root = ET.Element("root")
    
    if isinstance(data, dict):
        for key, value in data.items():
            # Casos especiais de tags do MEC
            if key == "cNPJ":
                tag_name = "CNPJ"
            elif key == "cPF":
                tag_name = "CPF"
            elif key == "codigoMEC":
                tag_name = "CodigoMEC"
            elif key == "rg":
                tag_name = "RG"
            elif key == "cep":
                tag_name = "CEP"
            elif key == "uf":
                tag_name = "UF"
            elif key == "id":
                tag_name = "ID"
            elif key == "codigoCursoEMEC":
                tag_name = "CodigoCursoEMEC"
            else:
                # Capitaliza a primeira letra para bater com o XSD
                tag_name = key[0].upper() + key[1:]
                
            if isinstance(value, list):
                for item in value:
                    child = ET.SubElement(root, tag_name)
                    dict_to_xml(item, child)
            elif isinstance(value, dict):
                child = ET.SubElement(root, tag_name)
                dict_to_xml(value, child)
            elif value is not None:
                child = ET.SubElement(root, tag_name)
                child.text = str(value)
    return root

def generate_historico_xml(payload: HistoricoPayload) -> str:
    """Gera o XML do Histórico Escolar a partir do modelo Pydantic validado."""
    data = payload.documentoHistoricoEscolarFinal.model_dump(exclude_none=True)
    
    # Raiz do documento com os namespaces exigidos pelo MEC
    root = ET.Element("DocumentoHistoricoEscolarFinal", {
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        "xmlns": "http://portal.mec.gov.br/diplomadigital/arquivos-em-xsd"
    })
    
    # Adiciona a versão ao nó principal do histórico
    inf = ET.SubElement(root, "infHistoricoEscolar", {"versao": "1.05"})
    
    # Converte recursivamente os dados
    dict_to_xml(data, inf)
    
    # Retorna o XML como string
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
