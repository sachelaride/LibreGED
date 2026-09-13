from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app import models, auth
from app.models_xsd import SchemaVersion
from app.schemas_pagination import PaginatedResponse
import math

router = APIRouter()

class SchemaVersionCreate(BaseModel):
    document_type_id: str
    code: str
    namespace: str
    xsd_hash: str
    environment: str = "homologation"

class SchemaVersionUpdate(BaseModel):
    code: Optional[str] = None
    namespace: Optional[str] = None
    xsd_hash: Optional[str] = None
    environment: Optional[str] = None

class SchemaVersionResponse(SchemaVersionCreate):
    id: str
    status: str
    valid_from: datetime
    valid_until: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/xsd", response_model=PaginatedResponse[SchemaVersionResponse], tags=["Admin - XSD"])
def get_schemas(document_type_id: Optional[str] = None, page: int = 1, size: int = 50, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    query = db.query(SchemaVersion)
    if document_type_id:
        query = query.filter(SchemaVersion.document_type_id == document_type_id)
        
    total = query.count()
    items = query.order_by(SchemaVersion.created_at.desc()).offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if size > 0 else 0
    
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

@router.post("/xsd", response_model=SchemaVersionResponse, tags=["Admin - XSD"])
def create_schema(payload: SchemaVersionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    # Verify doc type exists
    from app.models_ged_config import DocumentType
    doc_type = db.query(DocumentType).filter(DocumentType.id == payload.document_type_id).first()
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")
        
    new_schema = SchemaVersion(
        document_type_id=payload.document_type_id,
        code=payload.code,
        namespace=payload.namespace,
        xsd_hash=payload.xsd_hash,
        environment=payload.environment,
        status="proposed"
    )
    db.add(new_schema)
    db.commit()
    db.refresh(new_schema)
    
    from app.main import add_audit
    add_audit(db, "xsd", new_schema.id, "created", f"Schema {new_schema.code} created", current_user.id)
    
    return new_schema

@router.put("/xsd/{schema_id}", response_model=SchemaVersionResponse, tags=["Admin - XSD"])
def update_schema(schema_id: str, payload: SchemaVersionUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    schema = db.query(SchemaVersion).filter(SchemaVersion.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
        
    if payload.code is not None:
        schema.code = payload.code
    if payload.namespace is not None:
        schema.namespace = payload.namespace
    if payload.xsd_hash is not None:
        schema.xsd_hash = payload.xsd_hash
    if payload.environment is not None:
        schema.environment = payload.environment
        
    db.commit()
    db.refresh(schema)
    
    from app.main import add_audit
    add_audit(db, "xsd", schema.id, "updated", f"Schema {schema.code} updated", current_user.id)
    
    return schema

@router.delete("/xsd/{schema_id}", status_code=204, tags=["Admin - XSD"])
def delete_schema(schema_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    schema = db.query(SchemaVersion).filter(SchemaVersion.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
        
    if schema.status == "approved":
        raise HTTPException(status_code=409, detail="Não é possível excluir um schema aprovado.")
        
    from app.main import add_audit
    add_audit(db, "xsd", schema.id, "deleted", f"Schema {schema.code} deleted", current_user.id)
    
    db.delete(schema)
    db.commit()
    return None

@router.post("/xsd/{schema_id}/approve", response_model=SchemaVersionResponse, tags=["Admin - XSD"])
def approve_schema(schema_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_admin)):
    schema = db.query(SchemaVersion).filter(SchemaVersion.id == schema_id).first()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
        
    schema.status = "approved"
    # Retire others in the same environment and document type
    others = db.query(SchemaVersion).filter(
        SchemaVersion.document_type_id == schema.document_type_id,
        SchemaVersion.environment == schema.environment,
        SchemaVersion.id != schema.id,
        SchemaVersion.status == "approved"
    ).all()
    
    for other in others:
        other.status = "retired"
        other.valid_until = datetime.utcnow()
        
    db.commit()
    db.refresh(schema)
    
    from app.main import add_audit
    add_audit(db, "xsd", schema.id, "approved", f"Schema {schema.code} approved", current_user.id)
    
    return schema
