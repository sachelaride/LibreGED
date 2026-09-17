from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from app.database import get_db
from app import models
from app.auth import get_current_active_user
from app.models_xsd import SchemaVersion
from app.xsd_validator import validate_xml_against_xsd

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
    
    schema_filename = f"{schema.code}.xsd"
    valid, errors = validate_xml_against_xsd(payload.xml_content, schema_filename)
    if schema.code == "mock_diploma" and not valid:
        # Keep the local mock schema available under the administrative code.
        valid, errors = validate_xml_against_xsd(
            payload.xml_content,
            "mock_diploma.xsd",
        )

    return XSDValidatorResponse(
        valid=valid,
        schema_code=schema.code,
        errors=errors,
    )
