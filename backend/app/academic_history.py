from typing import Any

from sqlalchemy.orm import Session

from app import models
from app.models_academic_catalog import AcademicCurriculum


def current_enrollment_academic_link(
    db: Session,
    enrollment: models.Enrollment,
) -> tuple[dict[str, Any], str]:
    academic_class = enrollment.academic_class
    if (
        academic_class is not None
        and academic_class.institution_id == enrollment.institution_id
        and academic_class.offering.institution_id == enrollment.institution_id
        and academic_class.offering.course.institution_id == enrollment.institution_id
        and academic_class.offering.discipline.institution_id == enrollment.institution_id
        and academic_class.offering.term.institution_id == enrollment.institution_id
    ):
        offering = academic_class.offering
        term = offering.term
        curriculum = (
            db.query(AcademicCurriculum)
            .filter(
                AcademicCurriculum.institution_id == enrollment.institution_id,
                AcademicCurriculum.course_id == offering.course_id,
                AcademicCurriculum.status == "ativa",
                AcademicCurriculum.effective_from <= term.starts_on,
            )
            .order_by(AcademicCurriculum.effective_from.desc())
            .first()
        )
        return {
            "course_id": offering.course_id,
            "course_name": offering.course.name,
            "curriculum_id": curriculum.id if curriculum else None,
            "curriculum_version": curriculum.version if curriculum else None,
            "discipline_id": offering.discipline_id,
            "discipline_name": offering.discipline.name,
            "class_id": academic_class.id,
            "class_code": academic_class.code,
            "term_id": offering.term_id,
            "term_code": term.code,
            "term_name": term.name,
            "term_starts_on": term.starts_on.isoformat(),
            "term_ends_on": term.ends_on.isoformat(),
            "campus_id": offering.campus_id,
        }, "current_catalog"

    link = {
        "course_name": enrollment.course_name,
        "class_name": enrollment.class_name,
        "year": enrollment.year,
        "campus_id": enrollment.campus_id,
    }
    return {
        key: value
        for key, value in link.items()
        if value is not None
    }, "legacy_enrollment"
