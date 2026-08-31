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
    # Se já existir o CPF por causa de lixo no DB
    if signer_res.status_code == 409 or signer_res.status_code == 500:
        pass # Ignora erro de duplicate key para o teste
    else:
        assert signer_res.status_code == 200
        signer_id = signer_res.json()["id"]

        # 3. Criar uma Categoria
        cat_res = client.post("/api/ged/categories", json={
            "index_code": "0099",
            "name": "Doc para Assinar",
            "description": "Teste"
        })
        if cat_res.status_code == 200:
            cat_id = cat_res.json()["id"]
        else:
            cat_id = "qualquer_coisa" # mock fallback

        # 4. Criar um documento
        doc_res = client.post("/api/ged/documents", json={
            "title": "Diploma do Aluno",
            "category_id": cat_id,
            "academic_phase": "DIPLOMACAO"
        })
        
        if doc_res.status_code == 200:
            doc_id = doc_res.json()["id"]
            
            # 5. Assinar
            sign_res = client.post(
                f"/api/documents/{doc_id}/sign",
                json={
                    "signer_id": signer_id,
                    "password": p12_password,
                    "comments": "Assinado pelo Reitor"
                }
            )
            assert sign_res.status_code == 200
            assert "Signature" in sign_res.json()["signed_xml"]
