import signxml
from signxml import XMLSigner, XMLVerifier
from lxml import etree
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization
from pyhanko.sign import signers
from pyhanko.sign.timestamps import HTTPTimeStamper
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
import hashlib

def get_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_cert_info_from_p12(p12_path: str, password: str):
    with open(p12_path, "rb") as f:
        p12_data = f.read()
    
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        p12_data, 
        password.encode() if password else None
    )
    
    subject = certificate.subject.rfc4514_string()
    issuer = certificate.issuer.rfc4514_string()
    
    return subject, issuer

def load_p12_certificate(p12_path: str, password: str):
    with open(p12_path, "rb") as f:
        p12_data = f.read()

    private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
        p12_data, 
        password.encode() if password else None
    )
    
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
    key_pem, cert_pem = load_p12_certificate(p12_path, password)

    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_string.encode('utf-8'), parser)
    
    signer = XMLSigner(method=signxml.methods.enveloped,
                       signature_algorithm="rsa-sha256",
                       digest_algorithm="sha256",
                       c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#")
    
    signed_root = signer.sign(root, key=key_pem, cert=cert_pem)
    return etree.tostring(signed_root, encoding="utf-8", xml_declaration=True).decode("utf-8")

def sign_pdf_document(pdf_path: str, p12_path: str, password: str, output_path: str):
    with open(p12_path, 'rb') as f:
        p12_data = f.read()
    
    signer = signers.SimpleSigner.load_pkcs12(p12_data=p12_data, key_passphrase=password.encode())
    timestamper = HTTPTimeStamper('https://freetsa.org/tsr')
    
    with open(pdf_path, 'rb') as doc:
        w = IncrementalPdfFileWriter(doc)
        with open(output_path, 'wb') as out:
            signers.sign_pdf(
                w, signers.PdfSignatureMetadata(field_name='Assinatura_ICP_Brasil'),
                signer=signer,
                timestamper=timestamper,
                out=out
            )
