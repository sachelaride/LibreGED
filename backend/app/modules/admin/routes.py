from typing import Any

from fastapi import APIRouter, Depends

from app.auth import require_module_access
from app.modules.data_store import campuses, enrollments, institutions, pending_actions, students, teachers

router = APIRouter(prefix="/admin", tags=["Administração"])


@router.get("/dashboard")
def admin_dashboard(user: Any = Depends(require_module_access("admin"))):
    active_students = sum(1 for student in students.values() if student.get("status") == "matriculado")
    active_enrollments = sum(1 for enrollment in enrollments.values() if enrollment.get("status") == "matriculado")
    active_institutions = sum(1 for institution in institutions.values() if institution.get("status") == "ativa")
    courses_involved = len({student.get("course_id") for student in students.values() if student.get("course_id")})
    return {
        "module": "admin",
        "title": "Administração Geral",
        "stats": {
            "instituicoes_ativas": active_institutions,
            "campi_cadastrados": len(campuses),
            "alunos_ativos": active_students,
            "matriculas_ativas": active_enrollments,
            "professores_ativos": sum(1 for teacher in teachers.values() if teacher.get("status") == "ativo"),
            "pendencias_crticas": sum(1 for action in pending_actions if action.get("priority") in {"alta", "média"}),
            "cursos_vinculados": courses_involved,
        },
        "features": [
            "Instituições e campus",
            "Usuários e permissões",
            "Acompanhamento institucional",
            "Workflow e governança",
            "Visão integrada dos módulos",
            "Auditoria e governança",
        ],
        "user": getattr(user, "username", None),
    }


@router.get("/instituicoes")
def list_institutions(user: Any = Depends(require_module_access("admin"))):
    items = []
    for institution in institutions.values():
        items.append({
            "institution_id": institution["institution_id"],
            "name": institution["name"],
            "short_name": institution["short_name"],
            "status": institution["status"],
            "campus_count": len(institution.get("campus_ids", [])),
            "modality": institution["modality"],
            "education_level": institution["education_level"],
        })
    return {"module": "admin", "items": items}


@router.get("/usuarios")
def list_users(user: Any = Depends(require_module_access("admin"))):
    items = []
    for student in students.values():
        items.append({
            "user_id": student["student_id"],
            "name": student["full_name"],
            "role": "aluno",
            "status": student.get("status", "pendente"),
            "course": student.get("course"),
            "campus": student.get("campus"),
        })
    for teacher in teachers.values():
        items.append({
            "user_id": teacher["teacher_id"],
            "name": teacher["full_name"],
            "role": "professor",
            "status": teacher.get("status", "ativo"),
            "course": teacher.get("discipline_name"),
            "campus": campuses.get(teacher.get("campus_id"), {}).get("name", "Campus principal"),
        })
    return {"module": "admin", "items": items}


@router.get("/workflows")
def list_workflows(user: Any = Depends(require_module_access("admin"))):
    items = []
    for action in pending_actions:
        student = students.get(action.get("student_id"), {})
        items.append({
            "id": action.get("student_id"),
            "student": student.get("full_name", action.get("student_id")),
            "issue": action.get("issue"),
            "priority": action.get("priority"),
            "status": action.get("status"),
            "responsible": action.get("responsible"),
            "deadline": action.get("deadline"),
            "category": action.get("category"),
        })
    return {"module": "admin", "items": items}
