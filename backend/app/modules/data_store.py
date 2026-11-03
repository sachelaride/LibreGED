from __future__ import annotations

students = {
    "ALU-1001": {
        "student_id": "ALU-1001",
        "person_id": "PES-1001",
        "full_name": "Ana Souza",
        "cpf": "123.456.789-00",
        "email": "ana.souza@universidade.edu.br",
        "status": "matriculado",
        "course_id": "CUR-ADS",
        "course": "Análise e Desenvolvimento de Sistemas",
        "campus": "Campus Central",
        "enrollment_status": "matriculado",
        "document_status": "pendente",
        "document_checklist": ["RG", "CPF", "comprovante", "contrato"],
        "required_documents": ["Comprovante de residência", "Contrato acadêmico"],
        "responsible_financial": "Maria Souza",
        "entry_channel": "vestibular",
        "period": "2026/1",
        "admission_stage": "matrícula confirmada",
    },
    "ALU-1002": {
        "student_id": "ALU-1002",
        "person_id": "PES-1002",
        "full_name": "Bruno Lima",
        "cpf": "987.654.321-00",
        "email": "bruno.lima@universidade.edu.br",
        "status": "pendente",
        "course_id": "CUR-ECOM",
        "course": "Tecnologia em Comércio Exterior",
        "campus": "Campus Norte",
        "enrollment_status": "pendente",
        "document_status": "pendente",
        "document_checklist": ["RG", "CPF", "ensino médio"],
        "required_documents": ["Diploma do ensino médio", "Contrato acadêmico"],
        "responsible_financial": "Carlos Lima",
        "entry_channel": "transferencia",
        "period": "2026/1",
        "admission_stage": "cadastro em análise",
    },
}

people = {
    "PES-1001": {
        "person_id": "PES-1001",
        "full_name": "Ana Souza",
        "cpf": "123.456.789-00",
        "email": "ana.souza@universidade.edu.br",
        "person_kind": "aluno",
        "institution": "Instituto EduGED",
    },
    "PES-1002": {
        "person_id": "PES-1002",
        "full_name": "Bruno Lima",
        "cpf": "987.654.321-00",
        "email": "bruno.lima@universidade.edu.br",
        "person_kind": "aluno",
        "institution": "Instituto EduGED",
    },
    "PES-RESP-1": {
        "person_id": "PES-RESP-1",
        "full_name": "Maria Souza",
        "cpf": "111.222.333-44",
        "email": "maria.souza@email.com",
        "person_kind": "responsavel_financeiro",
        "institution": "Instituto EduGED",
    },
}

courses = {
    "CUR-ADS": {
        "course_id": "CUR-ADS",
        "name": "Análise e Desenvolvimento de Sistemas",
        "modality": "presencial",
        "campus": "Campus Central",
    },
    "CUR-ECOM": {
        "course_id": "CUR-ECOM",
        "name": "Tecnologia em Comércio Exterior",
        "modality": "presencial",
        "campus": "Campus Norte",
    },
}

enrollments = {
    "MAT-0001": {
        "enrollment_id": "MAT-0001",
        "student_id": "ALU-1001",
        "course_id": "CUR-ADS",
        "course_name": "Análise e Desenvolvimento de Sistemas",
        "period": "2026/1",
        "status": "matriculado",
        "campus": "Campus Central",
        "start_date": "2026-01-15",
        "contract_status": "aceito",
        "responsible_financial_id": "PES-RESP-1",
        "responsible_financial_name": "Maria Souza",
        "payment_plan": "anuidade_semestre",
        "documents_ok": True,
        "approved_by": "secretaria",
    },
    "MAT-0002": {
        "enrollment_id": "MAT-0002",
        "student_id": "ALU-1002",
        "course_id": "CUR-ECOM",
        "course_name": "Tecnologia em Comércio Exterior",
        "period": "2026/1",
        "status": "pendente",
        "campus": "Campus Norte",
        "start_date": "2026-02-01",
        "contract_status": "em_validacao",
        "responsible_financial_id": "PES-RESP-2",
        "responsible_financial_name": "Carlos Lima",
        "payment_plan": "anuidade_semestre",
        "documents_ok": False,
        "approved_by": None,
    },
}

student_journey = {
    "ALU-1001": [
        {
            "id": "JOU-1001-1",
            "stage": "inscricao",
            "status": "aprovado",
            "date": "2025-11-10",
            "responsible": "secretaria",
            "details": "Candidato validado para o processo seletivo.",
        },
        {
            "id": "JOU-1001-2",
            "stage": "matricula",
            "status": "confirmado",
            "date": "2026-01-15",
            "responsible": "secretaria",
            "details": "Matrícula ativa com contrato acadêmico aceito.",
        },
        {
            "id": "JOU-1001-3",
            "stage": "documentos",
            "status": "pendente",
            "date": "2026-01-20",
            "responsible": "ged",
            "details": "Documento complementar aguardando conferência final.",
        },
    ],
    "ALU-1002": [
        {
            "id": "JOU-1002-1",
            "stage": "inscricao",
            "status": "em_analise",
            "date": "2026-01-12",
            "responsible": "secretaria",
            "details": "Pré-matrícula em revisão documental.",
        },
        {
            "id": "JOU-1002-2",
            "stage": "documentos",
            "status": "pendente",
            "date": "2026-01-18",
            "responsible": "ged",
            "details": "Básico do aluno validado; documento adicional solicitado.",
        },
    ],
}

institutions = {
    "IES-001": {
        "institution_id": "IES-001",
        "name": "Instituto EduGED",
        "short_name": "EduGED",
        "campus_ids": ["CAMP-001", "CAMP-002"],
        "education_level": "superior",
        "modality": "presencial_ead",
        "status": "ativa",
    }
}

campuses = {
    "CAMP-001": {
        "campus_id": "CAMP-001",
        "name": "Campus Central",
        "city": "Recife",
        "institution_id": "IES-001",
        "coordinator": "Coordenação de Tecnologia",
        "active_courses": ["CUR-ADS", "CUR-COMPUTACAO"],
    },
    "CAMP-002": {
        "campus_id": "CAMP-002",
        "name": "Campus Norte",
        "city": "Caruaru",
        "institution_id": "IES-001",
        "coordinator": "Coordenação de Negócios",
        "active_courses": ["CUR-ECOM"],
    },
}

teachers = {
    "PROF-001": {
        "teacher_id": "PROF-001",
        "full_name": "Prof. João Pereira",
        "discipline_id": "DISC-ADS-01",
        "discipline_name": "Algoritmos",
        "campus_id": "CAMP-001",
        "course_id": "CUR-ADS",
        "status": "ativo",
    },
    "PROF-002": {
        "teacher_id": "PROF-002",
        "full_name": "Prof. Carla Mendes",
        "discipline_id": "DISC-ECOM-01",
        "discipline_name": "Comércio Exterior",
        "campus_id": "CAMP-002",
        "course_id": "CUR-ECOM",
        "status": "ativo",
    },
}

course_classes = {
    "TUR-ADS-101": {
        "class_id": "TUR-ADS-101",
        "course_id": "CUR-ADS",
        "course_name": "Análise e Desenvolvimento de Sistemas",
        "campus_id": "CAMP-001",
        "period": "2026/1",
        "teacher_id": "PROF-001",
        "teacher_name": "Prof. João Pereira",
        "students_count": 1,
        "status": "ativa",
    },
    "TUR-ECOM-201": {
        "class_id": "TUR-ECOM-201",
        "course_id": "CUR-ECOM",
        "course_name": "Tecnologia em Comércio Exterior",
        "campus_id": "CAMP-002",
        "period": "2026/1",
        "teacher_id": "PROF-002",
        "teacher_name": "Prof. Carla Mendes",
        "students_count": 1,
        "status": "ativa",
    },
}

academic_processes = {
    "ALU-1001": [
        {
            "process_id": "PROC-1001-1",
            "type": "matricula",
            "title": "Matrícula confirmada",
            "status": "concluido",
            "owner": "secretaria",
            "updated_at": "2026-01-15",
        },
        {
            "process_id": "PROC-1001-2",
            "type": "documento",
            "title": "Documentação complementar",
            "status": "pendente",
            "owner": "ged",
            "updated_at": "2026-01-20",
        },
    ],
    "ALU-1002": [
        {
            "process_id": "PROC-1002-1",
            "type": "documento",
            "title": "Doc. de matrícula",
            "status": "pendente",
            "owner": "secretaria",
            "updated_at": "2026-01-18",
        },
    ],
}

documents = {
    "DOC-001": {
        "document_id": "DOC-001",
        "title": "RG do aluno",
        "file_name": "rg_ana.pdf",
        "document_type": "Identidade",
        "status": "validado",
        "student_id": "ALU-1001",
        "related_process": "matricula",
    },
    "DOC-002": {
        "document_id": "DOC-002",
        "title": "Diploma",
        "file_name": "diploma.pdf",
        "document_type": "Diploma",
        "status": "assinatura pendente",
        "student_id": "ALU-1001",
        "related_process": "conclusao",
    },
    "DOC-003": {
        "document_id": "DOC-003",
        "title": "Comprovante de residência",
        "file_name": "residencia_bruno.pdf",
        "document_type": "Comprovante",
        "status": "pendente",
        "student_id": "ALU-1002",
        "related_process": "matricula",
    },
}

module_context = {
    "secretaria": {
        "primary_entities": ["alunos", "matriculas", "processos", "documentos"],
        "related_modules": ["coordenacao", "financeiro", "ged"],
    },
    "coordenacao": {
        "primary_entities": ["cursos", "turmas", "disciplinas", "alunos"],
        "related_modules": ["secretaria", "professores", "financeiro"],
    },
    "financeiro": {
        "primary_entities": ["contratos", "parcelas", "responsaveis", "cobrancas"],
        "related_modules": ["secretaria", "coordenacao"],
    },
    "ged": {
        "primary_entities": ["documentos", "dossies", "historicos", "assinaturas"],
        "related_modules": ["secretaria", "coordenacao"],
    },
    "ead": {
        "primary_entities": ["polos", "tutores", "disciplinas", "turmas"],
        "related_modules": ["secretaria", "coordenacao"],
    },
}


def get_academic_summary():
    return {
        "institution": institutions["IES-001"],
        "campuses": list(campuses.values()),
        "teachers": list(teachers.values()),
        "courses": list(courses.values()),
        "classes": list(course_classes.values()),
        "students_total": len(students),
        "enrollments_total": len(enrollments),
        "processes_total": sum(len(v) for v in academic_processes.values()),
        "documents_total": len(documents),
        "module_context": module_context,
    }


def get_student_context(student_id: str):
    student = students.get(student_id)
    if not student:
        return None
    course = courses.get(student.get("course_id"), {})
    class_record = next(
        (c for c in course_classes.values() if c.get("course_id") == student.get("course_id")),
        {},
    )
    return {
        "student": student,
        "course": course,
        "class": class_record,
        "enrollments": [e for e in enrollments.values() if e.get("student_id") == student_id],
        "documents": [d for d in documents.values() if d.get("student_id") == student_id],
        "processes": academic_processes.get(student_id, []),
        "journey": student_journey.get(student_id, []),
    }


def get_student_lifecycle_summary(student_id: str):
    student = students.get(student_id)
    if not student:
        return None

    enrollment = next(
        (value for value in enrollments.values() if value.get("student_id") == student_id),
        None,
    )
    document_count = sum(1 for doc in documents.values() if doc.get("student_id") == student_id)
    pending_documents = sum(1 for doc in documents.values() if doc.get("student_id") == student_id and doc.get("status") == "pendente")
    status = student.get("enrollment_status") or "pendente"

    next_actions = {
        "matriculado": "Acompanhar o desempenho e a documentação do aluno.",
        "pendente": "Solicitar documentação complementar e validar a matrícula.",
        "em análise": "Conferir a documentação e encerrar a pré-matrícula.",
    }

    return {
        "student_id": student_id,
        "student_name": student.get("full_name"),
        "course": student.get("course"),
        "status": status,
        "enrollment_status": enrollment.get("status") if enrollment else status,
        "documents_count": document_count,
        "pending_documents": pending_documents,
        "processes_count": len(academic_processes.get(student_id, [])),
        "next_action": next_actions.get(status, "Acompanhar o processo acadêmico."),
    }


grades = {
    "ALU-1001": {
        "Algoritmos": 9.4,
        "Banco de Dados": 8.7,
        "Matemática": 9.1,
    },
    "ALU-1002": {
        "Algoritmos": 7.8,
        "Banco de Dados": 8.1,
        "Matemática": 7.4,
    },
}

invoices = {
    "INV-01": {
        "invoice_id": "INV-01",
        "student_id": "ALU-1001",
        "amount": 1450.00,
        "due_date": "2026-11-20",
        "status": "pendente",
        "course_id": "CUR-ADS",
        "period": "2026/1",
        "installment": "1/2",
        "issuer": "Secretaria",
        "payment_method": "boleto",
        "contract_id": "CTR-1001",
        "responsible_financial": "Maria Souza",
    },
    "INV-02": {
        "invoice_id": "INV-02",
        "student_id": "ALU-1002",
        "amount": 1320.00,
        "due_date": "2026-11-12",
        "status": "quitado",
        "course_id": "CUR-ECOM",
        "period": "2026/1",
        "installment": "1/1",
        "issuer": "Financeiro",
        "payment_method": "pix",
        "contract_id": "CTR-1002",
        "responsible_financial": "Carlos Lima",
    },
}

financial_contracts = {
    "CTR-1001": {
        "contract_id": "CTR-1001",
        "student_id": "ALU-1001",
        "course_id": "CUR-ADS",
        "period": "2026/1",
        "status": "ativo",
        "plan": "anuidade_semestre",
        "total_amount": 4570.00,
        "discount": 350.00,
        "responsible_financial": "Maria Souza",
        "signed_at": "2026-01-10",
    },
    "CTR-1002": {
        "contract_id": "CTR-1002",
        "student_id": "ALU-1002",
        "course_id": "CUR-ECOM",
        "period": "2026/1",
        "status": "em_validacao",
        "plan": "anuidade_semestre",
        "total_amount": 4980.00,
        "discount": 0.00,
        "responsible_financial": "Carlos Lima",
        "signed_at": "2026-01-18",
    },
}

pending_actions = [
    {
        "student_id": "ALU-1001",
        "issue": "Documentação incompleta",
        "priority": "alta",
        "status": "em andamento",
        "responsible": "Secretaria",
        "deadline": "2026-11-15",
        "category": "Documentação",
        "course_id": "CUR-ADS",
    },
    {
        "student_id": "ALU-1002",
        "issue": "Plano curricular pendente",
        "priority": "média",
        "status": "em andamento",
        "responsible": "Coordenação",
        "deadline": "2026-11-18",
        "category": "Currículo",
        "course_id": "CUR-ECOM",
    },
]

classes = [
    {"class_id": "TUR-201", "name": "Algoritmos", "period": "2026/1"},
    {"class_id": "TUR-202", "name": "Banco de Dados", "period": "2026/1"},
]

module_catalog = {
    "secretaria": {"label": "Secretaria", "description": "Atendimento acadêmico e matrículas."},
    "professores": {"label": "Professores", "description": "Acompanhamento de turmas, notas e aulas."},
    "ged": {"label": "GED", "description": "Documentos, versões e auditoria documental."},
    "financeiro": {"label": "Financeiro", "description": "Financeiro, cobranças e manutenção acadêmica."},
    "coordenacao": {"label": "Coordenação", "description": "Validação curricular e governança acadêmica."},
    "aluno": {"label": "Aluno", "description": "Portal do estudante e acompanhamento acadêmico."},
}


def get_student_detail(student_id: str):
    student = students.get(student_id)
    if not student:
        return None
    enrollment = next((value for value in enrollments.values() if value.get("student_id") == student_id), None)
    return {
        "student": student,
        "person": people.get(student.get("person_id"), {}),
        "enrollment": enrollment,
        "documents": [doc for doc in documents.values() if doc.get("student_id") == student_id],
        "journey": student_journey.get(student_id, []),
        "finances": [invoice for invoice in invoices.values() if invoice.get("student_id") == student_id],
    }


def get_active_enrollment_count():
    return sum(1 for item in enrollments.values() if item.get("status") == "matriculado")


def get_pending_document_count():
    return sum(1 for doc in documents.values() if doc.get("status") == "pendente")
