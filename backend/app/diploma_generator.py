import xml.etree.ElementTree as ET
from .schemas_diploma import Model as DiplomaPayload

def dict_to_xml(data, root=None):
    if root is None:
        root = ET.Element("root")
    
    if isinstance(data, dict):
        for key, value in data.items():
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
            elif key == "codigoEMEC":
                tag_name = "CodigoEMEC"
            elif key == "enade":
                tag_name = "ENADE"
            else:
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

def generate_diploma_xml(payload: DiplomaPayload) -> str:
    """Gera o XML do Diplomado (Diploma público visual)."""
    data = payload.dadosDiploma.model_dump(exclude_none=True)
    
    root = ET.Element("Diploma", {
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        "xmlns": "http://portal.mec.gov.br/diplomadigital/arquivos-em-xsd"
    })
    
    dip_id = f"Dip{payload.id}"
    inf_id = f"VDip{payload.id}"
    inf = ET.SubElement(root, "infDiploma", {"versao": "1.05", "id": inf_id})
    dados_diploma = ET.SubElement(inf, "DadosDiploma", {"id": dip_id})
    
    dict_to_xml(data, dados_diploma)
    
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

def generate_academica_xml(payload: DiplomaPayload) -> str:
    """Gera o XML Institucional de Documentação Acadêmica para Registro."""
    root = ET.Element("DocumentacaoAcademicaRegistro", {
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        "xmlns": "http://portal.mec.gov.br/diplomadigital/arquivos-em-xsd"
    })
    
    dip_id = f"Dip{payload.id}"
    req_id = f"ReqDip{payload.id}"
    
    req = ET.SubElement(root, "RegistroReq", {"versao": "1.05", "id": req_id})
    
    dados_diploma = ET.SubElement(req, "DadosDiploma", {"id": dip_id})
    dict_to_xml(payload.dadosDiploma.model_dump(exclude_none=True), dados_diploma)
    
    if payload.dadosPrivadosDiplomado:
        priv_dict = payload.dadosPrivadosDiplomado.model_dump(exclude_none=True)
        priv = ET.SubElement(req, "DadosPrivadosDiplomado")
        dict_to_xml(priv_dict, priv)
        
    if getattr(payload, "termoResponsabilidade", None):
        termo = ET.SubElement(req, "TermoResponsabilidadeEmissora")
        dict_to_xml(payload.termoResponsabilidade.model_dump(exclude_none=True), termo)
        
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
