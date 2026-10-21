r"""Replace application data with a linked GED validation dataset.

Run from ``backend`` only after confirming the target database:
    ..\.venv\Scripts\python.exe -m app.scripts.reset_validation_environment --confirm-database eduged_libre
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shutil
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path

import pymupdf
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app import auth, models
from app.database import SessionLocal, engine
from app.models_ged import (
    DocumentCategory,
    DocumentTransitionHistory,
    GEDAcademicPhase,
    GEDDocument,
    GEDDocumentIndexValue,
    GEDDocumentStatus,
)
from app.models_ged_config import (
    DocumentClassification,
    DocumentType,
    DocumentTypeIndex,
    DocumentTypeVersion,
    GedIndex,
    UserDocumentType,
)
from app.models_storage import StorageRule
from app.models_workflow import (
    DocumentWorkflowInstance,
    Workflow,
    WorkflowState,
    WorkflowTask,
    WorkflowTransition,
    WorkflowVersion,
)
from app.storage import STORAGE_ROOT
from app.models import utc_now


PREFIX = "VALIDACAO-GED"
INSTITUTION_ID = f"{PREFIX.lower()}-instituicao"
CAMPUS_ID = f"{PREFIX.lower()}-campus"
ADMIN_ID = f"{PREFIX.lower()}-admin"
WORKFLOW_INTERNAL_NAME = "validacao-assinatura-ged-v1"
WORKFLOW_NAME = "Validação Documental e Assinaturas - Teste"

STATES = [
    ("Início", True, False, "start", {}, 100, 200),
    (
        "Validação documental",
        False,
        False,
        "user_task",
        {"pool_name": "admin_global", "task_form": "validar_documento"},
        330,
        200,
    ),
    (
        "Conferência acadêmica",
        False,
        False,
        "user_task",
        {"pool_name": "admin_global", "task_form": "conferir_dados_academicos"},
        560,
        200,
    ),
    (
        "Assinatura institucional",
        False,
        False,
        "user_task",
        {"pool_name": "admin_global", "task_form": "assinar_documento"},
        790,
        200,
    ),
    (
        "Registro e preservação",
        False,
        False,
        "user_task",
        {"pool_name": "admin_global", "task_form": "registrar_documento"},
        1020,
        200,
    ),
    ("Concluído", False, True, "end", {}, 1250, 200),
]

INDEX_SPECS = [
    ("CPF", "Caractere", "###.###.###-##"),
    ("Nome do Aluno", "Caractere", None),
    ("Matrícula", "Caractere", None),
    ("Número do RG", "Caractere", None),
    ("Data de Emissão", "Data", None),
    ("Curso", "Caractere", None),
    ("Semestre", "Caractere", None),
    ("Data de Colação", "Data", None),
    ("Número de Registro do Diploma", "Caractere", None),
]

DOCUMENT_TYPES = [
    {
        "name": "Documento Pessoal - Identidade",
        "group_id": "pessoal",
        "classification": "Identidade (RG)",
        "retention_years": 5,
        "phase": GEDAcademicPhase.MATRICULA,
        "signature_required": False,
        "indices": ["CPF", "Nome do Aluno", "Matrícula", "Número do RG", "Data de Emissão"],
        "partition": "pessoal/identidade",
    },
    {
        "name": "Documento Pessoal - CPF",
        "group_id": "pessoal",
        "classification": "Cadastro de Pessoa Física",
        "retention_years": 5,
        "phase": GEDAcademicPhase.MATRICULA,
        "signature_required": False,
        "indices": ["CPF", "Nome do Aluno", "Matrícula"],
        "partition": "pessoal/cpf",
    },
    {
        "name": "Termo de Responsabilidade",
        "group_id": "academico",
        "classification": "Termo assinado",
        "retention_years": 5,
        "phase": GEDAcademicPhase.CURSO,
        "signature_required": True,
        "indices": ["CPF", "Nome do Aluno", "Matrícula", "Data de Emissão"],
        "partition": "academico/termo-responsabilidade",
    },
    {
        "name": "Histórico Escolar da Graduação",
        "group_id": "academico",
        "classification": "Histórico final",
        "retention_years": 100,
        "phase": GEDAcademicPhase.FORMATURA,
        "signature_required": True,
        "indices": ["CPF", "Nome do Aluno", "Matrícula", "Curso", "Semestre"],
        "partition": "academico/historico",
    },
    {
        "name": "Diploma Digital (Oficial)",
        "group_id": "academico",
        "classification": "Diploma oficial",
        "retention_years": 100,
        "phase": GEDAcademicPhase.DIPLOMACAO,
        "signature_required": True,
        "indices": [
            "CPF",
            "Nome do Aluno",
            "Matrícula",
            "Curso",
            "Data de Colação",
            "Número de Registro do Diploma",
        ],
        "partition": "academico/diploma",
    },
]

STUDENTS = [
    {
        "name": "Aluno Demonstrativo 01",
        "cpf": "99999999101",
        "registration": "TESTE-2026-001",
        "email": "aluno01@example.invalid",
    },
    {
        "name": "Aluno Demonstrativo 02",
        "cpf": "99999999110",
        "registration": "TESTE-2026-002",
        "email": "aluno02@example.invalid",
    },
    {
        "name": "Aluno Demonstrativo 03",
        "cpf": "99999999128",
        "registration": "TESTE-2026-003",
        "email": "aluno03@example.invalid",
    },
]


def _quote(identifier: str) -> str:
    return engine.dialect.identifier_preparer.quote(identifier)


def _delete_application_data(db: Session) -> None:
    inspector = inspect(db.get_bind())
    table_names = set(inspector.get_table_names())
    preserved = {
        "alembic_version",
        "ged_workflows",
        "ged_workflow_states",
        "ged_workflow_transitions",
        "ged_workflow_versions",
        "representation_services",
        "representation_service_versions",
    }
    preserved.intersection_update(table_names)
    removable = table_names - preserved

    for table in preserved:
        nullability = {
            column["name"]: column["nullable"]
            for column in inspector.get_columns(table)
        }
        for foreign_key in inspector.get_foreign_keys(table):
            parent = foreign_key.get("referred_table")
            if parent not in removable:
                continue
            columns = foreign_key["constrained_columns"]
            if any(not nullability[name] for name in columns):
                raise RuntimeError(
                    f"A definição preservada {table} depende de dados que seriam removidos."
                )
            for column in columns:
                db.execute(text(
                    f"UPDATE {_quote(table)} SET {_quote(column)} = NULL "
                    f"WHERE {_quote(column)} IS NOT NULL"
                ))

    children = defaultdict(set)
    for child in removable:
        for foreign_key in inspector.get_foreign_keys(child):
            parent = foreign_key.get("referred_table")
            if parent in removable:
                children[parent].add(child)
                for column in foreign_key["constrained_columns"]:
                    column_info = next(
                        item for item in inspector.get_columns(child)
                        if item["name"] == column
                    )
                    if column_info["nullable"]:
                        db.execute(text(
                            f"UPDATE {_quote(child)} SET {_quote(column)} = NULL "
                            f"WHERE {_quote(column)} IS NOT NULL"
                        ))

    ordered = []
    visited = set()
    visiting = set()

    def visit(table: str) -> None:
        if table in visited or table in visiting:
            return
        visiting.add(table)
        for child in sorted(children[table]):
            visit(child)
        visiting.remove(table)
        visited.add(table)
        ordered.append(table)

    for table in sorted(removable):
        visit(table)
    for table in ordered:
        db.execute(text(f"DELETE FROM {_quote(table)}"))


def _ensure_workflow(db: Session) -> tuple[Workflow, dict[str, WorkflowState]]:
    workflow = db.query(Workflow).filter_by(internal_name=WORKFLOW_INTERNAL_NAME).first()
    if workflow is None:
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=WORKFLOW_NAME,
            internal_name=WORKFLOW_INTERNAL_NAME,
            is_active=True,
        )
        db.add(workflow)
        db.flush()
    else:
        workflow.name = WORKFLOW_NAME
        workflow.is_active = True

    states = {}
    for label, initial, completion, node_type, config, x, y in STATES:
        state = db.query(WorkflowState).filter_by(
            workflow_id=workflow.id, label=label
        ).first()
        if state is None:
            state = WorkflowState(
                id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                label=label,
            )
            db.add(state)
        state.is_initial = initial
        state.is_completion = completion
        state.node_type = node_type
        state.config_json = json.dumps(config, ensure_ascii=False)
        state.ui_pos_x = x
        state.ui_pos_y = y
        state.swimlane = "Validação e assinatura" if label not in {"Início", "Concluído"} else "Sistema"
        states[label] = state
        db.flush()

    for (origin_label, destination_label, transition_label) in [
        ("Início", "Validação documental", "Iniciar validação"),
        ("Validação documental", "Conferência acadêmica", "Validar"),
        ("Conferência acadêmica", "Assinatura institucional", "Aprovar"),
        ("Assinatura institucional", "Registro e preservação", "Assinar"),
        ("Registro e preservação", "Concluído", "Registrar"),
    ]:
        transition = db.query(WorkflowTransition).filter_by(
            workflow_id=workflow.id,
            origin_state_id=states[origin_label].id,
            destination_state_id=states[destination_label].id,
        ).first()
        if transition is None:
            db.add(WorkflowTransition(
                id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                origin_state_id=states[origin_label].id,
                destination_state_id=states[destination_label].id,
                label=transition_label,
                action_code="APPROVE",
                is_default=True,
            ))
        else:
            transition.label = transition_label
            transition.action_code = "APPROVE"
            transition.is_default = True

    db.flush()
    if not db.query(WorkflowVersion).filter_by(workflow_id=workflow.id).first():
        snapshot = {
            "id": workflow.id,
            "name": workflow.name,
            "internal_name": workflow.internal_name,
            "states": [
                {
                    "id": state.id,
                    "label": state.label,
                    "is_initial": state.is_initial,
                    "is_completion": state.is_completion,
                    "node_type": state.node_type,
                    "config": json.loads(state.config_json or "{}"),
                }
                for state in states.values()
            ],
        }
        db.add(WorkflowVersion(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            version_number=1,
            status="PUBLISHED",
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            published_at=utc_now(),
        ))
    return workflow, states


def _ensure_pdf(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = pymupdf.open()
    try:
        page = pdf.new_page()
        content = "\n".join([title, "AMOSTRA FICTÍCIA PARA TESTE - SEM VALIDADE JURÍDICA", *lines])
        remaining = page.insert_textbox(
            pymupdf.Rect(54, 54, 540, 760),
            content,
            fontsize=11,
            fontname="helv",
            lineheight=1.5,
        )
        if remaining < 0:
            raise RuntimeError(f"O texto não coube na página do arquivo {path.name}.")
        pdf.set_metadata({"title": title, "author": "LibreGED - Dados de validação"})
        pdf.save(path)
    finally:
        pdf.close()


def seed_validation_environment(db: Session, stage_root: Path) -> dict[str, int | str]:
    _delete_application_data(db)

    institution = models.Institution(
        id=INSTITUTION_ID,
        name="Instituição Demonstrativa LibreGED",
        cnpj="00.000.000/0001-91",
        legal_name="Instituição Demonstrativa LibreGED Ltda.",
    )
    db.add(institution)
    db.flush()
    db.add(models.InstitutionSettings(
        id=f"{PREFIX.lower()}-settings",
        institution_id=institution.id,
    ))
    campus = models.Campus(
        id=CAMPUS_ID,
        institution_id=institution.id,
        name="Campus Demonstrativo",
    )
    db.add(campus)
    db.flush()

    password = secrets.token_urlsafe(24)
    user = models.User(
        id=ADMIN_ID,
        username="admin.validacao",
        hashed_password=auth.get_password_hash(password),
        role="admin_global",
        institution_id=institution.id,
        campus_id=campus.id,
        is_active=True,
    )
    db.add(user)
    db.flush()

    storage_rule = StorageRule(
        id=f"{PREFIX.lower()}-storage",
        name="Storage de Validação GED",
        storage_type="Local",
        base_path="validacao_ged",
        max_files_per_folder=1000,
        max_gb_per_folder=10.0,
        enable_duplication=False,
        current_file_count=0,
        current_size_bytes=0,
        is_active=True,
    )
    db.add(storage_rule)

    indices = {}
    for name, data_type, mask in INDEX_SPECS:
        index = GedIndex(
            id=str(uuid.uuid4()),
            name=name,
            type=data_type,
            options=[],
            mask=mask,
            is_active=True,
            is_searchable=True,
        )
        db.add(index)
        indices[name] = index
    db.flush()

    workflow, workflow_states = _ensure_workflow(db)
    validation_state = workflow_states["Validação documental"]
    document_types = {}
    classifications = {}
    for number, spec in enumerate(DOCUMENT_TYPES, start=1):
        doc_type = DocumentType(
            id=str(uuid.uuid4()),
            name=spec["name"],
            workflow_id=workflow.id,
            is_active=True,
            group_id=spec["group_id"],
            retention_years=spec["retention_years"],
            legal_hold=False,
            access_policy={"visibility": "institutional", "demo": True},
            signature_rule={
                "required": spec["signature_required"],
                "type": "ICP-Brasil" if spec["signature_required"] else None,
            },
            active_version=1,
            storage_area_id=storage_rule.id,
            storage_partition_id=spec["partition"],
        )
        db.add(doc_type)
        db.flush()
        category = DocumentCategory(
            id=doc_type.id,
            index_code=f"TESTE-{number:03d}",
            name=doc_type.name,
            description=f"Tipo documental demonstrativo do grupo {spec['group_id']}.",
            is_active=1,
        )
        classification = DocumentClassification(
            id=str(uuid.uuid4()),
            document_type_id=doc_type.id,
            name=spec["classification"],
            is_active=True,
        )
        db.add_all([category, classification])
        db.add(DocumentTypeVersion(
            id=str(uuid.uuid4()),
            document_type_id=doc_type.id,
            version=1,
            status="ACTIVE",
            name=doc_type.name,
            workflow_id=workflow.id,
            group_id=spec["group_id"],
            retention_years=spec["retention_years"],
            legal_hold=False,
            access_policy=doc_type.access_policy,
            signature_rule=doc_type.signature_rule,
            effective_from=utc_now(),
            created_by=user.id,
        ))
        for index_name in spec["indices"]:
            db.add(DocumentTypeIndex(
                id=str(uuid.uuid4()),
                document_type_id=doc_type.id,
                index_id=indices[index_name].id,
                is_required=True,
                is_unique=False,
            ))
        db.add(UserDocumentType(
            id=str(uuid.uuid4()),
            user_id=user.id,
            document_type_id=doc_type.id,
            permissions=[
                "consultar",
                "cadastrar",
                "editar",
                "download",
                "assinar",
                "iniciar_fluxo",
                "executar_fluxo",
                "exportar",
            ],
            denied_permissions=[],
        ))
        document_types[spec["name"]] = (doc_type, spec)
        classifications[doc_type.id] = classification
    db.flush()

    students = []
    for position, data in enumerate(STUDENTS, start=1):
        student = models.Student(
            id=f"{PREFIX.lower()}-aluno-{position:02d}",
            institution_id=institution.id,
            campus_id=campus.id,
            full_name=data["name"],
            birth_date=f"200{position}-01-15",
            cpf=data["cpf"],
            email=data["email"],
        )
        db.add(student)
        db.flush()
        db.add(models.Enrollment(
            id=f"{PREFIX.lower()}-matricula-{position:02d}",
            institution_id=institution.id,
            student_id=student.id,
            campus_id=campus.id,
            course_name="Pedagogia - Turma de Validação",
            class_name="TESTE-2026",
            year=2026,
            status="active",
        ))
        students.append((student, data))
    db.flush()

    final_root = STORAGE_ROOT / "validacao_ged"
    document_count = 0
    total_size = 0
    for student, student_data in students:
        formatted_cpf = (
            f"{student_data['cpf'][:3]}.{student_data['cpf'][3:6]}."
            f"{student_data['cpf'][6:9]}-{student_data['cpf'][9:]}"
        )
        values = {
            "CPF": formatted_cpf,
            "Nome do Aluno": student.full_name,
            "Matrícula": student_data["registration"],
            "Número do RG": f"RG-TESTE-{student_data['registration'][-3:]}",
            "Data de Emissão": "2026-01-15",
            "Curso": "Pedagogia - Turma de Validação",
            "Semestre": "2026.1",
            "Data de Colação": "2026-10-01",
            "Número de Registro do Diploma": f"DIP-TESTE-2026-{student_data['registration'][-3:]}",
        }
        for type_name, (doc_type, spec) in document_types.items():
            document_id = str(uuid.uuid4())
            filename = f"{student_data['registration'].lower()}-{document_id[:8]}.pdf"
            relative_file = Path(spec["partition"]) / filename
            final_path = final_root / relative_file
            staged_path = stage_root / "validacao_ged" / relative_file
            document_values = {name: values[name] for name in spec["indices"]}
            _ensure_pdf(
                staged_path,
                spec["name"],
                [
                    f"Identificador de teste: {document_id}",
                    f"Tipo documental: {spec['name']}",
                    f"Grupo documental: {spec['group_id']}",
                    f"Classificação: {spec['classification']}",
                    *(f"Índice - {name}: {value}" for name, value in document_values.items()),
                ],
            )
            content = staged_path.read_bytes()
            total_size += len(content)
            document = GEDDocument(
                id=document_id,
                title=f"{spec['name']} - {student.full_name}",
                file_path=str(final_path.resolve()),
                file_hash=hashlib.sha256(content).hexdigest(),
                status=GEDDocumentStatus.PENDENTE_VALIDACAO,
                academic_phase=spec["phase"],
                extracted_metadata=json.dumps({
                    "demo": True,
                    "student_name": student.full_name,
                    "registration": student_data["registration"],
                    "document_type": spec["name"],
                    "group_id": spec["group_id"],
                    "indices": document_values,
                }, ensure_ascii=False),
                category_id=doc_type.id,
                classification_id=classifications[doc_type.id].id,
                student_id=student.id,
                institution_id=institution.id,
                campus_id=campus.id,
                uploaded_by_user_id=user.id,
                document_purpose="validation_demo",
                is_official=False,
            )
            db.add(document)
            db.flush()
            for index_name, value in document_values.items():
                db.add(GEDDocumentIndexValue(
                    id=str(uuid.uuid4()),
                    document_id=document.id,
                    index_id=indices[index_name].id,
                    value=value,
                ))
            instance = DocumentWorkflowInstance(
                id=str(uuid.uuid4()),
                document_id=document.id,
                workflow_id=workflow.id,
                current_state_id=validation_state.id,
            )
            db.add(instance)
            db.flush()
            db.add(WorkflowTask(
                id=str(uuid.uuid4()),
                instance_id=instance.id,
                name=validation_state.label,
                description="Conferir o PDF demonstrativo e os índices associados.",
                status="PENDING",
                assignee_id=user.id,
                assignee_role=user.role,
                task_form_key="validar_documento",
            ))
            db.add(DocumentTransitionHistory(
                id=str(uuid.uuid4()),
                document_id=document.id,
                from_status=None,
                to_status=GEDDocumentStatus.PENDENTE_VALIDACAO,
                changed_by_user_id=user.id,
                comments="Documento de teste criado e encaminhado para validação.",
            ))
            document_count += 1

    storage_rule.current_file_count = document_count
    storage_rule.current_size_bytes = total_size
    db.flush()
    return {
        "documents": document_count,
        "types": len(document_types),
        "indices": len(indices),
        "students": len(students),
        "workflow_id": workflow.id,
        "username": user.username,
        "password": password,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apaga dados da aplicação e cria um ambiente GED de validação."
    )
    parser.add_argument(
        "--confirm-database",
        required=True,
        help="Nome exato do banco PostgreSQL autorizado para limpeza.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o escopo da limpeza sem alterar banco ou arquivos.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Executa a limpeza destrutiva e recria os dados de validação.",
    )
    args = parser.parse_args()

    database_name = engine.url.database
    if not database_name or args.confirm_database != database_name:
        raise SystemExit("O nome informado não corresponde ao banco configurado.")
    if not engine.url.drivername.startswith("postgresql"):
        raise SystemExit("A limpeza exige PostgreSQL; nenhum dado foi alterado.")

    expected_storage = Path(__file__).resolve().parents[2] / "storage"
    if STORAGE_ROOT.resolve() != expected_storage.resolve():
        raise SystemExit("O diretório de storage configurado não é o esperado; nada foi alterado.")
    if args.dry_run:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        retained = {
            "alembic_version",
            "ged_workflows",
            "ged_workflow_states",
            "ged_workflow_transitions",
            "ged_workflow_versions",
            "representation_services",
            "representation_service_versions",
        } & tables
        with engine.connect() as connection:
            counts = {
                table: connection.execute(
                    text(f"SELECT COUNT(*) FROM {_quote(table)}")
                ).scalar_one()
                for table in sorted(tables & {
                    "users",
                    "institutions",
                    "ged_documents",
                    "ged_document_types",
                    "ged_indices",
                    "ged_workflows",
                    "representation_services",
                })
            }
            probe = Session(bind=connection)
            try:
                _delete_application_data(probe)
                probe.flush()
            finally:
                probe.close()
                connection.rollback()
        files = [path for path in STORAGE_ROOT.rglob("*") if path.is_file()]
        print(f"Banco alvo: {database_name}")
        print(f"Storage: {STORAGE_ROOT.resolve()}")
        print(f"Tabelas preservadas: {', '.join(sorted(retained))}")
        print(f"Linhas atuais no escopo: {json.dumps(counts, ensure_ascii=False)}")
        print(f"Arquivos atuais no storage: {len(files)}")
        print("Plano: remover os dados fora das definições preservadas e criar 5 tipos, 9 índices e 15 PDFs.")
        print("Dry-run: nenhuma alteração realizada.")
        return
    if not args.apply:
        raise SystemExit("Use --dry-run para revisar o escopo ou --apply para executar a limpeza.")

    stage_root = Path(tempfile.mkdtemp(
        prefix="storage-validation-staging-",
        dir=STORAGE_ROOT.parent,
    ))
    pending_storage = STORAGE_ROOT.with_name(f"{STORAGE_ROOT.name}.reset-pending-{uuid.uuid4().hex}")
    storage_swapped = False
    db = SessionLocal()
    try:
        result = seed_validation_environment(db, stage_root)
        db.flush()
        if STORAGE_ROOT.exists():
            STORAGE_ROOT.replace(pending_storage)
        stage_root.replace(STORAGE_ROOT)
        storage_swapped = True
        db.commit()
    except Exception:
        db.rollback()
        if storage_swapped and STORAGE_ROOT.exists():
            shutil.rmtree(STORAGE_ROOT)
        if pending_storage.exists():
            pending_storage.replace(STORAGE_ROOT)
        if stage_root.exists():
            shutil.rmtree(stage_root)
        raise
    finally:
        db.close()

    if pending_storage.exists():
        try:
            shutil.rmtree(pending_storage)
        except OSError as error:
            raise RuntimeError(
                f"O ambiente foi criado, mas não foi possível remover o storage antigo: {pending_storage}"
            ) from error

    print("Ambiente de validação recriado.")
    print(f"Banco: {database_name}")
    print(f"Tipos: {result['types']} | Índices: {result['indices']} | Alunos: {result['students']}")
    print(f"Documentos PDF: {result['documents']} | Tarefas aguardando validação: {result['documents']}")
    print(f"Workflow de validação: {result['workflow_id']}")
    print(f"Storage: {STORAGE_ROOT / 'validacao_ged'}")
    print(f"Administrador temporário: {result['username']}")
    print(f"Senha temporária: {result['password']}")
    print("Os PDFs são fictícios e não incluem assinatura digital criptográfica.")


if __name__ == "__main__":
    main()
