from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.storage import save_file, load_file
from app.models_ged import Signer, GEDDocument, GEDDocumentStatus, DocumentTransitionHistory, SignatureLog
from app.schemas_ged import SignerResponse, SignerCreate
from app.digital_signature import sign_xml_document, sign_pdf_document, get_cert_info_from_p12, get_file_hash
import uuid
import os
from pydantic import BaseModel
from datetime import datetime, UTC

from app.auth import get_current_active_user, role_checker
from app.models import User
from app.document_permissions import exigir_documento

router = APIRouter()

@router.post("/api/signers", response_model=SignerResponse, tags=["Assinaturas Híbridas"])
async def create_signer(
    name: str = Form(...),
    role: str = Form(...),
    cpf: str = Form(...),
    p12_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: User = Depends(role_checker(["admin_global"]))
):
    content = await p12_file.read()
    file_ext = p12_file.filename.split(".")[-1] if p12_file.filename else "p12"
    safe_name = f"cert_{uuid.uuid4()}.{file_ext}"
    saved_path = save_file(safe_name, content, db=db)
    
    db_signer = Signer(
        name=name,
        role=role,
        cpf=cpf,
        certificate_path=saved_path
    )
    db.add(db_signer)
    db.commit()
    db.refresh(db_signer)
    return db_signer

class SignRequest(BaseModel):
    signer_id: str
    password: str
    comments: str = "Assinatura Digital ICP-Brasil / PAdES-XMLDSig"

@router.post("/api/documents/{document_id}/sign", tags=["Assinaturas Híbridas"])
def sign_document(document_id: str, payload: SignRequest, db: Session = Depends(get_db),
                  usuario: User = Depends(get_current_active_user)):
    doc = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    
    exigir_documento(db, usuario, doc, "assinar")
    if doc.status in (GEDDocumentStatus.ARQUIVADO, GEDDocumentStatus.QUARENTENA, GEDDocumentStatus.SUSPENSO):
        raise HTTPException(409, "Documento arquivado ou em quarentena não pode ser assinado.")
    signer = db.query(Signer).filter(Signer.id == payload.signer_id).first()
    if not signer or not signer.certificate_path:
        raise HTTPException(status_code=404, detail="Signatário ou certificado não encontrado.")
    
    # 1. Determinar o tipo de arquivo
    is_xml = doc.file_path.lower().endswith(".xml")
    is_pdf = doc.file_path.lower().endswith(".pdf")
    
    if not is_xml and not is_pdf:
        raise HTTPException(status_code=400, detail="Apenas XML ou PDF são suportados para assinatura digital.")
        
    sig_type = "XMLDSig" if is_xml else "PAdES"
    
    # Absolute paths
    from app.config import UPLOAD_DIR
    import urllib.parse
    
    file_name = doc.file_path.split("/")[-1].split("\\")[-1]
    
    # We must properly decode the filename in case it has URL encoding
    decoded_file_name = urllib.parse.unquote(file_name)
    real_doc_path = os.path.join(UPLOAD_DIR, decoded_file_name)
    real_p12_path = os.path.join(UPLOAD_DIR, signer.certificate_path)
    
    if not os.path.exists(real_doc_path):
        raise HTTPException(500, f"Arquivo físico {real_doc_path} não encontrado no disco.")
    if not os.path.exists(real_p12_path):
        raise HTTPException(500, "Certificado digital não encontrado no disco.")
        
    # 2. Extrair Hash original e Info do certificado
    original_hash = get_file_hash(real_doc_path)
    
    try:
        cert_sub, cert_iss = get_cert_info_from_p12(real_p12_path, payload.password)
    except Exception as e:
        raise HTTPException(400, "Senha incorreta ou certificado inválido.")
        
    # Criar SignatureLog PENDING
    sig_log = SignatureLog(
        document_id=doc.id,
        user_id=usuario.id,
        signature_type=sig_type,
        original_file_hash=original_hash,
        certificate_subject=cert_sub,
        certificate_issuer=cert_iss,
        status="PENDING"
    )
    db.add(sig_log)
    db.commit()

    # 3. Assinar
    try:
        if is_xml:
            with open(real_doc_path, 'r', encoding='utf-8') as f:
                xml_string = f.read()
            signed_xml = sign_xml_document(xml_string, real_p12_path, payload.password)
            with open(real_doc_path, 'w', encoding='utf-8') as f:
                f.write(signed_xml)
        else:
            out_path = real_doc_path + ".signed.pdf"
            sign_pdf_document(real_doc_path, real_p12_path, payload.password, out_path)
            # Substituir original pelo assinado
            os.replace(out_path, real_doc_path)
            
        sig_log.status = "SUCCESS"
        sig_log.tsa_timestamp = datetime.now(UTC).replace(tzinfo=None)
        
    except Exception as e:
        sig_log.status = "FAILED"
        sig_log.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Erro durante assinatura: {str(e)}")
        
    # Atualiza Status
    old_status = doc.status
    doc.status = GEDDocumentStatus.ASSINADO
    
    transition = DocumentTransitionHistory(
        document_id=doc.id,
        from_status=old_status,
        to_status=GEDDocumentStatus.ASSINADO,
        comments=payload.comments
    )
    db.add(transition)
    db.commit()
    
    return {"message": "Documento assinado com sucesso", "log_id": sig_log.id, "type": sig_type}

@router.get("/api/signers", tags=["Assinaturas Híbridas"])
def list_signers(db: Session = Depends(get_db), usuario: User = Depends(get_current_active_user)):
    signers = db.query(Signer).filter(Signer.is_active == 1).all()
    # We only return safe metadata, not the certificate path
    return [{"id": s.id, "name": s.name, "role": s.role, "cpf": s.cpf} for s in signers]

@router.get("/api/documents/{document_id}/signatures", tags=["Assinaturas Híbridas"])
def get_document_signatures(document_id: str, db: Session = Depends(get_db), usuario: User = Depends(get_current_active_user)):
    logs = db.query(SignatureLog).filter(SignatureLog.document_id == document_id).order_by(SignatureLog.created_at.desc()).all()
    return logs
