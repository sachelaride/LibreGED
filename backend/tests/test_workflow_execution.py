import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_current_active_user
from app.database import SessionLocal
from app import models
from app import models_workflow
from app import models_ged
from app.models_ged_config import DocumentType
from scripts.seed_diploma_workflow import create_seed

cliente = TestClient(app)

def test_seed_diploma_workflow_creates_expected_nodes_and_swimlanes():
    """Valida se o workflow oficial de diplomação semeado possui estados, raias e transições."""
    create_seed()
    with SessionLocal() as db:
        wf = db.query(models_workflow.Workflow).filter_by(internal_name="diploma_oficial_v1").first()
        assert wf is not None, "Workflow diploma_oficial_v1 deve existir no banco"
        assert wf.is_active is True
        
        states = db.query(models_workflow.WorkflowState).filter_by(workflow_id=wf.id).all()
        assert len(states) >= 15, f"Esperado pelo menos 15 estados no fluxo de diplomação, encontrados {len(states)}"
        
        # Valida raias (swimlanes)
        initial_state = next((s for s in states if s.is_initial), None)
        assert initial_state is not None
        assert initial_state.swimlane == "secretaria"
        
        # Valida que existem service tasks automatizadas
        service_tasks = [s for s in states if s.node_type in {"service_task", "task_service"}]
        assert len(service_tasks) >= 5, "Devem existir nós de service task para busca de documentos"
        
        # Valida nós com formulários de tarefas
        form_tasks = [s for s in states if s.config and s.config.get("task_form")]
        assert len(form_tasks) >= 1, "Devem existir tarefas com formulário customizado"


def test_get_workflow_details_returns_states():
    with SessionLocal() as db:
        workflow = models_workflow.Workflow(
            name=f"Workflow Detalhe {uuid4().hex[:6]}",
            internal_name=f"workflow_detail_{uuid4().hex[:6]}",
        )
        db.add(workflow)
        db.flush()
        state = models_workflow.WorkflowState(
            workflow_id=workflow.id,
            label="Revisão",
            is_initial=True,
        )
        db.add(state)
        db.commit()
        workflow_id = workflow.id
        state_id = state.id

    response = cliente.get(f"/api/workflows/{workflow_id}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == workflow_id
    assert payload["states"][0]["id"] == state_id
    assert payload["states"][0]["is_initial"] is True


def test_workflow_start_instance_and_complete_task():
    """Valida a execução de ponta a ponta: início de instância, auto-execução de service tasks e conclusão de tarefa."""
    with SessionLocal() as db:
        # Usuário admin com permissão
        admin_user = db.query(models.User).filter_by(role="admin_global").first()
        if not admin_user:
            admin_user = models.User(id=str(uuid4()), username="admin_wf_test", hashed_password="pwd", role="admin_global")
            db.add(admin_user)
            db.commit()
            
        inst = db.query(models.Institution).first()
        if not inst:
            inst = models.Institution(id=str(uuid4()), name="Faculdade Teste", cnpj="00112233000199", legal_name="Faculdade Teste LTDA")
            db.add(inst)
            db.commit()

        # Cria tipo documental e categoria
        doc_type_name = f"Doc WF Test {uuid4().hex[:6]}"
        doc_type = DocumentType(name=doc_type_name, retention_years=5)
        db.add(doc_type)
        db.flush()
        db.add(models_ged.DocumentCategory(id=doc_type.id, name=doc_type.name))
        db.flush()
        
        doc = models_ged.GEDDocument(
            id=str(uuid4()),
            title="Documento para Workflow Teste",
            category_id=doc_type.id,
            institution_id=inst.id,
            status=models_ged.GEDDocumentStatus.PENDENTE_VALIDACAO,
            file_path="mock_path.pdf"
        )
        db.add(doc)

        # Cria workflow simples com Start -> ServiceTask -> UserTask -> End
        wf = models_workflow.Workflow(name=f"Workflow Teste Execucao {uuid4().hex[:6]}", internal_name=f"wf_test_{uuid4().hex[:6]}")
        db.add(wf)
        db.flush()

        s_start = models_workflow.WorkflowState(workflow_id=wf.id, label="Inicio", is_initial=True, node_type="start")
        s_service = models_workflow.WorkflowState(workflow_id=wf.id, label="Busca Automatica", node_type="service_task")
        s_user = models_workflow.WorkflowState(workflow_id=wf.id, label="Conferencia Secretaria", node_type="task", swimlane="secretaria")
        s_end = models_workflow.WorkflowState(workflow_id=wf.id, label="Concluido", is_completion=True, node_type="end")
        db.add_all([s_start, s_service, s_user, s_end])
        db.flush()

        t1 = models_workflow.WorkflowTransition(workflow_id=wf.id, origin_state_id=s_start.id, destination_state_id=s_service.id, label="Avancar", is_default=True)
        t2 = models_workflow.WorkflowTransition(workflow_id=wf.id, origin_state_id=s_service.id, destination_state_id=s_user.id, label="Para Conferencia", is_default=True)
        t3 = models_workflow.WorkflowTransition(workflow_id=wf.id, origin_state_id=s_user.id, destination_state_id=s_end.id, label="Aprovar", action_code="APROVAR", is_default=True)
        db.add_all([t1, t2, t3])
        db.commit()
        
        wf_id = wf.id
        doc_id = doc.id
        s_start_id = s_start.id
        s_user_id = s_user.id
        s_end_id = s_end.id
        admin_id = admin_user.id

    # Sobrescreve usuário autenticado
    app.dependency_overrides[get_current_active_user] = lambda: admin_user

    try:
        # Iniciar instância no nó Start
        resp = cliente.post("/api/workflows/instances", json={
            "document_id": doc_id,
            "workflow_id": wf_id,
            "current_state_id": s_start_id
        })
        assert resp.status_code == 200, f"Erro ao iniciar workflow: {resp.text}"
        inst_data = resp.json()
        assert inst_data["document_id"] == doc_id
        
        # O nó Start gera uma tarefa inicial pendente para o iniciador
        with SessionLocal() as db:
            tasks = db.query(models_workflow.WorkflowTask).filter_by(instance_id=inst_data["id"]).all()
            start_task = next((t for t in tasks if t.name == "Inicio" and t.status == "PENDING"), None)
            assert start_task is not None, "Tarefa inicial do nó Start deve estar PENDING"
            start_task_id = start_task.id

        # Avança a partir do nó Start
        resp_advance = cliente.put(f"/api/workflows/tasks/{start_task_id}/complete", json={
            "action": "Avancar",
            "comment": "Iniciando processamento."
        })
        assert resp_advance.status_code == 200, f"Erro ao avançar do start: {resp_advance.text}"

        # Agora a service_task (Busca Automatica) deve ter sido auto-executada e avançado para s_user (Conferencia Secretaria)!
        with SessionLocal() as db:
            instance_db = db.get(models_workflow.DocumentWorkflowInstance, inst_data["id"])
            assert instance_db.current_state_id == s_user_id, "A service_task deve ter sido auto-executada avançando para s_user"
            
            # Checa tarefas geradas
            tasks = db.query(models_workflow.WorkflowTask).filter_by(instance_id=instance_db.id).all()
            completed_service = [t for t in tasks if t.name == "Busca Automatica" and t.status == "COMPLETED"]
            assert len(completed_service) == 1, "Service task deve estar marcada como COMPLETED"
            
            pending_user = [t for t in tasks if t.name == "Conferencia Secretaria" and t.status == "PENDING"]
            assert len(pending_user) == 1, "User task deve estar com status PENDING"
            pending_task_id = pending_user[0].id

        # Concluir a tarefa do usuário
        resp_complete = cliente.put(f"/api/workflows/tasks/{pending_task_id}/complete", json={
            "action": "APPROVE",
            "comment": "Tudo validado com sucesso."
        })
        assert resp_complete.status_code == 200, f"Erro ao completar tarefa: {resp_complete.text}"
        
        # Checa estado final e documento
        with SessionLocal() as db:
            instance_db = db.get(models_workflow.DocumentWorkflowInstance, inst_data["id"])
            assert instance_db.current_state_id == s_end_id, "Fluxo deve ter chegado ao estado final Concluido"
            
            doc_db = db.get(models_ged.GEDDocument, doc_id)
            assert doc_db.status == models_ged.GEDDocumentStatus.VALIDO, "Documento deve transicionar para VALIDO no nó final"

    finally:
        app.dependency_overrides.pop(get_current_active_user, None)
