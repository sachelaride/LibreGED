import sys
import os
import json

# Ajustar path para importar módulos da app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app import models
from app import models_ged
from app import models_ged_config
from app import models_academic_dossier
from app import models_workflow
from app import models_representation

# Definição dos Índices
INDICES_DEF = [
    {"name": "CPF", "type": "Caractere", "mask": "000.000.000-00"},
    {"name": "Nome do Aluno", "type": "Caractere", "mask": None},
    {"name": "Curso", "type": "Caractere", "mask": None},
    {"name": "Ano de Conclusão", "type": "Número", "mask": None},
]

# Definição dos Tipos Documentais
DOCUMENT_TYPES_DEF = [
    {
        "name": "Termo de Responsabilidade",
        "retention_years": 5,
        "signature_rule": {"required": True, "type": "ICP-Brasil"},
        "indices": ["CPF", "Nome do Aluno", "Matrícula"]
    },
    {
        "name": "Histórico Escolar da Graduação",
        "retention_years": 100, # Permanente
        "signature_rule": {"required": True, "type": "ICP-Brasil"},
        "indices": ["CPF", "Nome do Aluno", "Curso", "Ano de Conclusão"]
    },
    {
        "name": "Diploma Digital (Oficial)",
        "retention_years": 100,
        "signature_rule": {"required": True, "type": "MEC_RNP"},
        "indices": ["CPF", "Nome do Aluno", "Curso", "Ano de Conclusão"]
    }
]

def create_catalog_seed():
    db = SessionLocal()
    
    print("Semeando Índices Globais...")
    index_map = {}
    for idx_def in INDICES_DEF:
        idx_obj = db.query(models_ged_config.GedIndex).filter_by(name=idx_def["name"]).first()
        if not idx_obj:
            idx_obj = models_ged_config.GedIndex(
                name=idx_def["name"],
                type=idx_def["type"],
                mask=idx_def["mask"]
            )
            db.add(idx_obj)
            db.flush()
        index_map[idx_def["name"]] = idx_obj
    
    print("Semeando Tipos Documentais da Diplomação...")
    group_id = "diplomacao_graduacao"
    
    for dt_def in DOCUMENT_TYPES_DEF:
        dt_name = dt_def["name"]
        dt_obj = db.query(models_ged_config.DocumentType).filter_by(name=dt_name).first()
        
        if not dt_obj:
            dt_obj = models_ged_config.DocumentType(
                name=dt_name,
                group_id=group_id,
                retention_years=dt_def["retention_years"],
                signature_rule=dt_def["signature_rule"],
                access_policy={"visibility": "institutional"}
            )
            db.add(dt_obj)
            db.flush()
            
            # Vínculo com os índices
            for index_name in dt_def["indices"]:
                index_id = index_map[index_name].id
                link = models_ged_config.DocumentTypeIndex(
                    document_type_id=dt_obj.id,
                    index_id=index_id,
                    is_required=True
                )
                db.add(link)
            print(f" [+] Criado: {dt_name}")
        else:
            print(f" [=] Já existente: {dt_name}")
            
    db.commit()
    print("Catálogo de Documentos semeado com sucesso!")
    db.close()

if __name__ == "__main__":
    create_catalog_seed()
