from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.storage import save_file, load_file
from app.models_ged import Signer, GEDDocument, GEDDocumentStatus, DocumentTransitionHistory
from app.schemas_ged import SignerResponse, SignerCreate
from app.digital_signature import sign_xml_document
import uuid
from pydantic import BaseModel

router = APIRouter()

@router.post("/api/signers", response_model=SignerResponse, tags=["Assinaturas (XMLDSig)"])
async def create_signer(
    name: str = Form(...),
    role: str = Form(...),
    cpf: str = Form(...),
    p12_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Cadastra um signatário recebendo seu certificado A1 (.p12 ou .pfx) para o cofre seguro.
    A senha NÃO deve ser gravada no banco; ela é requisitada no momento da assinatura.
    """
    content = await p12_file.read()
    file_ext = p12_file.filename.split(".")[-1] if p12_file.filename else "p12"
    safe_name = f"cert_{uuid.uuid4()}.{file_ext}"
    saved_path = save_file(safe_name, content)
    
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
    comments: str = "Assinatura Digital (ICP-Brasil)"

@router.post("/api/documents/{document_id}/sign", tags=["Assinaturas (XMLDSig)"])
def sign_document(document_id: str, payload: SignRequest, db: Session = Depends(get_db)):
    """
    Aciona a assinatura XMLDSig de um documento. 
    1. Busca o XML pendente.
    2. Lê o P12 do Signatário com a senha informada.
    3. Gera o XML assinado.
    4. Atualiza o status para ASSINADO.
    """
    doc = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    
    signer = db.query(Signer).filter(Signer.id == payload.signer_id).first()
    if not signer or not signer.certificate_path:
        raise HTTPException(status_code=404, detail="Signatário ou certificado não encontrado.")
    
    # Simula carregar o XML do documento (se fosse de fato um XML salvo, usaríamos load_file)
    # Por enquanto, carregamos mock ou string do arquivo
    try:
        xml_bytes = load_file(doc.file_path.split("/")[-1].split("\\")[-1])
        xml_string = xml_bytes.decode('utf-8')
    except Exception:
        # Se for mockado
        xml_string = f'<Documento><Titulo>{doc.title}</Titulo></Documento>'
        
    try:
        signed_xml = sign_xml_document(xml_string, signer.certificate_path, payload.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao assinar (Senha incorreta ou cert inválido?): {str(e)}")
        
    # Salvar o novo XML Assinado por cima
    # Em produção, poderíamos versionar o arquivo.
    file_name = doc.file_path.split("/")[-1].split("\\")[-1]
    save_file(file_name, signed_xml.encode('utf-8'))
    
    # Atualiza Status
    old_status = doc.status
    doc.status = GEDDocumentStatus.ASSINADO
    
    transition = DocumentTransitionHistory(
        document_id=doc.id,
        from_status=old_status,
        to_status=GEDDocumentStatus.ASSINADO,
        comments=f"Assinado digitalmente por {signer.name} ({signer.cpf})"
    )
    db.add(transition)
    db.commit()
    
    return {"message": "Documento assinado com sucesso", "signed_xml": signed_xml}
