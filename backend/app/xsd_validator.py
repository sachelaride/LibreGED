from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import etree


XSD_DIR = Path(__file__).parent.parent / "schemas_xsd"
MEC_V1_05_DIR = XSD_DIR / "mec_v1_05"
# The published v1.05 files use HTTPS for W3C namespace identifiers; parsers require their canonical HTTP URIs.
_MEC_V1_05_NAMESPACE_FIXES = (
    (b"https://www.w3.org/2001/XMLSchema", b"http://www.w3.org/2001/XMLSchema"),
    (b"https://www.w3.org/2000/09/xmldsig#", b"http://www.w3.org/2000/09/xmldsig#"),
)


class _LocalSchemaResolver(etree.Resolver):
    def __init__(self, schema_directory: Path, normalize_mec_namespaces: bool):
        self.schema_directory = schema_directory.resolve()
        self.normalize_mec_namespaces = normalize_mec_namespaces

    def resolve(self, url, pubid, context):
        parsed_url = urlsplit(url)
        if parsed_url.scheme not in ("", "file"):
            return None

        schema_name = unquote(parsed_url.path.rsplit("/", 1)[-1])
        if not schema_name:
            return None
        schema_path = (self.schema_directory / schema_name).resolve()
        if schema_path.parent != self.schema_directory:
            raise OSError("XSD dependencies must remain in the schema directory")

        schema_content = schema_path.read_bytes()
        if self.normalize_mec_namespaces:
            for source, replacement in _MEC_V1_05_NAMESPACE_FIXES:
                schema_content = schema_content.replace(source, replacement)
        return self.resolve_string(
            schema_content,
            context,
            base_url=schema_path.as_uri(),
        )


def get_xsd_path(schema_name: str) -> str:
    schema_path = (XSD_DIR / schema_name).resolve()
    try:
        schema_path.relative_to(XSD_DIR.resolve())
    except ValueError as exc:
        raise ValueError("Schema path must remain inside the XSD directory") from exc
    return str(schema_path)


def validate_xml_against_xsd(xml_string: str, xsd_filename: str) -> tuple[bool, list[str]]:
    try:
        schema_path = Path(get_xsd_path(xsd_filename))
    except ValueError as exc:
        return False, [str(exc)]

    if not schema_path.is_file():
        return False, [f"Arquivo XSD não encontrado: {xsd_filename}"]

    try:
        normalize_mec_namespaces = schema_path.is_relative_to(MEC_V1_05_DIR.resolve())
        schema_content = schema_path.read_bytes()
        if normalize_mec_namespaces:
            for source, replacement in _MEC_V1_05_NAMESPACE_FIXES:
                schema_content = schema_content.replace(source, replacement)

        schema_parser = etree.XMLParser(resolve_entities=False, no_network=True)
        schema_parser.resolvers.add(
            _LocalSchemaResolver(schema_path.parent, normalize_mec_namespaces)
        )
        schema_root = etree.fromstring(
            schema_content,
            schema_parser,
            base_url=schema_path.as_uri(),
        )
        schema = etree.XMLSchema(schema_root)
    except (OSError, etree.XMLSyntaxError, etree.XMLSchemaParseError) as exc:
        return False, [f"Erro ao carregar o schema XSD {xsd_filename}: {exc}"]

    try:
        document_parser = etree.XMLParser(resolve_entities=False, no_network=True)
        document = etree.fromstring(xml_string.encode("utf-8"), document_parser)
    except etree.XMLSyntaxError as exc:
        return False, [f"XML inválido: linha {exc.lineno}: {exc.msg}"]

    if schema.validate(document):
        return True, []

    errors = [
        f"Linha {error.line}: {error.message}"
        for error in schema.error_log
    ]
    return False, errors
