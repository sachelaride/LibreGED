"""Create the visual diploma workflow used by the BPMN editor."""

import json
import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import SessionLocal
from app import models
from app import models_academic_dossier
from app import models_ged
from app import models_workflow


WORKFLOW_NAME = "Emissão de Diplomas"
WORKFLOW_INTERNAL_NAME = "emissao-de-diplomas"


STATE_CONFIG = {
    "Aluno": {"pool": "Aluno", "icon": "user", "color": "#dbeafe"},
    "Secretaria Acadêmica": {"pool": "Secretaria Acadêmica", "icon": "clipboard-check", "color": "#bbf7d0"},
    "Coordenação": {"pool": "Coordenação", "icon": "graduation-cap", "color": "#fef3c7"},
    "Validação Institucional": {"pool": "Validação Institucional", "icon": "building", "color": "#e9d5ff"},
    "Assinatura Digital": {"pool": "Assinatura Digital", "icon": "pen-nib", "color": "#ddd6fe"},
    "Expedição": {"pool": "Expedição", "icon": "send", "color": "#cbd5e1"},
}


NODES = [
    ("inicio", "Solicitação de emissão", "event_start", True, False, 80, 120, "Aluno"),
    ("dados_aluno", "Dados do aluno e matrícula", "task_user", False, False, 300, 120, "Aluno"),
    ("confirmar_dados", "Confirmação dos dados pessoais", "task_user", False, False, 560, 120, "Aluno"),
    ("verifica_matricula", "Verificação de matrícula", "task_service", False, False, 820, 120, "Secretaria Acadêmica"),
    ("verifica_curso", "Verificação do curso", "task_service", False, False, 1080, 120, "Secretaria Acadêmica"),
    ("situacao_academica", "Verificação da situação acadêmica", "gateway_exclusive", False, False, 1340, 120, "Secretaria Acadêmica"),
    ("encaminhar_coordenacao", "Encaminhar para coordenação", "task_service", False, False, 1600, 120, "Secretaria Acadêmica"),
    ("validacao_curricular", "Validação curricular", "gateway_exclusive", False, False, 820, 360, "Coordenação"),
    ("validacao_historico", "Validação do histórico escolar", "task_service", False, False, 1080, 360, "Coordenação"),
    ("aprovacao_academica", "Aprovação acadêmica", "gateway_exclusive", False, False, 1340, 360, "Coordenação"),
    ("pendencia", "Pendência acadêmica / ajuste", "task_user", False, False, 1340, 560, "Aluno"),
    ("gerar_diploma", "Geração do diploma / XML", "task_script", False, False, 820, 640, "Validação Institucional"),
    ("validar_campos", "Validação de campos obrigatórios", "gateway_exclusive", False, False, 1080, 640, "Validação Institucional"),
    ("validar_institucional", "Validação institucional do curso e IES", "task_service", False, False, 1340, 640, "Validação Institucional"),
    ("validar_codigo", "Verificação do código de validação", "gateway_exclusive", False, False, 1600, 640, "Validação Institucional"),
    ("aprovado_institucional", "Documento aprovado institucionalmente", "event_message", False, False, 1880, 640, "Validação Institucional"),
    ("rejeitado", "Documento rejeitado / retrabalho", "task_service", False, False, 1880, 860, "Secretaria Acadêmica"),
    ("preparar_assinatura", "Preparação para assinatura", "task_service", False, False, 820, 940, "Assinatura Digital"),
    ("assinar_documento", "Assinatura do documento", "task_service", False, False, 1080, 940, "Assinatura Digital"),
    ("validar_assinatura", "Validação da assinatura", "gateway_exclusive", False, False, 1340, 940, "Assinatura Digital"),
    ("documento_assinado", "Documento assinado e autenticado", "event_message", False, False, 1600, 940, "Assinatura Digital"),
    ("publicar_diploma", "Publicação do diploma", "task_service", False, False, 820, 1200, "Expedição"),
    ("envio_aluno", "Envio ao aluno / portal", "task_service", False, False, 1080, 1200, "Expedição"),
    ("arquivar", "Arquivamento e histórico final", "task_service", False, False, 1340, 1200, "Expedição"),
    ("fim", "Conclusão do processo", "event_end", False, True, 1600, 1200, "Expedição"),
]


EDGES = [
    ("inicio", "dados_aluno", "Iniciar solicitação", "START_REQUEST"),
    ("dados_aluno", "confirmar_dados", "Dados preenchidos", "CONFIRM_DATA"),
    ("confirmar_dados", "verifica_matricula", "Enviar para secretaria", "SEND_TO_SECRETARY"),
    ("verifica_matricula", "verifica_curso", "Matrícula válida", "VALIDATE_REGISTRATION"),
    ("verifica_curso", "situacao_academica", "Curso validado", "VALIDATE_COURSE"),
    ("situacao_academica", "encaminhar_coordenacao", "Situação acadêmica regular", "APPROVE_SECRETARY"),
    ("encaminhar_coordenacao", "validacao_curricular", "Encaminhar coordenação", "FORWARD_COORDINATION"),
    ("validacao_curricular", "validacao_historico", "Histórico revisado", "REVIEW_CURRICULUM"),
    ("validacao_historico", "aprovacao_academica", "Histórico aprovado", "APPROVE_HISTORY"),
    ("aprovacao_academica", "gerar_diploma", "Gerar diploma", "GENERATE_DIPLOMA"),
    ("aprovacao_academica", "pendencia", "Pendência acadêmica", "ACADEMIC_PENDING"),
    ("pendencia", "dados_aluno", "Corrigir dados", "CORRECT_DATA"),
    ("gerar_diploma", "validar_campos", "Documento gerado", "GENERATE_DIPLOMA_XML"),
    ("validar_campos", "validar_institucional", "Campos válidos", "VALIDATE_REQUIRED_FIELDS"),
    ("validar_institucional", "validar_codigo", "Instituição validada", "VALIDATE_INSTITUTION"),
    ("validar_codigo", "aprovado_institucional", "Documento aprovado", "APPROVE_INSTITUTION"),
    ("validar_codigo", "rejeitado", "Documento rejeitado", "REJECT_INSTITUTION"),
    ("rejeitado", "dados_aluno", "Corrigir dados", "RETRY_AFTER_REJECTION"),
    ("aprovado_institucional", "preparar_assinatura", "Liberar assinatura", "PREPARE_SIGNATURE"),
    ("preparar_assinatura", "assinar_documento", "Preparar assinatura", "SIGN_DOCUMENT"),
    ("assinar_documento", "validar_assinatura", "Assinatura registrada", "VALIDATE_SIGNING"),
    ("validar_assinatura", "documento_assinado", "Assinatura válida", "APPROVE_SIGNATURE"),
    ("validar_assinatura", "preparar_assinatura", "Assinatura falhou", "RETRY_SIGNATURE"),
    ("documento_assinado", "publicar_diploma", "Publicar diploma", "PUBLISH_DIPLOMA"),
    ("publicar_diploma", "envio_aluno", "Enviar ao aluno", "SEND_TO_STUDENT"),
    ("envio_aluno", "arquivar", "Arquivar e registrar", "ARCHIVE_DOC"),
    ("arquivar", "fim", "Concluir processo", "COMPLETE_PROCESS"),
]


def _node_config(pool_name):
    return json.dumps(STATE_CONFIG.get(pool_name, {"pool": pool_name, "icon": "circle", "color": "#e2e8f0"}), ensure_ascii=False)


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
        for key, label, node_type, is_initial, is_completion, pos_x, pos_y, pool_name in NODES:
            state = models_workflow.WorkflowState(
                id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                label=label,
                node_type=node_type,
                is_initial=is_initial,
                is_completion=is_completion,
                ui_pos_x=pos_x,
                ui_pos_y=pos_y,
                config_json=_node_config(pool_name),
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
                    condition_key=None,
                    condition_value=None,
                    priority=0,
                    is_default=False,
                    allowed_roles="student,secretary,coordination,institutional,signer,expedition",
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
