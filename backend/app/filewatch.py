import os
import json
import shutil
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import unicodedata
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models
from app.storage import STORAGE_ROOT
from app.schemas_filewatch import validar_manifesto
from app.config import settings
from app.models_ged import GEDDocument, DocumentCategory
from app.models_ged_config import DocumentType

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


def _normalizar_tipo(valor: str) -> str:
    return "".join(
        caractere for caractere in unicodedata.normalize("NFKD", valor).lower()
        if not unicodedata.combining(caractere)
    ).strip()


def validar_tipo_documental(db: Session, documento: GEDDocument, nome_manifesto: str) -> None:
    """Ensure the manifest type matches the active configured document type."""
    configurados = db.query(DocumentType).all()
    nome = _normalizar_tipo(nome_manifesto)
    if configurados:
        tipo = next((item for item in configurados if _normalizar_tipo(item.name) == nome), None)
        if tipo is None or not tipo.is_active:
            raise ValueError("Tipo documental inexistente ou inativo.")
        if documento.category_id != tipo.id:
            raise ValueError("Tipo documental incompatível com o documento de destino.")
        return

    # Compatibility with legacy installations that still use DocumentCategory.
    categoria = db.get(DocumentCategory, documento.category_id)
    if categoria is None:
        raise ValueError("Tipo documental incompatível com o documento de destino.")
    categoria_nome = _normalizar_tipo(categoria.name)
    if categoria_nome != nome and SequenceMatcher(None, categoria_nome, nome).ratio() < 0.85:
        raise ValueError("Tipo documental incompatível com o documento de destino.")


def publish_ingestion_pair(pdf_content: bytes, manifest_content: bytes, base_name: str) -> tuple[Path, Path]:
    """Publish a package atomically: payload first, manifest last."""
    if Path(base_name).name != base_name or not base_name:
        raise ValueError("Nome de pacote inválido.")
    pdf_path = DIR_INCOMING / f"{base_name}.pdf"
    manifest_path = DIR_INCOMING / f"{base_name}.json"
    pdf_part = DIR_INCOMING / f"{base_name}.pdf.part"
    manifest_part = DIR_INCOMING / f"{base_name}.json.part"
    pdf_part.write_bytes(pdf_content)
    os.replace(pdf_part, pdf_path)
    manifest_part.write_bytes(manifest_content)
    os.replace(manifest_part, manifest_path)
    return pdf_path, manifest_path

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
            
        manifesto = validar_manifesto(manifest_data, pdf_path.name)
        ambiente = "homologation" if settings.ENVIRONMENT == "staging" else settings.ENVIRONMENT
        if manifesto.environment != ambiente:
            raise ValueError("O ambiente do manifesto difere do ambiente do worker.")
                
        # Validate hash
        actual_hash = calculate_sha256(processing_pdf)
        if actual_hash != manifesto.sha256:
            raise ValueError("O SHA-256 do PDF difere do informado no manifesto.")
            
        # Validate Institution
        inst = db.get(models.Institution, str(manifesto.institution_id))
        if not inst:
            raise ValueError("Instituição do manifesto não encontrada.")
        documento = db.get(GEDDocument, str(manifesto.document_id))
        if documento is None or documento.institution_id != inst.id:
            raise ValueError("Documento não encontrado na instituição informada.")
        validar_tipo_documental(db, documento, manifesto.document_type)

        existing_job = db.query(models.IngestionJob).filter(
            models.IngestionJob.ingestion_id == str(manifesto.ingestion_id)
        ).with_for_update().first()
        retry_job = None
        if existing_job is not None:
            same_payload = (
                existing_job.file_hash == actual_hash
                and existing_job.document_id == str(manifesto.document_id)
                and existing_job.institution_id == inst.id
            )
            if same_payload:
                if existing_job.status in {"PENDING", "FAILED", "RETRY"}:
                    retry_job = existing_job
                    retry_job.status = "PROCESSING"
                    retry_job.next_attempt_at = None
                else:
                    # A mesma entrega nunca deve criar um segundo processamento.
                    processing_pdf.unlink()
                    processing_manifest.unlink()
                    print(f"[FileWatch] Duplicate delivery ignored: {manifest_path.name}")
                    return
            raise ValueError(
                "Conflito de idempotência: o ingestion_id já existe com outro "
                "documento, instituição ou SHA-256."
            )
            
        new_job = retry_job or models.IngestionJob(
            id=str(uuid.uuid4()),
            ingestion_id=str(manifesto.ingestion_id),
            correlation_id=manifesto.correlation_id,
            document_id=str(manifesto.document_id),
            institution_id=inst.id,
            file_path=str(DIR_COMPLETED / pdf_path.name),
            manifest_path=str(DIR_COMPLETED / manifest_path.name),
            file_hash=actual_hash,
        )
        new_job.status = "COMPLETED"
        new_job.file_path = str(DIR_COMPLETED / pdf_path.name)
        new_job.manifest_path = str(DIR_COMPLETED / manifest_path.name)
        new_job.file_hash = actual_hash
        new_job.completed_at = models.utc_now()
        db.add(new_job) if retry_job is None else None
        db.commit()
        
        # Move to completed
        shutil.move(str(processing_pdf), str(DIR_COMPLETED / pdf_path.name))
        shutil.move(str(processing_manifest), str(DIR_COMPLETED / manifest_path.name))
        print(f"[FileWatch] Completed {manifest_path.name}")
        
    except Exception as e:
        print(f"[FileWatch] Error processing {manifest_path.name}: {e}")
        # Log error in DB if possible, and move to quarantine
        job_id = str(uuid.uuid4())
        
        db.rollback()
        inst_id = manifest_data.get("institution_id") if isinstance(locals().get("manifest_data"), dict) else None
        if not isinstance(inst_id, str):
            inst_id = None
        inst = db.query(models.Institution).filter(models.Institution.id == inst_id).first() if inst_id else None
        permanent = True
        target_dir = DIR_QUARANTINE
        
        if inst:
            is_conflict = "Conflito de idempotência" in str(e)
            current_retries = 1
            if isinstance(manifest_data, dict) and manifest_data.get("ingestion_id"):
                previous = db.query(models.IngestionJob).filter_by(
                    ingestion_id=str(manifest_data["ingestion_id"])
                ).first()
                current_retries = (previous.retries + 1) if previous else 1
            retryable = not isinstance(e, ValueError)
            permanent = is_conflict or not retryable or current_retries >= settings.FILEWATCH_MAX_RETRIES
            retry_at = None if permanent else models.utc_now() + timedelta(
                seconds=settings.FILEWATCH_RETRY_BASE_SECONDS * (2 ** (current_retries - 1))
            )
            target_dir = DIR_QUARANTINE if permanent else DIR_RETRY
            new_job = previous or models.IngestionJob(
                id=job_id,
                institution_id=inst.id,
                ingestion_id=None if is_conflict else (
                    str(manifest_data.get("ingestion_id")) if isinstance(manifest_data, dict) else None
                ),
            )
            new_job.status = (
                "CONFLICT" if is_conflict
                else ("QUARANTINE" if not retryable else ("FAILED" if permanent else "RETRY"))
            )
            new_job.file_path = str(target_dir / pdf_path.name)
            new_job.manifest_path = str(target_dir / manifest_path.name)
            new_job.error_message = str(e)
            new_job.file_hash = actual_hash if 'actual_hash' in locals() else None
            new_job.retries = current_retries
            new_job.next_attempt_at = retry_at
            new_job.correlation_id = str(manifest_data.get("correlation_id")) if isinstance(manifest_data, dict) \
                and manifest_data.get("correlation_id") else None
            db.add(new_job)
            db.commit()
             
        shutil.move(str(processing_pdf), str(target_dir / pdf_path.name))
        shutil.move(str(processing_manifest), str(target_dir / manifest_path.name))


def promote_due_retries(db: Session):
    now = models.utc_now()
    jobs = db.query(models.IngestionJob).filter(
        models.IngestionJob.status == "RETRY",
        models.IngestionJob.next_attempt_at <= now,
    ).all()
    for job in jobs:
        pdf = Path(job.file_path)
        manifest = Path(job.manifest_path)
        if pdf.is_file() and manifest.is_file():
            target_pdf = DIR_INCOMING / pdf.name
            target_manifest = DIR_INCOMING / manifest.name
            shutil.move(str(pdf), str(target_pdf))
            shutil.move(str(manifest), str(target_manifest))
            job.status = "PENDING"
            job.next_attempt_at = None
    db.commit()

async def run_filewatch_cycle():
    """Runs a single cycle of the filewatch directory polling."""
    db = SessionLocal()
    try:
        promote_due_retries(db)
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
