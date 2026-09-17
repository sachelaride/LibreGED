import pytest
import os
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
import datetime
from app.main import app
from app.database import SessionLocal
from app.models_ged_config import DocumentType
import uuid

client = TestClient(app)

def generate_test_p12(password: bytes):
    """Gera um certificado self-signed em memória para testar."""
    # Gera chave privada
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Gera certificado
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Test Signer"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=1)
    ).sign(private_key, hashes.SHA256())
    
    # Exporta para p12
    p12_data = pkcs12.serialize_key_and_certificates(
        name=b"test",
        key=private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password)
    )
    return p12_data

def test_xmldsig_flow():
    # 1. Preparar o certificado falso em memória
    p12_password = "teste"
    p12_bytes = generate_test_p12(p12_password.encode())
    
    institution_res = client.post(
        "/api/institutions",
        json={
            "name": "IES Assinatura",
            "cnpj": "61.000.000/0001-00",
            "legal_name": "IES Assinatura Ltda",
        },
    )
    assert institution_res.status_code == 200, institution_res.json()
    institution_id = institution_res.json()["id"]

    db = SessionLocal()
    document_type_id = str(uuid.uuid4())
    db.add(
        DocumentType(
            id=document_type_id,
            name="XML para Assinatura",
            storage_area_id="dummy_area",
            storage_partition_id="dummy_partition",
            is_active=True,
            signature_rule={"signatures": [{"role": "Reitor", "order": 1}]},
        )
    )
    db.commit()
    db.close()

    # 2. Upload do Signatário
    signer_res = client.post(
        "/api/signers",
        data={
            "name": "João Reitor",
            "role": "Reitor",
            "cpf": "11122233344"
        },
        files={"p12_file": ("test.p12", p12_bytes, "application/x-pkcs12")}
    )
    assert signer_res.status_code == 200, signer_res.json()
    signer_id = signer_res.json()["id"]

    # 3. Criar o documento pelo fluxo GED atual.
    doc_res = client.post(
        "/api/documents/upload",
        data={
            "title": "Diploma do Aluno",
            "document_type_id": document_type_id,
            "indices_json": "[]",
        },
        files={"file": ("diploma.xml", b"<Diploma><Aluno>Joao</Aluno></Diploma>", "application/xml")},
    )
    assert doc_res.status_code == 200, doc_res.json()
    doc_id = doc_res.json()["id"]

    # 4. Assinar
    sign_res = client.post(
        f"/api/documents/{doc_id}/sign",
        json={
            "signer_id": signer_id,
            "password": p12_password,
            "comments": "Assinado pelo Reitor",
        },
    )
    assert sign_res.status_code == 200, sign_res.json()
    assert sign_res.json()["type"] == "XMLDSig"
    signatures_res = client.get(f"/api/documents/{doc_id}/signatures")
    assert signatures_res.status_code == 200
    assert signatures_res.json()[0]["status"] == "SUCCESS"
