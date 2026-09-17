from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_db
from app import models
from app.models_ged import GEDDocument
from app.models_xsd import SchemaVersion
from app.auth import get_current_active_user

class XmlGenerationRequest(BaseModel):
    student_name: str
    course_name: str
    status: str
    document_type: str
    schema_version: Optional[str] = None
    namespace: Optional[str] = None
    environment: str = "homologation"

router = APIRouter(tags=["GED - Vida Acadêmica (Curso e Diplomação)"])

# Schemas repetidos ou importados
class StudentResponse(BaseModel):
    id: str
    institution_id: str
    full_name: str
    birth_date: date
    cpf: str
    email: str
    model_config = ConfigDict(from_attributes=True)

class EnrollmentResponse(BaseModel):
    id: str
    institution_id: str
    student_id: str
    course_name: str
    class_name: str
    year: int
    status: str
    model_config = ConfigDict(from_attributes=True)

@router.get("/api/students", response_model=List[StudentResponse])
def get_students(
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Student)
    if institution_id:
        query = query.filter(models.Student.institution_id == institution_id)
    # Por segurança, sempre filtramos pela instituição do usuário, a não ser que ele seja admin global
    if current_user.role != "admin_global":
        query = query.filter(models.Student.institution_id == current_user.institution_id)
    
    return query.all()

@router.get("/api/enrollments", response_model=List[EnrollmentResponse])
def get_enrollments(
    student_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Enrollment)
    if student_id:
        query = query.filter(models.Enrollment.student_id == student_id)
    
    if current_user.role != "admin_global":
        query = query.filter(models.Enrollment.institution_id == current_user.institution_id)
        
    return query.all()

@router.post("/api/documents/{document_id}/xml")
def generate_xml_for_document(
    document_id: str,
    payload: XmlGenerationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Validar documento
    document = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Verificar permissão do documento
    from app.auth import verify_document_ownership
    verify_document_ownership(current_user, document)

    if not payload.schema_version:
        from app.main import add_audit
        add_audit(
            db,
            "document",
            document_id,
            "xml_generation_blocked",
            "Schema version is required; inference is forbidden.",
            current_user.id,
        )
        db.commit()
        raise HTTPException(409, "schema version inference is forbidden")

    schema = db.query(SchemaVersion).filter(
        SchemaVersion.code == payload.schema_version,
        SchemaVersion.environment == payload.environment,
        SchemaVersion.status == "approved",
    ).first()
    if not schema:
        raise HTTPException(409, "schema version is not approved")

    generated_xml = ""
    # Selecionar o gerador correto de acordo com o tipo
    if payload.document_type == "diploma":
        from app.diploma_generator import generate_diploma_xml
        from app.schemas_diploma import Model as DiplomaPayload
        # Dados mockados para gerar XML. Na vida real viriam do ERP ou form
        data = DiplomaPayload(
            student_name=payload.student_name,
            course_name=payload.course_name,
            status=payload.status,
            namespace=payload.namespace,
            environment=payload.environment
        )
        generated_xml = generate_diploma_xml(data)
    elif payload.document_type == "historico":
        from app.historico_generator import generate_historico_xml
        from app.schemas_historico import Model as HistoricoPayload
        data = HistoricoPayload(
            student_name=payload.student_name,
            course_name=payload.course_name,
            status=payload.status
        )
        generated_xml = generate_historico_xml(data)
    elif payload.document_type == "curriculo":
        from app.curriculo_generator import generate_curriculo_xml
        from app.schemas_curriculo import Model as CurriculoPayload
        data = CurriculoPayload(
            course_name=payload.course_name
        )
        generated_xml = generate_curriculo_xml(data)
    else:
        raise HTTPException(status_code=400, detail="Invalid document type for XML generation")
        
    from app.main import add_audit
    add_audit(db, "document", document_id, "xml_generated", f"XML generated for {payload.document_type}", current_user.id)
    db.commit()
    return {"xml_content": generated_xml}


@router.post("/api/documents/{document_id}/representation")
def generate_visual_representation(
    document_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Essa rota geraria o RVDD (Representação Visual do Diploma Digital) ou HTML do histórico.
    document = db.query(GEDDocument).filter(GEDDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.auth import verify_document_ownership
    verify_document_ownership(current_user, document)

    from app.rvdd_generator import generate_rvdd_html
    html_content = generate_rvdd_html(document_id, payload.get("student_name", "Aluno"), payload.get("course_name", "Curso"))
    
    from app.main import add_audit
    add_audit(db, "document", document_id, "representation_generated", "Visual representation generated", current_user.id)
    db.commit()
    
    # Retornar como JSON para facilidade, o frontend renderiza num iframe
    return {"html_content": html_content}
