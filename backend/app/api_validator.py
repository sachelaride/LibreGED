from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from app.database import get_db
from app import models
from app.auth import get_current_active_user
from app.models_xsd import SchemaVersion
from app.xsd_validator import validate_xml_against_xsd
import os

router = APIRouter(tags=["GED - Validações"])

class XSDValidatorRequest(BaseModel):
    xml_content: str
    document_type_code: str
    environment: str = "homologation"

class XSDValidatorResponse(BaseModel):
    valid: bool
    schema_code: Optional[str] = None
    errors: List[str] = []

@router.post("/api/xsd/validator", response_model=XSDValidatorResponse)
def validate_xml_agnostic(
    payload: XSDValidatorRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Motor Agnostico de XSD:
    Busca o Schema Vigente para o código de documento solicitado e valida a string XML.
    """
    # 1. Obter a versão vigente do Schema
    schema = db.query(SchemaVersion).filter(
        SchemaVersion.code == payload.document_type_code,
        SchemaVersion.environment == payload.environment,
        SchemaVersion.status == "approved"
    ).order_by(SchemaVersion.valid_from.desc()).first()
    
    if not schema:
        return XSDValidatorResponse(
            valid=False,
            errors=[f"Nenhum Schema 'Vigente' encontrado para o documento: {payload.document_type_code}"]
        )
    
    # 2. Salvar arquivo temporário do XML (xsd_validator precisa de arquivo físico na implementação atual)
    # Mas como validate_xml_against_xsd aceita o arquivo XML para validar, 
    # teremos que ver se a assinatura dele permite receber string.
    # Vou escrever um arquivo temporário.
    import tempfile
    
    xml_fd, xml_path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(xml_fd, 'w', encoding='utf-8') as f:
        f.write(payload.xml_content)
        
    try:
        # Pega o XSD da pasta local
        xsd_path = os.path.join(os.path.dirname(__file__), "..", "schemas", schema.code + ".xsd")
        
        # Fallback para o XSD mock se não existir o real
        if not os.path.exists(xsd_path):
            xsd_path = os.path.join(os.path.dirname(__file__), "..", "schemas", "mock_diploma.xsd")
            
        validation_result = validate_xml_against_xsd(xml_path, xsd_path)
        
        return XSDValidatorResponse(
            valid=validation_result["valid"],
            schema_code=schema.code,
            errors=validation_result.get("errors", [])
        )
    finally:
        os.remove(xml_path)
