from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import require_module_access
from app.modules.data_store import campuses, course_classes, courses, pending_actions, students, teachers

router = APIRouter(prefix="/ead", tags=["EAD"])


def _build_polos():
    return [
        {
            "polo_id": campus["campus_id"],
            "name": campus["name"],
            "city": campus["city"],
            "coordinator": campus.get("coordinator", "Coordena??o do polo"),
            "status": "ativo",
            "students": sum(1 for student in students.values() if student.get("campus") == campus["name"]),
            "modality": "EaD",
            "support_hours": "Seg-Sex, 08:00-18:00",
        }
        for campus in campuses.values()
    ]


def _build_tutors():
    tutors = []
    for teacher in teachers.values():
        campus = campuses.get(teacher.get("campus_id"), {})
        tutors.append({
            "tutor_id": teacher["teacher_id"],
            "name": teacher["full_name"],
            "specialty": teacher["discipline_name"],
            "polo": campus.get("name", "Polo principal"),
            "status": teacher.get("status", "ativo"),
            "classes": 1,
            "attendance_rate": "94%",
        })
    return tutors


def _build_disciplines():
    items = []
    for class_record in course_classes.values():
        course = courses.get(class_record.get("course_id"), {})
        teacher = teachers.get(class_record.get("teacher_id"), {})
        items.append({
            "discipline_id": class_record["class_id"],
            "name": class_record["course_name"],
            "class_id": class_record["class_id"],
            "modality": "EaD",
            "credits": 4,
            "tutor": teacher.get("full_name", "Tutor da turma"),
            "weekly_load": "4h",
        })
    return items


def _build_attendance():
    records = []
    for student_id, student in students.items():
        class_record = next(
            (item for item in course_classes.values() if item.get("course_id") == student.get("course_id")),
            None,
        )
        if not class_record:
            continue
        records.append({
            "student_id": student_id,
            "student_name": student.get("full_name"),
            "class_id": class_record["class_id"],
            "class_name": class_record["course_name"],
            "polo": student.get("campus", "Campus principal"),
            "presence_rate": 96 if student.get("status") == "matriculado" else 88,
            "last_activity": "2026-11-01",
            "status": "em_dia" if student.get("status") == "matriculado" else "alerta",
        })
    return records


def _build_schedule():
    schedule = []
    for idx, class_record in enumerate(course_classes.values(), 1):
        campus = campuses.get(class_record.get("campus_id"), {})
        teacher = teachers.get(class_record.get("teacher_id"), {})
        schedule.append({
            "id": f"AULA-EAD-{idx:03d}",
            "title": f"Aula s?ncrona de {class_record['course_name']}",
            "date": "2026-11-03",
            "time": "19:00",
            "polo": campus.get("name", "Polo principal"),
            "tutor": teacher.get("full_name", "Tutor da turma"),
            "discipline": class_record["course_name"],
            "modality": "virtual",
            "type": "s?ncrona",
            "status": "agendada",
            "attendance": 20 + idx,
            "link": f"https://meet.example.edu/{class_record['class_id'].lower()}",
        })
    return schedule


def _build_activities():
    return [
        {
            "id": "ATV-EAD-001",
            "title": "Mapa conceitual do curso e objetivos de aprendizagem",
            "discipline": "An?lise e Desenvolvimento de Sistemas",
            "polo": "Campus Central",
            "tutor": "Prof. Jo?o Pereira",
            "due_date": "2026-11-05",
            "status": "pendente",
            "completion": 68,
        },
        {
            "id": "ATV-EAD-002",
            "title": "Estudo de caso e projeto integrador",
            "discipline": "Tecnologia em Com?rcio Exterior",
            "polo": "Campus Norte",
            "tutor": "Prof. Carla Mendes",
            "due_date": "2026-11-08",
            "status": "em_andamento",
            "completion": 82,
        },
    ]


def _build_evaluations():
    return [
        {
            "id": "AVA-EAD-001",
            "title": "Prova objetiva 1",
            "discipline": "An?lise e Desenvolvimento de Sistemas",
            "polo": "Campus Central",
            "tutor": "Prof. Jo?o Pereira",
            "date": "2026-11-07",
            "status": "em_andamento",
            "average": "8,4",
        },
        {
            "id": "AVA-EAD-002",
            "title": "Trabalho em equipe",
            "discipline": "Tecnologia em Com?rcio Exterior",
            "polo": "Campus Norte",
            "tutor": "Prof. Carla Mendes",
            "date": "2026-11-09",
            "status": "agendada",
            "average": "9,1",
        },
    ]


def _build_pending():
    items = []
    for idx, action in enumerate(pending_actions, 1):
        student = students.get(action["student_id"], {})
        items.append({
            "id": f"PED-EAD-{idx:03d}",
            "student": student.get("full_name", action["student_id"]),
            "polo": student.get("campus", "Campus principal"),
            "tutor": next((teacher["full_name"] for teacher in teachers.values() if teacher.get("course_id") == student.get("course_id")), "Tutor do curso"),
            "issue": action["issue"],
            "priority": action["priority"],
            "status": action["status"],
            "deadline": action["deadline"],
        })
    return items

POLOS = _build_polos()
TUTORES = _build_tutors()
DISCIPLINAS = _build_disciplines()
PRESENCA = _build_attendance()
AULAS_EAD = _build_schedule()
ATIVIDADES_EAD = _build_activities()
AVALIACOES_EAD = _build_evaluations()
PENDENCIAS_EAD = _build_pending()

INTEGRACOES = [
    {
        "origin": "sead",
        "target": "secretaria",
        "event": "matricula_aceita",
        "status": "sincronizado",
        "updated_at": "2026-11-01",
    },
    {
        "origin": "sead",
        "target": "ged",
        "event": "documentos_polo",
        "status": "pendente_validacao",
        "updated_at": "2026-11-01",
    },
]


class PoloCreate(BaseModel):
    name: str
    city: str
    coordinator: str
    modality: str = "EaD"


class TutorCreate(BaseModel):
    name: str
    specialty: str
    polo: str
    status: str = "ativo"


class AttendanceCreate(BaseModel):
    student_id: str
    class_id: str
    presence_rate: int
    status: str = "alerta"


class ActivityCreate(BaseModel):
    title: str
    discipline: str
    polo: str
    tutor: str
    due_date: str
    status: str = "pendente"
    completion: int = 0


class PendingCreate(BaseModel):
    student: str
    polo: str
    tutor: str
    issue: str
    priority: str = "m?dia"
    status: str = "pendente"
    deadline: str


@router.get("/dashboard")
def ead_dashboard(user: Any = Depends(require_module_access("ead"))):
    active_polos = [p for p in POLOS if p["status"] == "ativo"]
    active_tutors = [t for t in TUTORES if t["status"] == "ativo"]
    pending = [item for item in PENDENCIAS_EAD if item["status"] in {"pendente", "em_tratamento", "aguardando"}]
    return {
        "module": "ead",
        "title": "EAD ? Educa??o a Dist?ncia",
        "stats": {
            "polos_ativos": len(active_polos),
            "turmas_ead": len(course_classes),
            "tutores_ativos": len(active_tutors),
            "alunos_conectados": len(students),
            "pendencias_atendimento": len(pending),
            "aulas_agendadas": len(AULAS_EAD),
            "atividades_pendentes": len([item for item in ATIVIDADES_EAD if item["status"] == "pendente"]),
            "taxa_presenca": "94%",
        },
        "features": [
            "Polos e tutoria",
            "Turmas e disciplinas EaD",
            "Calend?rio de aulas presenciais e virtuais",
            "Acompanhamento de frequ?ncia",
            "Atividades e avalia??es",
            "Pend?ncias por tutor e polo",
            "Integra??o com SEAD e GED",
        ],
        "user": getattr(user, "username", None),
    }


@router.get("/polos")
def list_polos(user: Any = Depends(require_module_access("ead"))):
    return {"module": "ead", "items": POLOS}


@router.get("/tutores")
def list_tutors(user: Any = Depends(require_module_access("ead"))):
    return {"module": "ead", "items": TUTORES}


@router.get("/disciplinas")
def list_disciplines(user: Any = Depends(require_module_access("ead"))):
    return {"module": "ead", "items": DISCIPLINAS}


@router.get("/frequencia")
def list_attendance(user: Any = Depends(require_module_access("ead"))):
    return {"module": "ead", "items": PRESENCA}


def filter_ead_records(records, polo=None, tutor=None):
    filtered = list(records)
    polo_value = None if polo is None or not isinstance(polo, str) else polo
    tutor_value = None if tutor is None or not isinstance(tutor, str) else tutor
    if polo_value:
        filtered = [item for item in filtered if str(item.get("polo", "")).lower() == polo_value.lower()]
    if tutor_value:
        filtered = [item for item in filtered if str(item.get("tutor", "")).lower() == tutor_value.lower()]
    return filtered


@router.get("/calendario")
def list_calendar(
    polo: str | None = Query(default=None),
    tutor: str | None = Query(default=None),
    user: Any = Depends(require_module_access("ead")),
):
    return {"module": "ead", "items": filter_ead_records(AULAS_EAD, polo=polo, tutor=tutor)}


@router.get("/atividades")
def list_activities(
    polo: str | None = Query(default=None),
    tutor: str | None = Query(default=None),
    user: Any = Depends(require_module_access("ead")),
):
    return {"module": "ead", "items": filter_ead_records(ATIVIDADES_EAD, polo=polo, tutor=tutor)}


@router.get("/avaliacoes")
def list_evaluations(
    polo: str | None = Query(default=None),
    tutor: str | None = Query(default=None),
    user: Any = Depends(require_module_access("ead")),
):
    return {"module": "ead", "items": filter_ead_records(AVALIACOES_EAD, polo=polo, tutor=tutor)}


@router.get("/pendencias")
def list_pending(
    polo: str | None = Query(default=None),
    tutor: str | None = Query(default=None),
    user: Any = Depends(require_module_access("ead")),
):
    return {"module": "ead", "items": filter_ead_records(PENDENCIAS_EAD, polo=polo, tutor=tutor)}


@router.get("/acompanhamento")
def list_acompanhamento(
    polo: str | None = Query(default=None),
    tutor: str | None = Query(default=None),
    user: Any = Depends(require_module_access("ead")),
):
    calendar = filter_ead_records(AULAS_EAD, polo=polo, tutor=tutor)
    activities = filter_ead_records(ATIVIDADES_EAD, polo=polo, tutor=tutor)
    evaluations = filter_ead_records(AVALIACOES_EAD, polo=polo, tutor=tutor)
    pending = filter_ead_records(PENDENCIAS_EAD, polo=polo, tutor=tutor)
    return {
        "module": "ead",
        "filters": {"polo": polo, "tutor": tutor},
        "summary": {
            "aulas_agendadas": len(calendar),
            "atividades_pendentes": len([item for item in activities if item["status"] == "pendente"]),
            "avaliacoes_em_andamento": len([item for item in evaluations if item["status"] == "em_andamento"]),
            "pendencias_criticas": len([item for item in pending if item["priority"] == "alta"]),
            "taxa_media_presenca": "94%",
        },
        "calendar": calendar,
        "activities": activities,
        "evaluations": evaluations,
        "pending": pending,
    }


@router.get("/integracao")
def list_integrations(user: Any = Depends(require_module_access("ead"))):
    return {"module": "ead", "items": INTEGRACOES}


@router.get("/alunos")
def list_students(user: Any = Depends(require_module_access("ead"))):
    return {"module": "ead", "items": list(students.values())}


@router.post("/polos")
def create_polo(payload: PoloCreate, user: Any = Depends(require_module_access("ead"))):
    if not payload.name or not payload.city:
        raise HTTPException(status_code=400, detail="Nome e cidade do polo s?o obrigat?rios")
    polo = {
        "polo_id": f"POL-{len(POLOS) + 1:03d}",
        "name": payload.name,
        "city": payload.city,
        "coordinator": payload.coordinator,
        "status": "ativo",
        "students": 0,
        "modality": payload.modality,
        "support_hours": "Seg-Sex, 08:00-18:00",
    }
    POLOS.append(polo)
    return {"module": "ead", "message": "Polo registrado no EAD", "polo": polo}


@router.post("/tutores")
def create_tutor(payload: TutorCreate, user: Any = Depends(require_module_access("ead"))):
    if not payload.name or not payload.specialty:
        raise HTTPException(status_code=400, detail="Nome e especialidade do tutor s?o obrigat?rios")
    tutor = {
        "tutor_id": f"TUT-{len(TUTORES) + 1:03d}",
        "name": payload.name,
        "specialty": payload.specialty,
        "polo": payload.polo,
        "status": payload.status,
        "classes": 1,
        "attendance_rate": "90%",
    }
    TUTORES.append(tutor)
    return {"module": "ead", "message": "Tutor registrado no EAD", "tutor": tutor}


@router.post("/frequencia")
def register_attendance(payload: AttendanceCreate, user: Any = Depends(require_module_access("ead"))):
    if payload.student_id not in students:
        raise HTTPException(status_code=404, detail="Aluno n?o encontrado")
    record = {
        "student_id": payload.student_id,
        "student_name": students[payload.student_id]["full_name"],
        "class_id": payload.class_id,
        "class_name": next((d["name"] for d in DISCIPLINAS if d["class_id"] == payload.class_id), "Turma EaD"),
        "polo": next((p["name"] for p in POLOS if p["status"] == "ativo"), "Polo principal"),
        "presence_rate": payload.presence_rate,
        "last_activity": "2026-11-01",
        "status": payload.status,
    }
    PRESENCA.append(record)
    return {"module": "ead", "message": "Frequ?ncia registrada com sucesso", "record": record}


@router.post("/atividades")
def create_activity(payload: ActivityCreate, user: Any = Depends(require_module_access("ead"))):
    if not payload.title or not payload.discipline:
        raise HTTPException(status_code=400, detail="T?tulo e disciplina s?o obrigat?rios")
    activity = {
        "id": f"ATV-{len(ATIVIDADES_EAD) + 1:03d}",
        "title": payload.title,
        "discipline": payload.discipline,
        "polo": payload.polo,
        "tutor": payload.tutor,
        "due_date": payload.due_date,
        "status": payload.status,
        "completion": payload.completion,
    }
    ATIVIDADES_EAD.append(activity)
    return {"module": "ead", "message": "Atividade registrada", "activity": activity}


@router.post("/pendencias")
def create_pending(payload: PendingCreate, user: Any = Depends(require_module_access("ead"))):
    if not payload.student or not payload.issue:
        raise HTTPException(status_code=400, detail="Aluno e descri??o da pend?ncia s?o obrigat?rios")
    pending = {
        "id": f"PED-{len(PENDENCIAS_EAD) + 1:03d}",
        "student": payload.student,
        "polo": payload.polo,
        "tutor": payload.tutor,
        "issue": payload.issue,
        "priority": payload.priority,
        "status": payload.status,
        "deadline": payload.deadline,
    }
    PENDENCIAS_EAD.append(pending)
    return {"module": "ead", "message": "Pend?ncia registrada", "pending": pending}


@router.get("/turmas")
def list_classes(user: Any = Depends(require_module_access("ead"))):
    classes = []
    for class_record in course_classes.values():
        campus = campuses.get(class_record.get("campus_id"), {})
        teacher = teachers.get(class_record.get("teacher_id"), {})
        classes.append({
            "class_id": class_record["class_id"],
            "name": class_record["course_name"],
            "polo": campus.get("name", "Campus principal"),
            "tutor": teacher.get("full_name", "Tutor da turma"),
            "status": "em_andamento",
            "students": class_record.get("students_count", 0),
            "meetings": 8,
            "completion": "76%",
        })
    return {"module": "ead", "items": classes}
