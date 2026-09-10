import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models import Base, utc_now

class Node(Base):
    __tablename__ = "ecm_nodes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    node_type = Column(String, nullable=False, index=True) # e.g., 'cm:folder', 'ies:documento_graduacao'
    parent_id = Column(String, ForeignKey("ecm_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String, nullable=False, index=True)
    
    # Store all dynamic metadata
    properties = Column(JSONB, default=dict, nullable=False) 
    
    institution_id = Column(String, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    created_by = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    # Versioning
    major_version = Column(Integer, default=1, nullable=False)
    minor_version = Column(Integer, default=0, nullable=False)

    # Relationships
    children = relationship("Node", backref=__tablename__ + "_parent", remote_side=[id])
    aspects = relationship("NodeAspect", back_populates="node", cascade="all, delete-orphan")
    tags = relationship("NodeTag", back_populates="node", cascade="all, delete-orphan")


class NodeAspect(Base):
    __tablename__ = "ecm_node_aspects"
    
    node_id = Column(String, ForeignKey("ecm_nodes.id", ondelete="CASCADE"), primary_key=True)
    aspect_name = Column(String, primary_key=True) # e.g., 'ies:temporalidade', 'ies:lote_conversao'
    
    node = relationship("Node", back_populates="aspects")


class Tag(Base):
    __tablename__ = "ecm_tags"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)


class NodeTag(Base):
    __tablename__ = "ecm_node_tags"
    
    node_id = Column(String, ForeignKey("ecm_nodes.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(String, ForeignKey("ecm_tags.id", ondelete="CASCADE"), primary_key=True)
    
    node = relationship("Node", back_populates="tags")
    tag = relationship("Tag")

class Site(Base):
    __tablename__ = "ecm_sites"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True) # URL slug
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    visibility = Column(String, default="PUBLIC") # PUBLIC, MODERATED, PRIVATE
    
    institution_id = Column(String, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    created_by = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    members = relationship("SiteMember", back_populates="site", cascade="all, delete-orphan")

class SiteMember(Base):
    __tablename__ = "ecm_site_members"
    
    site_id = Column(String, ForeignKey("ecm_sites.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String, nullable=False) # SiteManager, SiteCollaborator, SiteContributor, SiteConsumer
    
    site = relationship("Site", back_populates="members")
    
    # We don't necessarily need a back_populates to User unless we want to query User.sites

class DashboardConfig(Base):
    __tablename__ = "ecm_dashboard_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_type = Column(String, nullable=False, index=True) # "USER" or "SITE"
    owner_id = Column(String, nullable=False, index=True)
    layout_json = Column(JSONB, nullable=False, default=dict)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class DynamicAspect(Base):
    __tablename__ = "ecm_dynamic_aspects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True) # e.g. "custom:financeiro"
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    institution_id = Column(String, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=True) # None = global
    
    created_at = Column(DateTime, default=utc_now)
    
    properties_def = relationship("DynamicProperty", back_populates="aspect", cascade="all, delete-orphan")


class DynamicProperty(Base):
    __tablename__ = "ecm_dynamic_properties"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    aspect_id = Column(String, ForeignKey("ecm_dynamic_aspects.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String, nullable=False) # e.g. "custom:valor_nota"
    title = Column(String, nullable=False)
    data_type = Column(String, nullable=False) # string, integer, float, date, boolean, json
    required = Column(Boolean, default=False)
    multiple = Column(Boolean, default=False)
    options_json = Column(JSONB, nullable=True) # for select/dropdowns
    
    aspect = relationship("DynamicAspect", back_populates="properties_def")
