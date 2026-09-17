"""Create the visual diploma workflow used by the BPMN editor."""

import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import SessionLocal
from app import models
from app import models_academic_dossier
from app import models_ged
from app import models_workflow


WORKFLOW_NAME = "Diploma Acadêmico - Emissão"
WORKFLOW_INTERNAL_NAME = "diploma-academico-emissao"


NODES = [
    ("inicio", "Início", "event_start", True, False, 80, 220),
    ("documentos", "Verificar documentos auxiliares", "task_service", False, False, 250, 220),
    ("documentos_ok", "Documentação completa?", "gateway_exclusive", False, False, 500, 220),
    ("solicitar", "Solicitar documentos pendentes", "task_user", False, False, 720, 80),
    ("aguardar", "Aguardar envio", "event_message", False, False, 940, 80),
    ("validar", "Validar dados acadêmicos", "task_service", False, False, 720, 360),
    ("dados_ok", "Dados válidos?", "gateway_exclusive", False, False, 940, 360),
    ("corrigir", "Corrigir dados acadêmicos", "task_user", False, False, 1160, 500),
    ("json", "Gerar JSON acadêmico", "task_script", False, False, 1160, 260),
    ("xml", "Gerar XML do diploma", "task_service", False, False, 1380, 260),
    ("xsd", "Validar XML contra XSD", "task_service", False, False, 1600, 260),
    ("xml_ok", "XML válido?", "gateway_exclusive", False, False, 1820, 260),
    ("rvdd", "Gerar representação visual RVDD", "task_service", False, False, 2040, 260),
    ("signatarios", "Selecionar signatários", "task_user", False, False, 2260, 260),
    ("assinar", "Assinar diploma", "task_user", False, False, 2480, 260),
    ("assinaturas_ok", "Todas as assinaturas concluídas?", "gateway_exclusive", False, False, 2700, 260),
    ("aguardar_assinatura", "Aguardar assinatura", "event_message", False, False, 2700, 500),
    ("evidencias", "Registrar hash e evidências", "task_service", False, False, 2920, 260),
    ("publicar", "Publicar diploma", "task_service", False, False, 3140, 260),
    ("fim", "Diploma finalizado", "event_end", False, True, 3360, 260),
]


EDGES = [
    ("inicio", "documentos", "Iniciar verificação", "START"),
    ("documentos", "documentos_ok", "Verificação concluída", "CHECK_DOCUMENTS"),
    ("documentos_ok", "solicitar", "Documentação pendente", "DOCUMENTS_PENDING"),
    ("solicitar", "aguardar", "Aguardar documentos", "WAIT_DOCUMENTS"),
    ("aguardar", "documentos", "Documentos recebidos", "DOCUMENTS_RECEIVED"),
    ("documentos_ok", "validar", "Documentação completa", "DOCUMENTS_COMPLETE"),
    ("validar", "dados_ok", "Validação concluída", "VALIDATE_ACADEMIC_DATA"),
    ("dados_ok", "corrigir", "Dados inválidos", "ACADEMIC_DATA_INVALID"),
    ("corrigir", "validar", "Dados corrigidos", "CORRECT_ACADEMIC_DATA"),
    ("dados_ok", "json", "Dados válidos", "ACADEMIC_DATA_VALID"),
    ("json", "xml", "JSON gerado", "GENERATE_DIPLOMA_JSON"),
    ("xml", "xsd", "XML gerado", "GENERATE_DIPLOMA_XML"),
    ("xsd", "xml_ok", "Validação XSD concluída", "VALIDATE_DIPLOMA_XSD"),
    ("xml_ok", "xml", "XML inválido", "XML_INVALID"),
    ("xml_ok", "rvdd", "XML válido", "XML_VALID"),
    ("rvdd", "signatarios", "RVDD gerado", "GENERATE_RVDD"),
    ("signatarios", "assinar", "Signatários selecionados", "SELECT_SIGNERS"),
    ("assinar", "assinaturas_ok", "Assinatura registrada", "SIGN_DIPLOMA"),
    ("assinaturas_ok", "aguardar_assinatura", "Assinatura pendente", "SIGNATURES_PENDING"),
    ("aguardar_assinatura", "assinar", "Assinatura recebida", "SIGNATURE_RECEIVED"),
    ("assinaturas_ok", "evidencias", "Todas assinaturas concluídas", "SIGNATURES_COMPLETE"),
    ("evidencias", "publicar", "Evidências registradas", "REGISTER_EVIDENCE"),
    ("publicar", "fim", "Diploma publicado", "PUBLISH_DIPLOMA"),
]


def run() -> None:
    db = SessionLocal()
    try:
        workflow = (
            db.query(models_workflow.Workflow)
            .filter_by(internal_name=WORKFLOW_INTERNAL_NAME)
            .first()
        )
        if workflow is None:
            workflow = models_workflow.Workflow(
                id=str(uuid.uuid4()),
                name=WORKFLOW_NAME,
                internal_name=WORKFLOW_INTERNAL_NAME,
                is_active=True,
            )
            db.add(workflow)
            db.flush()
        else:
            print(f"Workflow já existe: {workflow.name} ({workflow.id})")
            return

        states = {}
        for key, label, node_type, is_initial, is_completion, pos_x, pos_y in NODES:
            state = models_workflow.WorkflowState(
                id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                label=label,
                node_type=node_type,
                is_initial=is_initial,
                is_completion=is_completion,
                ui_pos_x=pos_x,
                ui_pos_y=pos_y,
            )
            db.add(state)
            states[key] = state
        db.flush()

        for origin, destination, label, action_code in EDGES:
            db.add(
                models_workflow.WorkflowTransition(
                    id=str(uuid.uuid4()),
                    workflow_id=workflow.id,
                    origin_state_id=states[origin].id,
                    destination_state_id=states[destination].id,
                    label=label,
                    action_code=action_code,
                    is_default=origin not in {"documentos_ok", "dados_ok", "xml_ok", "assinaturas_ok"},
                )
            )

        db.commit()
        print(f"Workflow criado: {WORKFLOW_NAME}")
        print(f"ID: {workflow.id}")
        print(f"Nós: {len(NODES)} | Transições: {len(EDGES)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
