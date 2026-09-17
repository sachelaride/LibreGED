import os
import sys

# Ajustar o caminho para rodar a partir do backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import SessionLocal
from app.models_ged_config import DocumentType, DocumentTypeVersion, DocumentTypeIndex, GedIndex
from app import models
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

def get_or_create_document_type(db, name: str, indices_map: list):
    doc_type = db.query(DocumentType).filter_by(name=name).first()
    if not doc_type:
        doc_type = DocumentType(
            id=str(uuid.uuid4()),
            name=name,
            is_active=True,
            # Placeholder, in a real system this would map to a known workflow ID if applicable
            workflow_id=None,
            # We enforce grouping for academic dossiers, using a convention
            group_id="acad_dossier", 
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
        idx_cod_mec = get_or_create_index(db, "Código e-MEC do Curso", "Caractere")
        idx_data_emissao = get_or_create_index(db, "Data de Emissão", "Data")
        idx_curso = get_or_create_index(db, "Curso", "Caractere")
        idx_processo = get_or_create_index(db, "Número do Processo", "Caractere")
        
        print("Criando Tipos Documentais Acadêmicos MEC...")
        
        # 1. Diploma Digital
        get_or_create_document_type(db, "Diploma Digital", [
            {"index": idx_cpf, "is_required": True, "is_unique": False},
            {"index": idx_nome, "is_required": True, "is_unique": False},
            {"index": idx_data_emissao, "is_required": True, "is_unique": False},
            {"index": idx_cod_mec, "is_required": True, "is_unique": False},
        ])
        
        # 2. Histórico Escolar Digital
        get_or_create_document_type(db, "Histórico Escolar Digital", [
            {"index": idx_cpf, "is_required": True, "is_unique": False},
            {"index": idx_rgm, "is_required": True, "is_unique": False},
            {"index": idx_nome, "is_required": True, "is_unique": False},
            {"index": idx_curso, "is_required": True, "is_unique": False},
        ])
        
        # 3. Currículo Escolar Digital
        get_or_create_document_type(db, "Currículo Escolar Digital", [
            {"index": idx_cod_mec, "is_required": True, "is_unique": False},
            {"index": idx_curso, "is_required": True, "is_unique": False},
        ])
        
        # 4. RVDD (Registro Visual do Diploma Digital)
        get_or_create_document_type(db, "RVDD (Documentação Acadêmica)", [
            {"index": idx_cpf, "is_required": True, "is_unique": False},
            {"index": idx_nome, "is_required": True, "is_unique": False},
            {"index": idx_processo, "is_required": True, "is_unique": False},
        ])
        
        # 5. Arquivo de Fiscalização e Lista de Anulados
        get_or_create_document_type(db, "Arquivo de Fiscalização", [
            {"index": idx_cod_mec, "is_required": True, "is_unique": False},
        ])
        get_or_create_document_type(db, "Lista de Diplomas Anulados", [
            {"index": idx_cod_mec, "is_required": True, "is_unique": False},
            {"index": idx_data_emissao, "is_required": True, "is_unique": False},
        ])
        
        print("Carga dos tipos acadêmicos MEC finalizada com sucesso!")

    except Exception as e:
        db.rollback()
        print(f"Erro na criação do seed acadêmico: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()
