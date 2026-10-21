import sys
import os
import json

# Ajustar path para importar módulos da app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models_workflow import Workflow, WorkflowState, WorkflowTransition
import app.models_academic_dossier
import app.models_ged

DOCUMENTS_TO_CHECK = [
    "Termo de Responsabilidade",
    "Documento Pessoal - Identidade",
    "Documento Pessoal - CPF",
    "Histórico Escolar da Graduação",
    "Diploma Digital (Oficial)"
]

def create_seed():
    db = SessionLocal()
    
    # 1. Create Workflow
    workflow_name = "Processo Emissão Diploma Oficial"
    internal_name = "diploma_oficial_v1"
    
    existing = db.query(Workflow).filter_by(internal_name=internal_name).first()
    if existing:
        print(f"Workflow '{internal_name}' já existe. Excluindo anterior para recriar...")
        db.delete(existing)
        db.commit()
        
    wf = Workflow(name=workflow_name, internal_name=internal_name, is_active=True)
    db.add(wf)
    db.flush()
    
    print(f"Workflow ID criado: {wf.id}")

    # Layout vars
    ui_x = 100
    ui_y_base = 200
    ui_step = 200
    
    # Create Start State
    start_state = WorkflowState(
        workflow_id=wf.id,
        label="Início do Processo",
        is_initial=True,
        swimlane="secretaria",
        node_type="start",
        ui_pos_x=ui_x,
        ui_pos_y=ui_y_base
    )
    db.add(start_state)
    db.flush()
    
    current_source_state = start_state
    ui_x += ui_step

    # Generate document checks
    for idx, doc in enumerate(DOCUMENTS_TO_CHECK):
        print(f"Gerando check para: {doc}")
        
        # 1. Busca (Service Task)
        busca_state = WorkflowState(
            workflow_id=wf.id,
            label=f"Busca: {doc}",
            swimlane="sistema",
            node_type="service_task",
            config_json=json.dumps({"api_endpoint": f"/api/ged/busca?doc={doc}&user=<email>"}),
            ui_pos_x=ui_x,
            ui_pos_y=ui_y_base
        )
        db.add(busca_state)
        db.flush()
        
        # Link from previous to Busca
        db.add(WorkflowTransition(
            workflow_id=wf.id, origin_state_id=current_source_state.id, destination_state_id=busca_state.id,
            label="Avançar", is_default=True
        ))
        ui_x += ui_step
        
        # 2. Gateway
        gateway_state = WorkflowState(
            workflow_id=wf.id,
            label=f"{doc} encontrado?",
            swimlane="sistema",
            node_type="gateway",
            ui_pos_x=ui_x,
            ui_pos_y=ui_y_base
        )
        db.add(gateway_state)
        db.flush()
        
        # Link from Busca to Gateway
        db.add(WorkflowTransition(
            workflow_id=wf.id, origin_state_id=busca_state.id, destination_state_id=gateway_state.id,
            label="Analisar"
        ))
        
        # 3. Vincular (Service Task - Sim)
        vincular_state = WorkflowState(
            workflow_id=wf.id,
            label=f"Vincular: {doc}",
            swimlane="sistema",
            node_type="service_task",
            config_json=json.dumps({"api_endpoint": f"/api/ged/vincular?doc={doc}"}),
            ui_pos_x=ui_x + ui_step,
            ui_pos_y=ui_y_base - 100
        )
        db.add(vincular_state)
        db.flush()
        
        # 4. Rebusca / Notificar (Manual Task - Não)
        rebusca_state = WorkflowState(
            workflow_id=wf.id,
            label=f"Pendente: {doc}",
            swimlane="secretaria",
            node_type="user_task",
            config_json=json.dumps({"notificar": "sim", "msg": f"Anexar {doc} para <nome>.", "task_form": "anexar_pendencia"}),
            ui_pos_x=ui_x,
            ui_pos_y=ui_y_base + 150
        )
        db.add(rebusca_state)
        db.flush()
        
        # Links from Gateway
        db.add(WorkflowTransition(
            workflow_id=wf.id, origin_state_id=gateway_state.id, destination_state_id=vincular_state.id,
            label="Sim", condition_key="encontrado", condition_value="true", priority=1
        ))
        db.add(WorkflowTransition(
            workflow_id=wf.id, origin_state_id=gateway_state.id, destination_state_id=rebusca_state.id,
            label="Não", is_default=True, priority=0
        ))
        
        # Link from Rebusca back to Gateway (loop to check again once fixed)
        db.add(WorkflowTransition(
            workflow_id=wf.id, origin_state_id=rebusca_state.id, destination_state_id=busca_state.id,
            label="Verificar Novamente", is_default=True
        ))
        
        # Set current source state for the next document in loop (it continues from Vincular)
        current_source_state = vincular_state
        ui_x += ui_step * 2

    # End State
    end_state = WorkflowState(
        workflow_id=wf.id,
        label="Dossiê de Diplomação Concluído",
        is_completion=True,
        swimlane="secretaria",
        node_type="end",
        ui_pos_x=ui_x,
        ui_pos_y=ui_y_base
    )
    db.add(end_state)
    db.flush()
    
    # Link last Vincular to End
    db.add(WorkflowTransition(
        workflow_id=wf.id, origin_state_id=current_source_state.id, destination_state_id=end_state.id,
        label="Finalizar Dossiê", is_default=True
    ))

    db.commit()
    print("Workflow gigante gerado com sucesso no banco de dados!")
    db.close()

if __name__ == "__main__":
    create_seed()
