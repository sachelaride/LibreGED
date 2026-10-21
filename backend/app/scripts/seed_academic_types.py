import os
import sys

# Ajustar o caminho para rodar a partir do backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import SessionLocal
from app.models_ged_config import DocumentType, DocumentTypeVersion, DocumentTypeIndex, GedIndex
from app import models
from app import models_ged
from app import models_workflow
from app import models_academic_dossier
import uuid

def get_or_create_index(db, name: str, type_: str, options: list = None, mask: str = None):
    index = db.query(GedIndex).filter_by(name=name).first()
    if not index:
        index = GedIndex(
            id=str(uuid.uuid4()),
            name=name,
            type=type_,
            options=options or [],
            mask=mask,
            is_active=True
        )
        db.add(index)
        db.commit()
        db.refresh(index)
    return index

def get_or_create_document_type(db, name: str, indices_map: list, group_id: str = "acad_dossier"):
    doc_type = db.query(DocumentType).filter_by(name=name).first()
    if not doc_type:
        doc_type = DocumentType(
            id=str(uuid.uuid4()),
            name=name,
            is_active=True,
            # Placeholder, in a real system this would map to a known workflow ID if applicable
            workflow_id=None,
            # We enforce grouping for academic dossiers, using a convention
            group_id=group_id,
            retention_years=5,
            legal_hold=False,
            active_version=1
        )
        db.add(doc_type)
        db.commit()
        
        # Version 1
        version = DocumentTypeVersion(
            id=str(uuid.uuid4()),
            document_type_id=doc_type.id,
            version=1,
            status="ACTIVE",
            name=doc_type.name,
            retention_years=doc_type.retention_years,
            legal_hold=doc_type.legal_hold,
            effective_from=models.utc_now()
        )
        db.add(version)
        db.commit()
        db.refresh(doc_type)
        
        # Link Indices
        for idx_info in indices_map:
            index_obj = idx_info["index"]
            is_required = idx_info.get("is_required", True)
            is_unique = idx_info.get("is_unique", False)
            link = DocumentTypeIndex(
                id=str(uuid.uuid4()),
                document_type_id=doc_type.id,
                index_id=index_obj.id,
                is_required=is_required,
                is_unique=is_unique
            )
            db.add(link)
        db.commit()
        
    return doc_type

def run():
    db = SessionLocal()
    try:
        print("Criando índices base...")
        idx_cpf = get_or_create_index(db, "CPF", "Caractere", mask="###.###.###-##")
        idx_nome = get_or_create_index(db, "Nome", "Caractere")
        idx_rgm = get_or_create_index(db, "RGM / Matrícula", "Caractere")
        idx_rg = get_or_create_index(db, "RG", "Caractere")

        print("Criando tipos essenciais de documentos pessoais...")
        get_or_create_document_type(db, "Documento Pessoal - Identidade", [
            {"index": idx_nome, "is_required": True},
            {"index": idx_rg, "is_required": True},
            {"index": idx_cpf, "is_required": True},
            {"index": idx_rgm, "is_required": False},
        ], group_id="pessoal")
        get_or_create_document_type(db, "Documento Pessoal - CPF", [
            {"index": idx_nome, "is_required": True},
            {"index": idx_cpf, "is_required": True},
        ], group_id="pessoal")

        print("Carga dos tipos pessoais essenciais finalizada com sucesso!")

    except Exception as e:
        db.rollback()
        print(f"Erro na criação do seed acadêmico: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()
