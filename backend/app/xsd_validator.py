from lxml import etree
import os
from pathlib import Path

# Pasta onde ficam os schemas XSD (oficiais do MEC ou mocks locais)
XSD_DIR = Path(__file__).parent.parent / "schemas_xsd"

def get_xsd_path(schema_name: str) -> str:
    """Retorna o caminho absoluto de um arquivo XSD na pasta de esquemas."""
    return str(XSD_DIR / schema_name)

def validate_xml_against_xsd(xml_string: str, xsd_filename: str) -> tuple[bool, list[str]]:
    """
    Valida um XML (string) contra um arquivo XSD.
    Retorna uma tupla: (bool indicando se é válido, lista de strings com erros se houver).
    """
    xsd_path = get_xsd_path(xsd_filename)
    if not os.path.exists(xsd_path):
        return False, [f"Arquivo XSD não encontrado: {xsd_filename}"]

    try:
        # Load schema
        with open(xsd_path, 'rb') as f:
            schema_root = etree.XML(f.read())
        schema = etree.XMLSchema(schema_root)
        
        # Parse XML
        xml_parser = etree.XMLParser(schema=schema)
        try:
            # tenta fazer o parse já validando contra o schema
            etree.fromstring(xml_string.encode('utf-8'), xml_parser)
            return True, []
        except etree.XMLSyntaxError as e:
            # Coleta os erros de validação do schema caso falhe
            errors = []
            for error in xml_parser.error_log:
                errors.append(f"Linha {error.line}: {error.message}")
            return False, errors
            
    except Exception as e:
        return False, [f"Erro interno de processamento XSD: {str(e)}"]
