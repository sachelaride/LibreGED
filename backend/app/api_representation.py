from datetime import datetime
from hashlib import sha256

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from lxml import etree
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth, models, models_representation
from app.database import get_db
from app.schemas_representation import (
    REPRESENTATION_DOCUMENT_TYPES,
    RepresentationExecutionRequest,
    RepresentationExecutionResponse,
    RepresentationServiceCreate,
    RepresentationServiceResponse,
    RepresentationVersionCreate,
    RepresentationVersionResponse,
)

router = APIRouter(prefix="/api/representation-services", tags=["GED - Representação Visual"])


def _hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _validate_document_type(document_type: str) -> None:
    if document_type not in REPRESENTATION_DOCUMENT_TYPES:
        raise HTTPException(status_code=422, detail="Tipo de documento de representação inválido")


def _compile_xslt(content: str) -> None:
    try:
        etree.XSLT(etree.XML(content.encode("utf-8"), parser=etree.XMLParser(resolve_entities=False, no_network=True)))
    except (etree.XMLSyntaxError, etree.XSLTParseError) as exc:
        raise HTTPException(status_code=422, detail=f"XSLT inválido: {exc}") from exc


def _audit(db: Session, entity_id: str, action: str, details: str, user_id: str) -> None:
    from app.main import add_audit

    add_audit(db, "representation_service", entity_id, action, details, user_id)


@router.get("", response_model=list[RepresentationServiceResponse])
def list_services(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin),
):
    return db.query(models_representation.RepresentationService).order_by(
        models_representation.RepresentationService.name
    ).all()


@router.post("", response_model=RepresentationServiceResponse, status_code=201)
def create_service(
    payload: RepresentationServiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin),
):
    _validate_document_type(payload.document_type)
    service = models_representation.RepresentationService(**payload.model_dump())
    db.add(service)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Código de serviço já cadastrado") from exc
    db.refresh(service)
    _audit(db, service.id, "created", f"Serviço {service.code} criado", current_user.id)
    db.commit()
    return service


@router.get("/{service_id}/versions", response_model=list[RepresentationVersionResponse])
def list_versions(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin),
):
    if not db.get(models_representation.RepresentationService, service_id):
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return db.query(models_representation.RepresentationServiceVersion).filter_by(
        service_id=service_id
    ).order_by(models_representation.RepresentationServiceVersion.revision.desc()).all()


def _create_version(service_id: str, version_label: str, xslt_content: str, user_id: str, db: Session):
    _compile_xslt(xslt_content)
    last = db.query(models_representation.RepresentationServiceVersion).filter_by(
        service_id=service_id
    ).order_by(models_representation.RepresentationServiceVersion.revision.desc()).first()
    version = models_representation.RepresentationServiceVersion(
        service_id=service_id,
        revision=(last.revision + 1 if last else 1),
        version_label=version_label,
        xslt_content=xslt_content,
        content_hash=_hash(xslt_content),
        created_by_user_id=user_id,
    )
    db.add(version)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Versão já cadastrada para este serviço") from exc
    db.refresh(version)
    _audit(db, version.id, "version_created", f"Versão {version.version_label} criada", user_id)
    db.commit()
    return version


@router.post("/{service_id}/versions", response_model=RepresentationVersionResponse, status_code=201)
def create_version(
    service_id: str,
    payload: RepresentationVersionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin),
):
    if not db.get(models_representation.RepresentationService, service_id):
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return _create_version(service_id, payload.version_label, payload.xslt_content, current_user.id, db)


@router.post("/{service_id}/versions/upload", response_model=RepresentationVersionResponse, status_code=201)
async def upload_version(
    service_id: str,
    version_label: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin),
):
    if not db.get(models_representation.RepresentationService, service_id):
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    try:
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="O XSLT deve ser UTF-8") from exc
    return _create_version(service_id, version_label, content, current_user.id, db)


@router.post("/{service_id}/versions/{version_id}/publish", response_model=RepresentationVersionResponse)
def publish_version(
    service_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin),
):
    version = db.query(models_representation.RepresentationServiceVersion).filter_by(
        id=version_id, service_id=service_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    db.query(models_representation.RepresentationServiceVersion).filter(
        models_representation.RepresentationServiceVersion.service_id == service_id,
        models_representation.RepresentationServiceVersion.status == "PUBLISHED",
        models_representation.RepresentationServiceVersion.id != version_id,
    ).update({"status": "ARCHIVED"})
    version.status = "PUBLISHED"
    version.published_at = datetime.utcnow()
    db.commit()
    _audit(db, version.id, "version_published", f"Versão {version.version_label} publicada", current_user.id)
    db.commit()
    db.refresh(version)
    return version


@router.post("/render", response_model=RepresentationExecutionResponse)
def render(
    payload: RepresentationExecutionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    service = db.get(models_representation.RepresentationService, payload.service_id)
    if not service or not service.is_active:
        raise HTTPException(status_code=404, detail="Serviço de representação não encontrado ou inativo")
    version = db.get(models_representation.RepresentationServiceVersion, payload.version_id) if payload.version_id else None
    if version is None:
        version = db.query(models_representation.RepresentationServiceVersion).filter_by(
            service_id=service.id, status="PUBLISHED"
        ).first()
    if not version or version.service_id != service.id:
        raise HTTPException(status_code=409, detail="O serviço não possui versão publicada")

    execution = models_representation.RepresentationExecution(
        service_id=service.id,
        service_version_id=version.id,
        document_id=payload.document_id,
        input_xml_hash=_hash(payload.xml_content),
        requested_by_user_id=current_user.id,
        status="PENDING",
    )
    db.add(execution)
    try:
        transform = etree.XSLT(etree.XML(version.xslt_content.encode("utf-8"), parser=etree.XMLParser(resolve_entities=False, no_network=True)))
        result = str(transform(etree.XML(payload.xml_content.encode("utf-8"), parser=etree.XMLParser(resolve_entities=False, no_network=True))))
        execution.output_hash = _hash(result)
        execution.status = "SUCCEEDED"
        execution.completed_at = datetime.utcnow()
        db.commit()
        _audit(db, execution.id, "render_succeeded", f"Execução com versão {version.version_label}", current_user.id)
        db.commit()
    except (etree.XMLSyntaxError, etree.XSLTApplyError, etree.XSLTParseError) as exc:
        execution.status = "FAILED"
        execution.error_message = str(exc)
        execution.completed_at = datetime.utcnow()
        db.commit()
        _audit(db, execution.id, "render_failed", str(exc), current_user.id)
        db.commit()
        raise HTTPException(status_code=422, detail=f"Falha na representação visual: {exc}") from exc
    db.refresh(execution)
    response = RepresentationExecutionResponse.model_validate(execution)
    return response.model_copy(update={"html_content": result})


@router.get("/executions/{execution_id}", response_model=RepresentationExecutionResponse)
def get_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    execution = db.get(models_representation.RepresentationExecution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return execution
