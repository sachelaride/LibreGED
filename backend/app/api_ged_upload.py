from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.storage import save_file
from app.models_ged import GEDDocument, GEDDocumentStatus, GEDAcademicPhase, DocumentCategory
from app.schemas_ged import GEDDocumentResponse
from app.ocr_engine import DocumentAnalyzer
import uuid
import json

router = APIRouter()
analyzer = DocumentAnalyzer()

@router.post("/api/ged/documents/upload", response_model=GEDDocumentResponse, tags=["GED - Vida Acadêmica (Matrícula)"])
async def upload_scanner_document(
    title: str = Form(...),
    category_code: str = Form(...),
    academic_phase: str = Form("MATRICULA"),
    student_id: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Rota para o scanner da recepção. Recebe um arquivo físico, faz a leitura via OCR/IA
    e o salva no estado PENDENTE_VALIDACAO contendo o JSON de metadados extraídos.
    """
    cat = db.query(DocumentCategory).filter(DocumentCategory.index_code == category_code).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Categoria (index_code) inválida.")
        
    content = await file.read()
    file_ext = file.filename.split(".")[-1] if file.filename else "pdf"
    safe_name = f"{uuid.uuid4()}.{file_ext}"
    saved_path = save_file(safe_name, content, db=db)
    
    # Acionar OCR mockado
    extracted_data = analyzer.analyze_document(saved_path, cat.name)
    json_metadata = json.dumps(extracted_data, ensure_ascii=False)
    
    db_doc = GEDDocument(
        title=title,
        file_path=saved_path,
        category_id=cat.id,
        student_id=student_id,
        academic_phase=GEDAcademicPhase(academic_phase),
        status=GEDDocumentStatus.PENDENTE_VALIDACAO,
        extracted_metadata=json_metadata
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    return db_doc
