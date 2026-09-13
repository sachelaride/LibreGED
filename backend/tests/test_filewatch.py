import pytest
import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import engine, get_db
from app import models
from app.models import Base
from app.filewatch import DIR_INCOMING, DIR_PROCESSING, DIR_COMPLETED, DIR_QUARANTINE, process_ingestion_file

# Setup testing DB using the shared PostgreSQL test engine
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def preparar_banco(request):
    if request.node.name.startswith(("test_manifesto_exige", "test_manifesto_recusa", "test_manifesto_valido")):
        yield
        return
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    # Create test institution
    inst_id = "11111111-1111-4111-8111-111111111111"
    db.add(models.Institution(id=inst_id, name="FW Inst", cnpj="123", legal_name="FW Inst"))
    db.commit()
    from app.models_ged import DocumentCategory, GEDDocument
    categoria = DocumentCategory(id="categoria-fw", name="Hist?rico")
    db.add(categoria)
    db.flush()
    db.add(GEDDocument(
        id="33333333-3333-4333-8333-333333333333", title="Hist?rico",
        file_path="", category_id=categoria.id, institution_id=inst_id,
    ))
    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def diretorios_temporarios(request, monkeypatch):
    if request.node.name.startswith(("test_manifesto_exige", "test_manifesto_recusa", "test_manifesto_valido")):
        return
    tmp_path = request.getfixturevalue("tmp_path")
    from app import filewatch
    for nome in ["DIR_INCOMING", "DIR_PROCESSING", "DIR_COMPLETED", "DIR_QUARANTINE"]:
        diretorio = tmp_path / nome
        diretorio.mkdir()
        monkeypatch.setattr(filewatch, nome, diretorio)
        monkeypatch.setitem(globals(), nome, diretorio)


def criar_manifesto(nome, resumo):
    return {
        "manifest_version": 1,
        "ingestion_id": "22222222-2222-4222-8222-222222222222",
        "correlation_id": "ERP-123",
        "document_id": "33333333-3333-4333-8333-333333333333",
        "institution_id": "11111111-1111-4111-8111-111111111111",
        "file_name": nome,
        "content_type": "application/pdf",
        "sha256": resumo,
        "document_type": "historico",
        "source_system": "ERP",
        "created_at": "2026-08-29T20:00:00Z",
        "environment": "test",
    }


@pytest.mark.asyncio
async def test_filewatch_success():
    
    pdf_path = DIR_INCOMING / "doc1.pdf"
    manifest_path = DIR_INCOMING / "doc1.json"
    
    # Create PDF content
    pdf_content = b"fake pdf content"
    pdf_path.write_bytes(pdf_content)
    
    sha256_hash = hashlib.sha256(pdf_content).hexdigest()
    
    manifest_data = criar_manifesto("doc1.pdf", sha256_hash)
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)
        
    # Fake mtime to make it stable
    old_time = (datetime.now() - timedelta(seconds=10)).timestamp()
    os.utime(pdf_path, (old_time, old_time))
    os.utime(manifest_path, (old_time, old_time))
    
    db = TestingSessionLocal()
    await process_ingestion_file(manifest_path, db)
    
    # Check completed dir
    assert (DIR_COMPLETED / "doc1.pdf").exists()
    assert (DIR_COMPLETED / "doc1.json").exists()
    
    # Check DB
    job = db.query(models.IngestionJob).first()
    assert job is not None
    assert job.status == "COMPLETED"
    assert job.file_hash == sha256_hash
    
    db.close()


@pytest.mark.asyncio
async def test_filewatch_duplicate_ingestion_is_idempotent():
    pdf_path = DIR_INCOMING / "duplicado.pdf"
    manifest_path = DIR_INCOMING / "duplicado.json"
    pdf_content = b"duplicate pdf content"
    pdf_path.write_bytes(pdf_content)
    manifest_path.write_text(json.dumps(
        criar_manifesto(pdf_path.name, hashlib.sha256(pdf_content).hexdigest())
    ), encoding="utf-8")
    old_time = (datetime.now() - timedelta(seconds=10)).timestamp()
    os.utime(pdf_path, (old_time, old_time))
    os.utime(manifest_path, (old_time, old_time))

    with TestingSessionLocal() as sessao:
        await process_ingestion_file(manifest_path, sessao)
        duplicate_pdf = DIR_INCOMING / pdf_path.name
        duplicate_manifest = DIR_INCOMING / manifest_path.name
        duplicate_pdf.write_bytes(pdf_content)
        duplicate_manifest.write_text(json.dumps(
            criar_manifesto(pdf_path.name, hashlib.sha256(pdf_content).hexdigest())
        ), encoding="utf-8")
        os.utime(duplicate_pdf, (old_time, old_time))
        os.utime(duplicate_manifest, (old_time, old_time))
        await process_ingestion_file(duplicate_manifest, sessao)

        assert sessao.query(models.IngestionJob).count() == 1
        assert sessao.query(models.IngestionJob).one().status == "COMPLETED"
        assert not duplicate_pdf.exists()
        assert not duplicate_manifest.exists()

    assert (DIR_COMPLETED / pdf_path.name).exists()
    assert (DIR_COMPLETED / manifest_path.name).exists()

@pytest.mark.asyncio
async def test_filewatch_quarantine_invalid_hash():
    
    pdf_path = DIR_INCOMING / "doc2.pdf"
    manifest_path = DIR_INCOMING / "doc2.json"
    
    pdf_content = b"fake pdf content 2"
    pdf_path.write_bytes(pdf_content)
    
    manifest_data = criar_manifesto("doc2.pdf", "0" * 64)
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)
        
    old_time = (datetime.now() - timedelta(seconds=10)).timestamp()
    os.utime(pdf_path, (old_time, old_time))
    os.utime(manifest_path, (old_time, old_time))
    
    db = TestingSessionLocal()
    await process_ingestion_file(manifest_path, db)
    
    # Check quarantine dir
    assert (DIR_QUARANTINE / "doc2.pdf").exists()
    assert (DIR_QUARANTINE / "doc2.json").exists()
    
    db.close()


@pytest.mark.parametrize("campo", list(criar_manifesto("doc.pdf", "0" * 64)))
def test_manifesto_exige_campos_obrigatorios(campo):
    from app.schemas_filewatch import validar_manifesto
    dados = criar_manifesto("doc.pdf", "0" * 64)
    del dados[campo]
    with pytest.raises(ValueError):
        validar_manifesto(dados, "doc.pdf")


@pytest.mark.parametrize("campo,valor", [
    ("manifest_version", 2), ("manifest_version", True), ("manifest_version", "1"),
    ("ingestion_id", "invalido"), ("document_id", "invalido"),
    ("institution_id", "invalido"), ("sha256", "invalido"),
    ("file_name", "../doc.pdf"), ("file_name", "outro.pdf"),
    ("content_type", "text/plain"), ("created_at", "2026-08-29T20:00:00"),
    ("environment", "desconhecido"), ("source_system", " "),
    ("metadata", []), ("campo_desconhecido", "valor"),
])
def test_manifesto_recusa_contrato_invalido(campo, valor):
    from app.schemas_filewatch import validar_manifesto
    dados = criar_manifesto("doc.pdf", "0" * 64)
    dados[campo] = valor
    with pytest.raises(ValueError):
        validar_manifesto(dados, "doc.pdf")


@pytest.mark.asyncio
@pytest.mark.parametrize("dados", [[], None, 123, {"manifest_version": 99}])
async def test_manifesto_invalido_preserva_par_em_quarentena(dados):
    manifesto = DIR_INCOMING / "invalido.json"
    pdf = DIR_INCOMING / "invalido.pdf"
    manifesto.write_text(json.dumps(dados), encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4 teste")
    instante = (datetime.now() - timedelta(seconds=10)).timestamp()
    for arquivo in (manifesto, pdf):
        os.utime(arquivo, (instante, instante))
    with TestingSessionLocal() as sessao:
        await process_ingestion_file(manifesto, sessao)
    assert (DIR_QUARANTINE / pdf.name).read_bytes() == b"%PDF-1.4 teste"
    assert json.loads((DIR_QUARANTINE / manifesto.name).read_text()) == dados


def test_manifesto_valido():
    from app.schemas_filewatch import validar_manifesto
    dados = criar_manifesto("doc.pdf", "0" * 64)
    dados["metadata"] = {"student_id": "aluno", "group_id": None}
    manifesto = validar_manifesto(dados, "doc.pdf")
    assert manifesto.manifest_version == 1
    assert manifesto.metadata == dados["metadata"]


@pytest.mark.asyncio
@pytest.mark.parametrize("alteracao", ["ambiente", "documento_ausente", "outra_instituicao"])
async def test_filewatch_recusa_destino_incompativel(alteracao):
    from app.models_ged import GEDDocument
    dados = criar_manifesto("destino.pdf", hashlib.sha256(b"%PDF-1.4 teste").hexdigest())
    with TestingSessionLocal() as sessao:
        if alteracao == "ambiente":
            dados["environment"] = "production"
        elif alteracao == "documento_ausente":
            dados["document_id"] = "44444444-4444-4444-8444-444444444444"
        else:
            outra = models.Institution(id="outra", name="Outra", cnpj="456", legal_name="Outra")
            sessao.add(outra)
            sessao.flush()
            sessao.get(GEDDocument, dados["document_id"]).institution_id = outra.id
            sessao.commit()
        manifesto = DIR_INCOMING / "destino.json"
        pdf = DIR_INCOMING / "destino.pdf"
        manifesto.write_text(json.dumps(dados), encoding="utf-8")
        pdf.write_bytes(b"%PDF-1.4 teste")
        instante = (datetime.now() - timedelta(seconds=10)).timestamp()
        for arquivo in (manifesto, pdf):
            os.utime(arquivo, (instante, instante))
        await process_ingestion_file(manifesto, sessao)
        tarefa = sessao.query(models.IngestionJob).one()
        assert tarefa.status == "QUARANTINE"
        assert tarefa.error_message
        assert (DIR_QUARANTINE / pdf.name).read_bytes() == b"%PDF-1.4 teste"
        assert not (DIR_COMPLETED / pdf.name).exists()
