import json
from datetime import date
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.auth import require_module_access
from app.database import get_db
from app.models_academic_catalog import (
    AcademicAssessment,
    AcademicAttendance,
    AcademicClass,
    AcademicGrade,
    AcademicStaff,
)

router = APIRouter(prefix="/professores", tags=["Professores"])
ProfessorUser = Depends(require_module_access("professores"))

ACTIVE_ENROLLMENT_STATUSES = ("active", "ativo", "matriculado", "enrolled")
MANAGER_ROLES = {"admin_global", "admin_instituicao", "operador"}


class AssessmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    max_score: float = Field(gt=0, le=1000)
    due_date: date | None = None


class AssessmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    max_score: float | None = Field(default=None, gt=0, le=1000)
    due_date: date | None = None


class GradeInput(BaseModel):
    score: float = Field(ge=0, le=1000)
    comment: str | None = Field(default=None, max_length=2000)


class AttendanceInput(BaseModel):
    status: Literal["present", "absent", "justified", "remote"]
    note: str | None = Field(default=None, max_length=1000)


def _class_query(db: Session, user: Any) -> Any:
    query = db.query(AcademicClass)
    if user.role != "admin_global":
        if not user.institution_id:
            raise HTTPException(status_code=403, detail="Usuário sem instituição vinculada")
        query = query.filter(AcademicClass.institution_id == user.institution_id)
    elif user.institution_id:
        query = query.filter(AcademicClass.institution_id == user.institution_id)
    if user.campus_id:
        query = query.join(AcademicClass.offering).filter_by(campus_id=user.campus_id)
    if user.role not in MANAGER_ROLES:
        staff = (
            db.query(AcademicStaff)
            .filter(
                AcademicStaff.user_id == user.id,
                AcademicStaff.institution_id == user.institution_id,
                AcademicStaff.staff_type == "professor",
                AcademicStaff.status == "ativo",
            )
            .first()
        )
        if staff is None:
            return query.filter(AcademicClass.id == "")
        query = query.filter(AcademicClass.teacher_id == staff.id)
    return query


def _get_accessible_class(db: Session, class_id: str, user: Any, *, write: bool = False) -> AcademicClass:
    academic_class = _class_query(db, user).filter(AcademicClass.id == class_id).first()
    if academic_class is None:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    if write and academic_class.status not in {"ativa", "active"}:
        raise HTTPException(status_code=409, detail="Lançamentos só podem ser feitos em turmas ativas")
    return academic_class


def _class_response(db: Session, academic_class: AcademicClass) -> dict[str, Any]:
    offering = academic_class.offering
    return {
        "id": academic_class.id,
        "class_id": academic_class.id,
        "code": academic_class.code,
        "course_name": offering.course.name,
        "course_id": offering.course_id,
        "discipline_name": offering.discipline.name,
        "discipline_id": offering.discipline_id,
        "term_name": offering.term.name,
        "term_id": offering.term_id,
        "campus_id": offering.campus_id,
        "teacher_id": academic_class.teacher_id,
        "teacher_name": academic_class.teacher.full_name if academic_class.teacher else None,
        "students_count": db.query(models.Enrollment).filter(
            models.Enrollment.academic_class_id == academic_class.id,
            models.Enrollment.institution_id == academic_class.institution_id,
            models.Enrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
        ).count(),
        "status": academic_class.status,
    }


def _class_roster(db: Session, academic_class: AcademicClass) -> list[dict[str, Any]]:
    rows = (
        db.query(models.Enrollment, models.Student)
        .join(models.Student, models.Student.id == models.Enrollment.student_id)
        .filter(
            models.Enrollment.academic_class_id == academic_class.id,
            models.Enrollment.institution_id == academic_class.institution_id,
            models.Enrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
            models.Student.institution_id == academic_class.institution_id,
        )
        .order_by(models.Student.full_name)
        .all()
    )
    return [
        {
            "enrollment_id": enrollment.id,
            "student_id": student.id,
            "full_name": student.full_name,
            "status": enrollment.status,
        }
        for enrollment, student in rows
    ]


def _get_active_enrollment(
    db: Session,
    academic_class: AcademicClass,
    enrollment_id: str,
) -> models.Enrollment:
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.id == enrollment_id,
        models.Enrollment.academic_class_id == academic_class.id,
        models.Enrollment.institution_id == academic_class.institution_id,
        models.Enrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
    ).first()
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Matrícula ativa não encontrada nesta turma")
    return enrollment


def _audit(
    db: Session,
    user: Any,
    entity: str,
    entity_id: str,
    action: str,
    changes: dict[str, Any],
) -> None:
    from app.main import add_audit

    add_audit(
        db,
        entity,
        entity_id,
        action,
        json.dumps(changes, ensure_ascii=False, sort_keys=True, default=str),
        str(user.id),
    )


def _assessment_response(assessment: AcademicAssessment) -> dict[str, Any]:
    return {
        "id": assessment.id,
        "class_id": assessment.class_id,
        "name": assessment.name,
        "description": assessment.description,
        "max_score": assessment.max_score,
        "due_date": assessment.due_date,
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at,
    }


def _get_assessment(db: Session, assessment_id: str, user: Any, *, write: bool = False) -> AcademicAssessment:
    query = db.query(AcademicAssessment).filter(AcademicAssessment.id == assessment_id)
    if user.role != "admin_global" or user.institution_id:
        query = query.filter(AcademicAssessment.institution_id == user.institution_id)
    assessment = query.first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    _get_accessible_class(db, assessment.class_id, user, write=write)
    return assessment


@router.get("/dashboard")
def professores_dashboard(
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    classes = _class_query(db, user).all()
    class_ids = [item.id for item in classes]
    grade_query = db.query(
        func.count(AcademicGrade.id),
        func.avg(AcademicGrade.score),
    ).filter(
        AcademicGrade.assessment_id.in_(
            db.query(AcademicAssessment.id).filter(AcademicAssessment.class_id.in_(class_ids or [""]))
        )
    )
    if user.institution_id:
        grade_query = grade_query.filter(AcademicGrade.institution_id == user.institution_id)
    grade_count, grade_average = grade_query.one()
    students_count = sum(len(_class_roster(db, item)) for item in classes)
    return {
        "module": "professores",
        "title": "Dashboard dos Professores",
        "stats": {
            "turmas": len(classes),
            "professores": len({item.teacher_id for item in classes if item.teacher_id}),
            "alunos_avaliados": grade_count,
            "media_geral": round(float(grade_average), 2) if grade_average is not None else 0,
            "disciplinas_ativas": len({
                item.offering.discipline_id
                for item in classes
                if item.status in {"ativa", "active"}
            }),
            "avaliacoes": db.query(AcademicAssessment).filter(
                AcademicAssessment.class_id.in_(class_ids or [""]),
            ).count(),
            "turmas_ativas": sum(item.status in {"ativa", "active"} for item in classes),
            "alunos_vinculados": students_count,
        },
        "classes": [_class_response(db, item) for item in classes],
        "teachers": [],
        "features": ["Turmas", "Frequência", "Notas", "Avaliações"],
        "user": getattr(user, "username", None),
    }


@router.get("/turmas")
def list_classes(
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    classes = _class_query(db, user).order_by(AcademicClass.code).all()
    return {"module": "professores", "items": [_class_response(db, item) for item in classes]}


@router.get("/disciplinas")
def list_disciplines(
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    classes = _class_query(db, user).all()
    items = [_class_response(db, item) for item in classes]
    return {"module": "professores", "items": items}


@router.get("/alunos")
def list_professor_students(
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    items = []
    for academic_class in _class_query(db, user).all():
        class_info = _class_response(db, academic_class)
        for student in _class_roster(db, academic_class):
            items.append({
                **student,
                "course": class_info["course_name"],
                "campus": class_info["campus_id"],
                "class_id": academic_class.id,
            })
    return {"module": "professores", "items": items}


@router.get("/turmas/{class_id}")
def get_class(
    class_id: str,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    academic_class = _get_accessible_class(db, class_id, user)
    return {"module": "professores", "class_item": _class_response(db, academic_class)}


@router.get("/turmas/{class_id}/alunos")
def list_class_students(
    class_id: str,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    academic_class = _get_accessible_class(db, class_id, user)
    return {"module": "professores", "items": _class_roster(db, academic_class)}


@router.get("/avaliacoes")
def list_assessments(
    class_id: str | None = None,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    query = db.query(AcademicAssessment)
    if user.role != "admin_global" or user.institution_id:
        query = query.filter(AcademicAssessment.institution_id == user.institution_id)
    if class_id:
        _get_accessible_class(db, class_id, user)
        query = query.filter(AcademicAssessment.class_id == class_id)
    else:
        accessible_class_ids = [item.id for item in _class_query(db, user).all()]
        query = query.filter(AcademicAssessment.class_id.in_(accessible_class_ids or [""]))
    items = query.order_by(AcademicAssessment.due_date, AcademicAssessment.name).all()
    return {"module": "professores", "items": [_assessment_response(item) for item in items]}


@router.post("/turmas/{class_id}/avaliacoes", status_code=status.HTTP_201_CREATED)
def create_assessment(
    class_id: str,
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    academic_class = _get_accessible_class(db, class_id, user, write=True)
    assessment = AcademicAssessment(
        id=uuid4().hex,
        institution_id=academic_class.institution_id,
        class_id=academic_class.id,
        **payload.model_dump(),
    )
    db.add(assessment)
    _audit(db, user, "academic_assessment", assessment.id, "created", {"class_id": class_id})
    db.commit()
    db.refresh(assessment)
    return {"module": "professores", "item": _assessment_response(assessment)}


@router.patch("/avaliacoes/{assessment_id}")
def update_assessment(
    assessment_id: str,
    payload: AssessmentUpdate,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    assessment = _get_assessment(db, assessment_id, user, write=True)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is None:
        raise HTTPException(status_code=422, detail="O nome da avaliação não pode ser nulo")
    if "max_score" in changes and changes["max_score"] is None:
        raise HTTPException(status_code=422, detail="A pontuação máxima não pode ser nula")
    new_max_score = changes.get("max_score", assessment.max_score)
    if db.query(AcademicGrade).filter(
        AcademicGrade.assessment_id == assessment.id,
        AcademicGrade.score > new_max_score,
    ).first():
        raise HTTPException(status_code=409, detail="A pontuação máxima não pode ficar abaixo de notas já lançadas")
    changed_fields = {
        key: value
        for key, value in changes.items()
        if getattr(assessment, key) != value
    }
    if changed_fields:
        for key, value in changed_fields.items():
            setattr(assessment, key, value)
        _audit(db, user, "academic_assessment", assessment.id, "updated", {"changed_fields": sorted(changed_fields)})
        db.commit()
        db.refresh(assessment)
    return {"module": "professores", "item": _assessment_response(assessment)}


@router.delete("/avaliacoes/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    assessment = _get_assessment(db, assessment_id, user, write=True)
    if db.query(AcademicGrade).filter(AcademicGrade.assessment_id == assessment.id).first():
        raise HTTPException(
            status_code=409,
            detail="Remova os lançamentos de nota individualmente antes de excluir a avaliação",
        )
    assessment_id = assessment.id
    db.delete(assessment)
    _audit(db, user, "academic_assessment", assessment_id, "deleted", {})
    db.commit()


@router.get("/avaliacoes/{assessment_id}/notas")
def list_assessment_grades(
    assessment_id: str,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    assessment = _get_assessment(db, assessment_id, user)
    grades = {
        grade.enrollment_id: grade
        for grade in db.query(AcademicGrade).filter(
            AcademicGrade.assessment_id == assessment.id,
        ).all()
    }
    items = []
    for roster_item in _class_roster(db, assessment.academic_class):
        grade = grades.get(roster_item["enrollment_id"])
        items.append({
            **roster_item,
            "grade_id": grade.id if grade else None,
            "score": grade.score if grade else None,
            "comment": grade.comment if grade else None,
            "updated_at": grade.updated_at if grade else None,
        })
    return {"module": "professores", "items": items}


@router.put("/avaliacoes/{assessment_id}/notas/{enrollment_id}")
def save_grade(
    assessment_id: str,
    enrollment_id: str,
    payload: GradeInput,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    assessment = _get_assessment(db, assessment_id, user, write=True)
    if payload.score > assessment.max_score:
        raise HTTPException(status_code=422, detail="A nota excede a pontuação máxima da avaliação")
    enrollment = _get_active_enrollment(db, assessment.academic_class, enrollment_id)
    grade = db.query(AcademicGrade).filter(
        AcademicGrade.assessment_id == assessment.id,
        AcademicGrade.enrollment_id == enrollment.id,
    ).first()
    action = "updated" if grade else "created"
    if grade is None:
        grade = AcademicGrade(
            id=uuid4().hex,
            institution_id=assessment.institution_id,
            assessment_id=assessment.id,
            enrollment_id=enrollment.id,
            score=payload.score,
            comment=payload.comment,
        )
        db.add(grade)
    else:
        grade.score = payload.score
        grade.comment = payload.comment
    _audit(
        db,
        user,
        "academic_grade",
        grade.id,
        action,
        {"assessment_id": assessment.id, "enrollment_id": enrollment.id},
    )
    db.commit()
    db.refresh(grade)
    return {
        "module": "professores",
        "grade": {
            "id": grade.id,
            "assessment_id": grade.assessment_id,
            "enrollment_id": grade.enrollment_id,
            "score": grade.score,
            "comment": grade.comment,
            "updated_at": grade.updated_at,
        },
    }


@router.delete("/avaliacoes/{assessment_id}/notas/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(
    assessment_id: str,
    enrollment_id: str,
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    assessment = _get_assessment(db, assessment_id, user, write=True)
    _get_active_enrollment(db, assessment.academic_class, enrollment_id)
    grade = db.query(AcademicGrade).filter(
        AcademicGrade.assessment_id == assessment.id,
        AcademicGrade.enrollment_id == enrollment_id,
    ).first()
    if grade is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    grade_id = grade.id
    db.delete(grade)
    _audit(db, user, "academic_grade", grade_id, "deleted", {"assessment_id": assessment.id})
    db.commit()


@router.get("/turmas/{class_id}/frequencia")
def list_attendance(
    class_id: str,
    attendance_date: date = Query(...),
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    academic_class = _get_accessible_class(db, class_id, user)
    attendance = {
        item.enrollment_id: item
        for item in db.query(AcademicAttendance).filter(
            AcademicAttendance.class_id == academic_class.id,
            AcademicAttendance.attendance_date == attendance_date,
        ).all()
    }
    items = []
    for roster_item in _class_roster(db, academic_class):
        record = attendance.get(roster_item["enrollment_id"])
        items.append({
            **roster_item,
            "attendance_id": record.id if record else None,
            "status": record.status if record else None,
            "note": record.note if record else None,
        })
    return {"module": "professores", "attendance_date": attendance_date, "items": items}


@router.put("/turmas/{class_id}/frequencia/{enrollment_id}")
def save_attendance(
    class_id: str,
    enrollment_id: str,
    payload: AttendanceInput,
    attendance_date: date = Query(...),
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    academic_class = _get_accessible_class(db, class_id, user, write=True)
    enrollment = _get_active_enrollment(db, academic_class, enrollment_id)
    record = db.query(AcademicAttendance).filter(
        AcademicAttendance.class_id == academic_class.id,
        AcademicAttendance.enrollment_id == enrollment.id,
        AcademicAttendance.attendance_date == attendance_date,
    ).first()
    action = "updated" if record else "created"
    if record is None:
        record = AcademicAttendance(
            id=uuid4().hex,
            institution_id=academic_class.institution_id,
            class_id=academic_class.id,
            enrollment_id=enrollment.id,
            attendance_date=attendance_date,
            status=payload.status,
            note=payload.note,
        )
        db.add(record)
    else:
        record.status = payload.status
        record.note = payload.note
    _audit(
        db,
        user,
        "academic_attendance",
        record.id,
        action,
        {"class_id": academic_class.id, "enrollment_id": enrollment.id, "date": attendance_date},
    )
    db.commit()
    db.refresh(record)
    return {
        "module": "professores",
        "attendance": {
            "id": record.id,
            "class_id": record.class_id,
            "enrollment_id": record.enrollment_id,
            "attendance_date": record.attendance_date,
            "status": record.status,
            "note": record.note,
        },
    }


@router.delete("/turmas/{class_id}/frequencia/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    class_id: str,
    enrollment_id: str,
    attendance_date: date = Query(...),
    db: Session = Depends(get_db),
    user: Any = ProfessorUser,
):
    academic_class = _get_accessible_class(db, class_id, user, write=True)
    _get_active_enrollment(db, academic_class, enrollment_id)
    record = db.query(AcademicAttendance).filter(
        AcademicAttendance.class_id == academic_class.id,
        AcademicAttendance.enrollment_id == enrollment_id,
        AcademicAttendance.attendance_date == attendance_date,
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Registro de frequência não encontrado")
    record_id = record.id
    db.delete(record)
    _audit(
        db,
        user,
        "academic_attendance",
        record_id,
        "deleted",
        {"class_id": academic_class.id, "attendance_date": attendance_date},
    )
    db.commit()
