import pytest
import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app import models
from app.models import Base
from app.filewatch import DIR_INCOMING, DIR_PROCESSING, DIR_COMPLETED, DIR_QUARANTINE, process_ingestion_file

# Setup testing DB
engine = create_engine("sqlite:///./test_filewatch.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    # Create test institution
    inst_id = "test-fw-inst"
    db.add(models.Institution(id=inst_id, name="FW Inst", cnpj="123", legal_name="FW Inst"))
    db.commit()
    db.close()
    
    yield
    Base.metadata.drop_all(bind=engine)

def _clean_dirs():
    for d in [DIR_INCOMING, DIR_PROCESSING, DIR_COMPLETED, DIR_QUARANTINE]:
        for f in d.glob("*"):
            f.unlink()

@pytest.mark.asyncio
async def test_filewatch_success():
    _clean_dirs()
    
    pdf_path = DIR_INCOMING / "doc1.pdf"
    manifest_path = DIR_INCOMING / "doc1.json"
    
    # Create PDF content
    pdf_content = b"fake pdf content"
    pdf_path.write_bytes(pdf_content)
    
    sha256_hash = hashlib.sha256(pdf_content).hexdigest()
    
    manifest_data = {
        "institution_id": "test-fw-inst",
        "document_type": "historico",
        "hash_sha256": sha256_hash
    }
    
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
async def test_filewatch_quarantine_invalid_hash():
    _clean_dirs()
    
    pdf_path = DIR_INCOMING / "doc2.pdf"
    manifest_path = DIR_INCOMING / "doc2.json"
    
    pdf_content = b"fake pdf content 2"
    pdf_path.write_bytes(pdf_content)
    
    manifest_data = {
        "institution_id": "test-fw-inst",
        "document_type": "historico",
        "hash_sha256": "invalidhash123"
    }
    
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
