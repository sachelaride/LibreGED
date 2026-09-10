from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import json
from uuid import uuid4
from hashlib import sha256

from app.database import get_db
from app.models import User
router = APIRouter()
from app.models_ecm import Node, NodeAspect, Tag, NodeTag, DashboardConfig, SiteMember
from app.schemas_ecm import NodeCreate, NodeResponse, AspectAdd, TagCreate, TagResponse, PropertiesUpdate, DashboardConfigUpdate, DashboardConfigResponse
from app.auth import get_current_active_user
from app.services.retention_service import apply_temporality_rule
from app.storage import save_file


@router.post("/api/ecm/nodes/upload", response_model=List[NodeResponse], tags=["ECM"])
def upload_nodes(
    files: List[UploadFile] = File(...),
    node_type: str = Form(...),
    properties: str = Form("{}"), # JSON string
    parent_id: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    try:
        props_dict = json.loads(properties)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid properties JSON")

    uploaded_nodes = []
    
    for file in files:
        # Ler conteúdo do arquivo
        content = file.file.read()
        original_name = file.filename or "unnamed_file"
        version_id = str(uuid4())
        
        # Gerar IDs com antecedência para construir a referência no banco
        node_id_temp = str(uuid4()) 
        
        # Salvar no storage fisico
        stored_path = save_file(f"{node_id_temp}-v1.0-{version_id}-{original_name}", content, db=db)
        
        # Criar nó ECM
        node = Node(
            id=node_id_temp,
            node_type=node_type,
            name=original_name,
            properties=props_dict.copy(),
            parent_id=parent_id,
            major_version=1,
            minor_version=0,
            institution_id=user.institution_id,
            created_by=user.id
        )
        
        # Adicionar metadados do arquivo nas propriedades (simulando aspecto cm:content)
        node.properties["cm:content"] = {
            "stored_path": stored_path,
            "file_name": original_name,
            "size": len(content),
            "mime_type": file.content_type,
            "checksum": sha256(content).hexdigest()
        }

        db.add(node)
        
        # Adicionar o aspecto de conteúdo físico explicitamente
        aspect = NodeAspect(node_id=node.id, aspect_name="cm:content")
        db.add(aspect)
        
        # Regra de temporalidade
        if node_type == "ies:documento_graduacao":
            codigo_serie = props_dict.get("ies:codigo_serie")
            if codigo_serie:
                apply_temporality_rule(node, codigo_serie, db)
                
        uploaded_nodes.append(node)
        
    db.commit()
    
    for node in uploaded_nodes:
        db.refresh(node)
        
    return uploaded_nodes


@router.post("/api/ecm/nodes/{node_id}/versions", response_model=NodeResponse, tags=["ECM"])
def upload_node_version(
    node_id: str,
    file: UploadFile = File(...),
    version_type: str = Form("minor"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    if version_type not in {"major", "minor"}:
        raise HTTPException(status_code=400, detail="version_type must be major or minor")

    node = db.query(Node).filter(
        Node.id == node_id,
        Node.institution_id == user.institution_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Version file cannot be empty")

    if version_type == "major":
        next_major = node.major_version + 1
        next_minor = 0
    else:
        next_major = node.major_version
        next_minor = node.minor_version + 1

    original_name = Path(file.filename or node.name).name
    version_id = str(uuid4())
    stored_path = save_file(
        f"{node.id}-v{next_major}.{next_minor}-{version_id}-{original_name}",
        content,
        db=db
    )

    properties = dict(node.properties or {})
    properties["cm:content"] = {
        "stored_path": stored_path,
        "file_name": original_name,
        "size": len(content),
        "mime_type": file.content_type,
        "checksum": sha256(content).hexdigest()
    }

    node.major_version = next_major
    node.minor_version = next_minor
    node.properties = properties
    db.commit()
    db.refresh(node)
    return node


@router.post("/api/ecm/nodes", response_model=NodeResponse, tags=["ECM"])
def create_node(
    payload: NodeCreate, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_active_user)
):
    # Base ECM Node creation
    node = Node(
        node_type=payload.node_type,
        name=payload.name,
        properties=payload.properties,
        parent_id=payload.parent_id,
        institution_id=user.institution_id,
        created_by=user.id
    )
    db.add(node)
    
    # Se for um documento acadêmico, aplicamos as regras da Matriz do MEC
    if payload.node_type == "ies:documento_graduacao":
        codigo_serie = payload.properties.get("ies:codigo_serie")
        if codigo_serie:
            apply_temporality_rule(node, codigo_serie, db)
            
    db.commit()
    db.refresh(node)
    return node

@router.get("/api/ecm/nodes", response_model=List[NodeResponse], tags=["ECM"])
def list_nodes(
    parent_id: str = None,
    node_type: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    query = db.query(Node).filter(Node.institution_id == user.institution_id)
    if parent_id:
        query = query.filter(Node.parent_id == parent_id)
    if node_type:
        query = query.filter(Node.node_type == node_type)
        
    return query.all()

@router.post("/api/ecm/nodes/{node_id}/aspects", response_model=NodeResponse, tags=["ECM"])
def add_aspect(
    node_id: str,
    payload: AspectAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    node = db.query(Node).filter(Node.id == node_id, Node.institution_id == user.institution_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    aspect = db.query(NodeAspect).filter_by(node_id=node.id, aspect_name=payload.aspect_name).first()
    if not aspect:
        aspect = NodeAspect(node_id=node.id, aspect_name=payload.aspect_name)
        db.add(aspect)
        db.commit()
        db.refresh(node)
    return node

@router.put("/api/ecm/nodes/{node_id}/properties", response_model=NodeResponse, tags=["ECM"])
def update_node_properties(
    node_id: str,
    payload: PropertiesUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    node = db.query(Node).filter(Node.id == node_id, Node.institution_id == user.institution_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    # Update properties dict
    new_props = node.properties.copy()
    new_props.update(payload.properties)
    node.properties = new_props
    
    db.commit()
    db.refresh(node)
    return node

@router.get("/api/ecm/tags", response_model=List[TagResponse], tags=["ECM Tags"])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).all()

@router.post("/api/ecm/tags", response_model=TagResponse, tags=["ECM Tags"])
def create_tag(payload: TagCreate, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.name == payload.name).first()
    if not tag:
        tag = Tag(name=payload.name)
        db.add(tag)
        db.commit()
        db.refresh(tag)
    return tag

@router.post("/api/ecm/nodes/{node_id}/tags", response_model=NodeResponse, tags=["ECM Tags"])
def add_node_tag(
    node_id: str,
    payload: TagCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    node = db.query(Node).filter(Node.id == node_id, Node.institution_id == user.institution_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    # Get or create tag
    tag = db.query(Tag).filter(Tag.name == payload.name).first()
    if not tag:
        tag = Tag(name=payload.name)
        db.add(tag)
        db.commit()
    
    # Check if already tagged
    node_tag = db.query(NodeTag).filter_by(node_id=node.id, tag_id=tag.id).first()
    if not node_tag:
        node_tag = NodeTag(node_id=node.id, tag_id=tag.id)
        db.add(node_tag)
        db.commit()
        
    db.refresh(node)
    return node

@router.delete("/api/ecm/nodes/{node_id}/tags/{tag_id}", tags=["ECM Tags"])
def remove_node_tag(
    node_id: str,
    tag_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    node = db.query(Node).filter(Node.id == node_id, Node.institution_id == user.institution_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node_tag = db.query(NodeTag).filter_by(node_id=node.id, tag_id=tag_id).first()
    if node_tag:
        db.delete(node_tag)
        db.commit()
        
    return {"message": "Tag removed successfully"}

@router.get("/api/ecm/dashboards/{owner_type}/{owner_id}", response_model=DashboardConfigResponse, tags=["ECM Dashboards"])
def get_dashboard(
    owner_type: str,
    owner_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    owner_type = owner_type.upper()
    if owner_type not in ["USER", "SITE"]:
        raise HTTPException(status_code=400, detail="owner_type must be USER or SITE")
        
    # Validar Acesso
    if owner_type == "USER" and owner_id != user.id and user.role != "admin_global":
        raise HTTPException(status_code=403, detail="Cannot read another user's dashboard")
        
    if owner_type == "SITE" and user.role != "admin_global":
        member = db.query(SiteMember).filter_by(site_id=owner_id, user_id=user.id).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this site")
            
    config = db.query(DashboardConfig).filter_by(owner_type=owner_type, owner_id=owner_id).first()
    if not config:
        # Retornar default se não existir
        config = DashboardConfig(
            id=str(uuid.uuid4()),
            owner_type=owner_type,
            owner_id=owner_id,
            layout_json={"layout": "default", "columns": []}
        )
        # We don't save the default in DB to save space, just return it
        return config
    return config

@router.put("/api/ecm/dashboards/{owner_type}/{owner_id}", response_model=DashboardConfigResponse, tags=["ECM Dashboards"])
def update_dashboard(
    owner_type: str,
    owner_id: str,
    payload: DashboardConfigUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    owner_type = owner_type.upper()
    if owner_type not in ["USER", "SITE"]:
        raise HTTPException(status_code=400, detail="owner_type must be USER or SITE")
        
    # Validar Acesso de Edição
    if owner_type == "USER" and owner_id != user.id and user.role != "admin_global":
        raise HTTPException(status_code=403, detail="Cannot edit another user's dashboard")
        
    if owner_type == "SITE" and user.role != "admin_global":
        member = db.query(SiteMember).filter_by(site_id=owner_id, user_id=user.id).first()
        if not member or member.role != "SiteManager":
            raise HTTPException(status_code=403, detail="Only SiteManagers can edit site dashboards")
            
    config = db.query(DashboardConfig).filter_by(owner_type=owner_type, owner_id=owner_id).first()
    if not config:
        config = DashboardConfig(
            id=str(uuid.uuid4()),
            owner_type=owner_type,
            owner_id=owner_id,
            layout_json=payload.layout_json
        )
        db.add(config)
    else:
        config.layout_json = payload.layout_json
        
    db.commit()
    db.refresh(config)
    return config
