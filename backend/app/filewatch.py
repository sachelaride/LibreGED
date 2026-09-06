import os
import json
import shutil
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models
from app.storage import STORAGE_ROOT

# Ingestion directories
INGESTION_ROOT = STORAGE_ROOT / "ingestion"
DIR_INCOMING = INGESTION_ROOT / "incoming"
DIR_PROCESSING = INGESTION_ROOT / "processing"
DIR_RETRY = INGESTION_ROOT / "retry"
DIR_QUARANTINE = INGESTION_ROOT / "quarantine"
DIR_COMPLETED = INGESTION_ROOT / "completed"
DIR_ORPHANED = INGESTION_ROOT / "orphaned"

for d in [DIR_INCOMING, DIR_PROCESSING, DIR_RETRY, DIR_QUARANTINE, DIR_COMPLETED, DIR_ORPHANED]:
    d.mkdir(parents=True, exist_ok=True)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_stable(file_path: Path, min_age_seconds: int = 5) -> bool:
    """Check if file has not been modified for at least min_age_seconds."""
    if not file_path.exists():
        return False
    mtime = file_path.stat().st_mtime
    now = datetime.now().timestamp()
    return (now - mtime) >= min_age_seconds

def calculate_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def process_ingestion_file(manifest_path: Path, db: Session):
    """Processes a single ingestion manifest and its associated PDF."""
    pdf_path = manifest_path.with_suffix(".pdf")
    
    if not pdf_path.exists():
        # Orphaned manifest
        if is_stable(manifest_path, 3600): # 1 hour
            print(f"[FileWatch] Orphaned manifest: {manifest_path.name}")
            shutil.move(str(manifest_path), str(DIR_ORPHANED / manifest_path.name))
        return
        
    if not is_stable(pdf_path) or not is_stable(manifest_path):
        return # wait until stable
        
    # ATOMIC CLAIM
    processing_manifest = DIR_PROCESSING / manifest_path.name
    processing_pdf = DIR_PROCESSING / pdf_path.name
    try:
        # Move both to processing atomically
        os.rename(manifest_path, processing_manifest)
        os.rename(pdf_path, processing_pdf)
    except OSError:
        # Another worker might have taken it
        return
        
    print(f"[FileWatch] Processing {manifest_path.name}...")
    
    try:
        # Load manifest
        with open(processing_manifest, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            
        required_keys = ["institution_id", "document_type", "hash_sha256"]
        for key in required_keys:
            if key not in manifest_data:
                raise ValueError(f"Missing required key in manifest: {key}")
                
        # Validate hash
        actual_hash = calculate_sha256(processing_pdf)
        if actual_hash != manifest_data["hash_sha256"]:
            raise ValueError(f"Hash mismatch. Expected {manifest_data['hash_sha256']}, got {actual_hash}")
            
        # Validate Institution
        inst = db.query(models.Institution).filter(models.Institution.id == manifest_data["institution_id"]).first()
        if not inst:
            raise ValueError(f"Institution {manifest_data['institution_id']} not found.")
            
        # Create IngestionJob
        job_id = str(uuid.uuid4())
        new_job = models.IngestionJob(
            id=job_id,
            institution_id=inst.id,
            status="COMPLETED",
            file_path=str(DIR_COMPLETED / pdf_path.name),
            manifest_path=str(DIR_COMPLETED / manifest_path.name),
            file_hash=actual_hash,
            completed_at=datetime.utcnow()
        )
        db.add(new_job)
        db.commit()
        
        # Move to completed
        shutil.move(str(processing_pdf), str(DIR_COMPLETED / pdf_path.name))
        shutil.move(str(processing_manifest), str(DIR_COMPLETED / manifest_path.name))
        print(f"[FileWatch] Completed {manifest_path.name}")
        
    except Exception as e:
        print(f"[FileWatch] Error processing {manifest_path.name}: {e}")
        # Log error in DB if possible, and move to quarantine
        job_id = str(uuid.uuid4())
        
        inst_id = manifest_data.get("institution_id") if 'manifest_data' in locals() else None
        inst = db.query(models.Institution).filter(models.Institution.id == inst_id).first() if inst_id else None
        
        if inst:
            new_job = models.IngestionJob(
                id=job_id,
                institution_id=inst.id,
                status="QUARANTINE",
                file_path=str(DIR_QUARANTINE / pdf_path.name),
                manifest_path=str(DIR_QUARANTINE / manifest_path.name),
                error_message=str(e),
                file_hash=actual_hash if 'actual_hash' in locals() else None,
            )
            db.add(new_job)
            db.commit()
             
        shutil.move(str(processing_pdf), str(DIR_QUARANTINE / pdf_path.name))
        shutil.move(str(processing_manifest), str(DIR_QUARANTINE / manifest_path.name))

async def run_filewatch_cycle():
    """Runs a single cycle of the filewatch directory polling."""
    db = next(get_db_session())
    try:
        manifests = list(DIR_INCOMING.glob("*.json"))
        for manifest in manifests:
            await process_ingestion_file(manifest, db)
            
        # Also check for orphaned PDFs (older than 1h without manifest)
        pdfs = list(DIR_INCOMING.glob("*.pdf"))
        for pdf in pdfs:
            manifest = pdf.with_suffix(".json")
            if not manifest.exists() and is_stable(pdf, 3600):
                print(f"[FileWatch] Orphaned PDF: {pdf.name}")
                shutil.move(str(pdf), str(DIR_ORPHANED / pdf.name))
    finally:
        db.close()
