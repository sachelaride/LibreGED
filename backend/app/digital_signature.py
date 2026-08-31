import signxml
from signxml import XMLSigner, XMLVerifier
from lxml import etree
from cryptography.hazmat.primitives.serialization import pkcs12
import os

from cryptography.hazmat.primitives import serialization

def load_p12_certificate(p12_path: str, password: str):
    """
    Carrega o certificado A1 (.p12 ou .pfx).
    Retorna (chave_privada_pem, certificado_pem).
    """
    with open(p12_path, "rb") as f:
        p12_data = f.read()

    # pkcs12.load_key_and_certificates requires bytes password
    private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
        p12_data, 
        password.encode() if password else None
    )
    
    # signxml expects PEM format
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    cert_pem = certificate.public_bytes(
        encoding=serialization.Encoding.PEM
    )
    
    return key_pem, cert_pem

def sign_xml_document(xml_string: str, p12_path: str, password: str) -> str:
    """
    Recebe um XML em string e o assina usando o padrão XMLDSig.
    O hash padrão é SHA-256 (MEC exige padrão ICP-Brasil).
    """
    # 1. Carregar certificado e chave privada
    private_key, certificate = load_p12_certificate(p12_path, password)

    # 2. Parsear XML
    # C14N: Removendo espaços vazios que quebram o hash
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_string.encode('utf-8'), parser)
    
    # 3. Assinar o XML root
    signer = XMLSigner(method=signxml.methods.enveloped,
                       signature_algorithm="rsa-sha256",
                       digest_algorithm="sha256",
                       c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#")
    
    signed_root = signer.sign(root, key=private_key, cert=certificate)

    # 4. Retornar a string XML assinada
    return etree.tostring(signed_root, encoding="utf-8", xml_declaration=True).decode("utf-8")

def verify_xml_signature(signed_xml_string: str) -> bool:
    """
    Verifica se a assinatura do XML é válida matematicamente e se os hashes coincidem.
    Obs: Isso valida a integridade do XML, mas não valida se a cadeia ICP-Brasil é confiável (requer cadeia de TCs).
    """
    root = etree.fromstring(signed_xml_string.encode('utf-8'))
    try:
        XMLVerifier().verify(root)
        return True
    except Exception as e:
        print(f"Erro na verificação da assinatura: {e}")
        return False
