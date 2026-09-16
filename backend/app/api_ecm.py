from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import json
from uuid import uuid4
from hashlib import sha256

from app.database import get_db
from app.models import User
router = APIRouter()
from app.models_ecm import Node, NodeAspect, NodeVersion, NodePermission, Tag, NodeTag, DashboardConfig, Site, SiteMember
from app.schemas_ecm import NodeCreate, NodeResponse, NodeVersionResponse, NodePropertiesResponse, NodePermissionUpdate, AspectAdd, TagCreate, TagResponse, PropertiesUpdate, DashboardConfigUpdate, DashboardConfigResponse
from app.auth import get_current_active_user
from app.services.retention_service import apply_temporality_rule
from app.storage import save_file
from app.storage import STORAGE_ROOT
from app.document_permissions import exigir_permissao
from app.models_ged_config import DocumentType

def check_node_permission(db, user, node_type, acao):
    tipo = db.get(DocumentType, node_type)
    if tipo:
        exigir_permissao(db, user, node_type, acao)


def _has_node_scope(db, user, node, permission):
    if user.role == "admin_global":
        return True
    all_grants = db.query(NodePermission).filter(NodePermission.node_id == node.id).all()
    if not all_grants:
        return True
    site_ids = {
        site_id for site_id, in db.query(SiteMember.site_id).filter(
            SiteMember.user_id == user.id
        ).all()
    }
    matching = [
        grant for grant in all_grants
        if grant.user_id == user.id or grant.site_id in site_ids
    ]
    return any(permission in (grant.permissions or []) for grant in matching)


def check_node_scope(db, user, node, permission):
    if not _has_node_scope(db, user, node, permission):
        raise HTTPException(status_code=403, detail="Node permission denied")


def _node_file_path(node):
    content = (node.properties or {}).get("cm:content") or {}
    stored_path = content.get("stored_path")
    if not stored_path:
        raise HTTPException(status_code=404, detail="File unavailable")
    path = Path(stored_path).resolve()
    if not path.is_file() or not path.is_relative_to(STORAGE_ROOT.resolve()):
        raise HTTPException(status_code=404, detail="File unavailable")
    return content, path


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

    check_node_permission(db, user, node_type, 'cadastrar')

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
        db.add(NodeVersion(
            node_id=node.id, major_version=1, minor_version=0,
            file_name=original_name, stored_path=stored_path,
            checksum=sha256(content).hexdigest(), size=len(content),
            mime_type=file.content_type, created_by=user.id,
        ))
        
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
    if user.role == "admin_instituicao" and user.institution_id != node.institution_id:
        raise HTTPException(status_code=403, detail="Node belongs to another institution")

    check_node_permission(db, user, node.node_type, 'editar')
    check_node_scope(db, user, node, "edit")

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
    db.add(NodeVersion(
        node_id=node.id, major_version=next_major, minor_version=next_minor,
        file_name=original_name, stored_path=stored_path,
        checksum=sha256(content).hexdigest(), size=len(content),
        mime_type=file.content_type, created_by=user.id,
    ))
    db.commit()
    db.refresh(node)
    return node


@router.get("/api/ecm/nodes/{node_id}/versions", response_model=List[NodeVersionResponse], tags=["ECM"])
def list_node_versions(
    node_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    node = db.query(Node).filter(
        Node.id == node_id,
        Node.institution_id == user.institution_id,
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    check_node_permission(db, user, node.node_type, "consultar")
    return db.query(NodeVersion).filter(
        NodeVersion.node_id == node.id
    ).order_by(NodeVersion.major_version.desc(), NodeVersion.minor_version.desc()).all()


@router.post("/api/ecm/nodes", response_model=NodeResponse, tags=["ECM"])
def create_node(
    payload: NodeCreate, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_active_user)
):
    # Base ECM Node creation
    check_node_permission(db, user, payload.node_type, 'cadastrar')
    
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
    tag: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    query = db.query(Node).filter(Node.institution_id == user.institution_id)
    if parent_id:
        query = query.filter(Node.parent_id == parent_id)
    if node_type:
        query = query.filter(Node.node_type == node_type)
    if tag:
        query = query.join(NodeTag, NodeTag.node_id == Node.id).join(
            Tag, Tag.id == NodeTag.tag_id
        ).filter(Tag.name.ilike(tag.strip())).distinct()
        
    nodes = query.all()
    return [
        node for node in nodes
        if _has_node_scope(db, user, node, "read")
    ]

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

    check_node_permission(db, user, node.node_type, 'editar')
    check_node_scope(db, user, node, "edit")

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
        
    check_node_permission(db, user, node.node_type, 'editar')
    check_node_scope(db, user, node, "edit")

    # Update properties dict
    new_props = node.properties.copy()
    new_props.update(payload.properties)
    node.properties = new_props
    
    db.commit()
    db.refresh(node)
    return node


@router.get("/api/ecm/nodes/{node_id}/properties", response_model=NodePropertiesResponse, tags=["ECM"])
def get_node_properties(
    node_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    node = db.query(Node).filter(
        Node.id == node_id,
        Node.institution_id == user.institution_id,
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    check_node_permission(db, user, node.node_type, "consultar")
    check_node_scope(db, user, node, "read")
    return {"node_id": node.id, "properties": node.properties or {}}


@router.get("/api/ecm/nodes/{node_id}/preview", tags=["ECM"])
def preview_node(
    node_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    node = db.query(Node).filter(
        Node.id == node_id,
        Node.institution_id == user.institution_id,
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    check_node_permission(db, user, node.node_type, "consultar")
    check_node_scope(db, user, node, "read")
    content, path = _node_file_path(node)
    return FileResponse(
        path,
        media_type=content.get("mime_type") or "application/octet-stream",
        content_disposition_type="inline",
        filename=content.get("file_name") or node.name,
    )


@router.get("/api/ecm/nodes/{node_id}/download", tags=["ECM"])
def download_node(
    node_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    node = db.query(Node).filter(
        Node.id == node_id,
        Node.institution_id == user.institution_id,
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    check_node_permission(db, user, node.node_type, "consultar")
    check_node_scope(db, user, node, "download")
    content, path = _node_file_path(node)
    return FileResponse(
        path,
        media_type=content.get("mime_type") or "application/octet-stream",
        content_disposition_type="attachment",
        filename=content.get("file_name") or node.name,
    )


@router.put("/api/ecm/nodes/{node_id}/permissions", tags=["ECM Permissions"])
def update_node_permissions(
    node_id: str,
    payload: NodePermissionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    node_query = db.query(Node).filter(Node.id == node_id)
    if user.role != "admin_global":
        node_query = node_query.filter(Node.institution_id == user.institution_id)
    node = node_query.first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if payload.site_id:
        site = db.query(Site).filter(
            Site.id == payload.site_id,
            Site.institution_id == node.institution_id,
        ).first()
        if site is None:
            raise HTTPException(status_code=422, detail="Site does not belong to the node institution")
    if user.role not in {"admin_global", "admin_instituicao"}:
        member = None
        if payload.site_id:
            member = db.query(SiteMember).filter(
                SiteMember.site_id == payload.site_id,
                SiteMember.user_id == user.id,
                SiteMember.role == "SiteManager",
            ).first()
        if member is None:
            raise HTTPException(status_code=403, detail="Only global admins or SiteManagers can manage node permissions")
    if (payload.user_id is None) == (payload.site_id is None):
        raise HTTPException(status_code=422, detail="Informe user_id ou site_id, mas não ambos.")
    if payload.user_id:
        target = db.query(User).filter(User.id == payload.user_id).first()
        if target is None:
            raise HTTPException(status_code=422, detail="Usuário não encontrado.")
        if target.institution_id != node.institution_id:
            raise HTTPException(status_code=422, detail="Usuário pertence a outra instituição.")
    allowed = {"read", "edit", "download", "share"}
    if not set(payload.permissions).issubset(allowed):
        raise HTTPException(status_code=422, detail="Permissão de nó inválida.")
    query = db.query(NodePermission).filter(NodePermission.node_id == node.id)
    if payload.user_id:
        query = query.filter(NodePermission.user_id == payload.user_id)
    else:
        query = query.filter(NodePermission.site_id == payload.site_id)
    grant = query.first()
    if grant is None:
        grant = NodePermission(
            node_id=node.id,
            user_id=payload.user_id,
            site_id=payload.site_id,
            permissions=sorted(set(payload.permissions)),
        )
        db.add(grant)
    else:
        grant.permissions = sorted(set(payload.permissions))
    db.commit()
    return {
        "node_id": node.id,
        "user_id": grant.user_id,
        "site_id": grant.site_id,
        "permissions": grant.permissions,
    }

@router.get("/api/ecm/tags", response_model=List[TagResponse], tags=["ECM Tags"])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).join(NodeTag, NodeTag.tag_id == Tag.id).join(
        Node, Node.id == NodeTag.node_id
    ).distinct().order_by(Tag.name).all()

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
        
    check_node_permission(db, user, node.node_type, 'editar')
    check_node_scope(db, user, node, "edit")

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
        
    check_node_permission(db, user, node.node_type, 'editar')
    check_node_scope(db, user, node, "edit")

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
