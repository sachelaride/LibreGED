import pytest
import time
from app.database import SessionLocal
from app.models_ged import FilaProcessamento, GEDDocument, DocumentCategory, GEDAcademicPhase, GEDDocumentStatus
from app.worker_fila import _process_fila_loop, start_worker, stop_worker, _stop_event

def test_fila_worker_processing():
    db = SessionLocal()
    
    # 1. Cria mock do doc
    cat = db.query(DocumentCategory).first()
    if not cat:
        cat = DocumentCategory(name="Teste", index_code="000")
        db.add(cat)
        db.commit()
        db.refresh(cat)
        
    doc = GEDDocument(
        title="Diploma Queue Test",
        category_id=cat.id,
        academic_phase=GEDAcademicPhase.DIPLOMACAO,
        status=GEDDocumentStatus.RASCUNHO,
        file_path="mock"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # 2. Insere na Fila
    fila = FilaProcessamento(documento_id=doc.id)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    
    job_id = fila.job_id
    
    # 3. Dispara o worker numa thread ou manualmente (para teste, rodamos o script mas o paramos rápido)
    start_worker()
    
    # Aguarda tempo suficiente pro worker puxar a fila e processar (simulamos 2s lá dentro, então esperamos 3s)
    time.sleep(3)
    stop_worker()
    
    # 4. Verifica o resultado
    db.expire_all() # força refresh
    fila_check = db.query(FilaProcessamento).filter(FilaProcessamento.job_id == job_id).first()
    
    assert fila_check is not None
    assert fila_check.status == "CONCLUIDO"
    assert fila_check.tentativas == 1
    
    doc_check = db.query(GEDDocument).filter(GEDDocument.id == doc.id).first()
    assert doc_check.status == GEDDocumentStatus.VALIDO
    
    db.close()
