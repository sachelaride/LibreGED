import xml.etree.ElementTree as ET
from .schemas_curriculo import Model as CurriculoPayload

def dict_to_xml(data, root=None):
    if root is None:
        root = ET.Element("root")
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "cNPJ":
                tag_name = "CNPJ"
            elif key == "codigoMEC":
                tag_name = "CodigoMEC"
            elif key == "codigoCursoEMEC":
                tag_name = "CodigoCursoEMEC"
            elif key == "uf":
                tag_name = "UF"
            elif key == "cep":
                tag_name = "CEP"
            elif key == "numeroDOU":
                tag_name = "NumeroDOU"
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

def generate_curriculo_xml(payload: CurriculoPayload) -> str:
    """Gera o XML do Currículo Escolar com a formatação exigida pelo MEC."""
    root = ET.Element("CurriculoEscolar", {
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        "xmlns": "http://portal.mec.gov.br/diplomadigital/arquivos-em-xsd"
    })
    
    inf = ET.SubElement(root, "infCurriculoEscolar", {"versao": "1.05"})
    
    ET.SubElement(inf, "CodigoCurriculo").text = str(payload.codigoCurriculo)
    ET.SubElement(inf, "DataCurriculo").text = str(payload.dataCurriculo)
    ET.SubElement(inf, "MinutosRelogioDaHoraAula").text = str(payload.minutosRelogioDaHoraAula)
    
    dict_to_xml(payload.dadosCurso.model_dump(exclude_none=True), ET.SubElement(inf, "DadosCurso"))
    dict_to_xml(payload.iesEmissora.model_dump(exclude_none=True), ET.SubElement(inf, "IesEmissora"))
    
    inf_etiquetas = ET.SubElement(inf, "infEtiquetas")
    if payload.etiqueta:
        for etiq in payload.etiqueta:
            dict_to_xml(etiq.model_dump(exclude_none=True), ET.SubElement(inf_etiquetas, "Etiqueta"))
            
    inf_areas = ET.SubElement(inf, "infAreas")
    if payload.area:
        for area in payload.area:
            val = area.model_dump(exclude_none=True) if hasattr(area, 'model_dump') else area
            dict_to_xml(val, ET.SubElement(inf_areas, "Area"))
            
    inf_estrutura = ET.SubElement(inf, "infEstruturaCurricular")
    if payload.unidadeCurricular:
        for uni in payload.unidadeCurricular:
            dict_to_xml(uni.model_dump(exclude_none=True), ET.SubElement(inf_estrutura, "UnidadeCurricular"))
            
    inf_ativ = ET.SubElement(inf, "infEstruturaAtividadesComplementares")
    if payload.categoria:
        for cat in payload.categoria:
            cat_el = ET.SubElement(inf_ativ, "Categoria")
            cat_dict = cat.model_dump(exclude_none=True)
            atividades = cat_dict.pop("atividades", [])
            dict_to_xml(cat_dict, cat_el)
            if atividades:
                atividades_el = ET.SubElement(cat_el, "Atividades")
                for at in atividades:
                    dict_to_xml(at, ET.SubElement(atividades_el, "Atividade"))

    inf_crit = ET.SubElement(inf, "infCriteriosIntegralizacao")
    if payload.criterioIntegralizacaoRotulos:
        for crit in payload.criterioIntegralizacaoRotulos:
            dict_to_xml(crit.model_dump(exclude_none=True), ET.SubElement(inf_crit, "CriterioIntegralizacaoRotulos"))
            
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
