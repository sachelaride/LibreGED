from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Index,
    JSON,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models import Base, utc_now


class InstitutionTranscriptProfile(Base):
    __tablename__ = "institution_transcript_profiles"

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(
        String,
        ForeignKey("institutions.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution")


class CourseTranscriptProfile(Base):
    __tablename__ = "course_transcript_profiles"

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    course_id = Column(
        String,
        ForeignKey("academic_courses.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution")
    course = relationship("AcademicCourse")


class StudentCourseTranscriptProfile(Base):
    __tablename__ = "student_course_transcript_profiles"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "course_id",
            name="uq_student_course_transcript_profile",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("academic_courses.id"), nullable=False, index=True)
    entry_date = Column(Date, nullable=False)
    access_form = Column(String, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution")
    student = relationship("Student")
    course = relationship("AcademicCourse")


class AcademicCourse(Base):
    __tablename__ = "academic_courses"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_academic_course_code"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=True, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False, index=True)
    degree = Column(String, nullable=False)
    modality = Column(String, nullable=False)
    duration_periods = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="ativo")

    institution = relationship("Institution")
    campus = relationship("Campus")


class AcademicDepartment(Base):
    __tablename__ = "academic_departments"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_academic_department_code"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=True, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="ativo")

    institution = relationship("Institution")
    campus = relationship("Campus")


class AcademicSector(Base):
    __tablename__ = "academic_sectors"
    __table_args__ = (
        UniqueConstraint("department_id", "code", name="uq_academic_sector_code"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    department_id = Column(String, ForeignKey("academic_departments.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="ativo")

    institution = relationship("Institution")
    department = relationship("AcademicDepartment")


class AcademicDiscipline(Base):
    __tablename__ = "academic_disciplines"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_academic_discipline_code"),
        CheckConstraint("workload_hours > 0", name="ck_academic_discipline_workload"),
        CheckConstraint("credits >= 0", name="ck_academic_discipline_credits"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False, index=True)
    workload_hours = Column(Integer, nullable=False)
    credits = Column(Integer, nullable=False, default=0)
    syllabus = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ativo")

    institution = relationship("Institution")


class AcademicTerm(Base):
    __tablename__ = "academic_terms"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_academic_term_code"),
        CheckConstraint("ends_on >= starts_on", name="ck_academic_term_dates"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="planejado")

    institution = relationship("Institution")


class AcademicCurriculum(Base):
    __tablename__ = "academic_curricula"
    __table_args__ = (
        UniqueConstraint("course_id", "version", name="uq_academic_curriculum_version"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("academic_courses.id"), nullable=False, index=True)
    version = Column(String, nullable=False)
    effective_from = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="ativa")

    institution = relationship("Institution")
    course = relationship("AcademicCourse")


class AcademicCurriculumDiscipline(Base):
    __tablename__ = "academic_curriculum_disciplines"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "discipline_id", name="uq_academic_curriculum_discipline"),
        CheckConstraint("term_number > 0", name="ck_academic_curriculum_term_number"),
    )

    id = Column(String, primary_key=True, index=True)
    curriculum_id = Column(String, ForeignKey("academic_curricula.id"), nullable=False, index=True)
    discipline_id = Column(String, ForeignKey("academic_disciplines.id"), nullable=False, index=True)
    term_number = Column(Integer, nullable=False)
    is_required = Column(Boolean, nullable=False, default=True)

    curriculum = relationship("AcademicCurriculum")
    discipline = relationship("AcademicDiscipline")


class AcademicCurriculumPrerequisite(Base):
    __tablename__ = "academic_curriculum_prerequisites"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_discipline_id",
            "prerequisite_curriculum_discipline_id",
            name="uq_academic_curriculum_prerequisite",
        ),
        CheckConstraint(
            "curriculum_discipline_id != prerequisite_curriculum_discipline_id",
            name="ck_academic_curriculum_prerequisite_not_self",
        ),
        Index("ix_acad_cur_prereq_target", "curriculum_discipline_id"),
        Index("ix_acad_cur_prereq_source", "prerequisite_curriculum_discipline_id"),
    )

    id = Column(String, primary_key=True, index=True)
    curriculum_discipline_id = Column(
        String,
        ForeignKey("academic_curriculum_disciplines.id"),
        nullable=False,
    )
    prerequisite_curriculum_discipline_id = Column(
        String,
        ForeignKey("academic_curriculum_disciplines.id"),
        nullable=False,
    )


class AcademicCurriculumEquivalence(Base):
    __tablename__ = "academic_curriculum_equivalences"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_discipline_id",
            "equivalent_discipline_id",
            name="uq_academic_curriculum_equivalence",
        ),
        CheckConstraint(
            "curriculum_discipline_id != equivalent_discipline_id",
            name="ck_academic_curriculum_equivalence_not_self",
        ),
        Index("ix_acad_cur_equivalence_target", "curriculum_discipline_id"),
        Index("ix_acad_cur_equivalence_source", "equivalent_discipline_id"),
    )

    id = Column(String, primary_key=True, index=True)
    curriculum_discipline_id = Column(
        String,
        ForeignKey("academic_curriculum_disciplines.id"),
        nullable=False,
    )
    equivalent_discipline_id = Column(
        String,
        ForeignKey("academic_disciplines.id"),
        nullable=False,
    )


class AcademicCurriculumElectiveGroup(Base):
    __tablename__ = "academic_curriculum_elective_groups"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "code", name="uq_academic_curriculum_elective_group"),
        CheckConstraint("minimum_credits > 0", name="ck_academic_curriculum_elective_min_credits"),
    )

    id = Column(String, primary_key=True, index=True)
    curriculum_id = Column(String, ForeignKey("academic_curricula.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    minimum_credits = Column(Integer, nullable=False)


class AcademicCurriculumElectiveDiscipline(Base):
    __tablename__ = "academic_curriculum_elective_disciplines"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_discipline_id",
            name="uq_academic_curriculum_elective_discipline",
        ),
        UniqueConstraint(
            "elective_group_id",
            "curriculum_discipline_id",
            name="uq_academic_curriculum_elective_group_discipline",
        ),
        Index("ix_acad_cur_elective_group", "elective_group_id"),
        Index("ix_acad_cur_elective_link", "curriculum_discipline_id"),
    )

    id = Column(String, primary_key=True, index=True)
    elective_group_id = Column(
        String,
        ForeignKey("academic_curriculum_elective_groups.id"),
        nullable=False,
    )
    curriculum_discipline_id = Column(
        String,
        ForeignKey("academic_curriculum_disciplines.id"),
        nullable=False,
    )


class AcademicCreditRecognition(Base):
    __tablename__ = "academic_credit_recognitions"
    __table_args__ = (
        CheckConstraint(
            "workload_hours > 0",
            name="ck_academic_credit_recognition_workload",
        ),
        CheckConstraint(
            "credits >= 0",
            name="ck_academic_credit_recognition_credits",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_academic_credit_recognition_status",
        ),
        Index("ix_acad_credit_recognition_student", "student_id", "course_id"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("academic_courses.id"), nullable=False, index=True)
    curriculum_discipline_id = Column(
        String,
        ForeignKey("academic_curriculum_disciplines.id"),
        nullable=False,
        index=True,
    )
    source_institution = Column(String, nullable=False)
    source_course = Column(String, nullable=False)
    source_discipline = Column(String, nullable=False)
    workload_hours = Column(Integer, nullable=False)
    credits = Column(Integer, nullable=False, default=0)
    request_note = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)
    decision_note = Column(String, nullable=True)
    reviewer_id = Column(String, nullable=True)
    requested_at = Column(DateTime, nullable=False, default=utc_now)
    decided_at = Column(DateTime, nullable=True)

    institution = relationship("Institution")
    student = relationship("Student")
    course = relationship("AcademicCourse")
    curriculum_discipline = relationship("AcademicCurriculumDiscipline")


class AcademicStaff(Base):
    __tablename__ = "academic_staff"
    __table_args__ = (
        UniqueConstraint("institution_id", "email", name="uq_academic_staff_email"),
        UniqueConstraint("institution_id", "staff_code", name="uq_academic_staff_code"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    staff_code = Column(String, nullable=False)
    full_name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False)
    staff_type = Column(String, nullable=False, index=True)
    transcript_title = Column(String(40), nullable=True)
    transcript_cpf = Column(String(11), nullable=True)
    transcript_lattes = Column(String(255), nullable=True)
    status = Column(String, nullable=False, default="ativo")

    institution = relationship("Institution")
    campus = relationship("Campus")


class AcademicCoordinatorAssignment(Base):
    __tablename__ = "academic_coordinator_assignments"
    __table_args__ = (
        CheckConstraint(
            "ends_on >= starts_on",
            name="ck_academic_coordinator_assignment_dates",
        ),
        Index(
            "ix_academic_coord_assignment_scope",
            "course_id",
            "campus_id",
            "starts_on",
            "ends_on",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    coordinator_id = Column(String, ForeignKey("academic_staff.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("academic_courses.id"), nullable=False, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=False, index=True)
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=False)

    institution = relationship("Institution")
    coordinator = relationship("AcademicStaff")
    course = relationship("AcademicCourse")
    campus = relationship("Campus")


class AcademicCoordinationAction(Base):
    __tablename__ = "academic_coordination_actions"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('alta', 'média', 'baixa')",
            name="ck_academic_coordination_action_priority",
        ),
        CheckConstraint(
            "status IN ('em andamento', 'aguardando', 'concluída')",
            name="ck_academic_coordination_action_status",
        ),
        Index(
            "ix_academic_coordination_action_scope",
            "institution_id",
            "course_id",
            "campus_id",
            "status",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("academic_courses.id"), nullable=False, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=False, index=True)
    issue = Column(String(500), nullable=False)
    priority = Column(String(20), nullable=False, default="média")
    status = Column(String(30), nullable=False, default="em andamento", index=True)
    responsible = Column(String(160), nullable=False)
    deadline = Column(Date, nullable=True)
    category = Column(String(120), nullable=False)
    created_by = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    resolved_by = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    resolved_at = Column(DateTime, nullable=True)

    institution = relationship("Institution")
    student = relationship("Student")
    course = relationship("AcademicCourse")
    campus = relationship("Campus")
    creator = relationship("User", foreign_keys=[created_by])
    resolver = relationship("User", foreign_keys=[resolved_by])


class AcademicOffering(Base):
    __tablename__ = "academic_offerings"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "discipline_id",
            "term_id",
            "campus_id",
            name="uq_academic_offering_scope",
        ),
        CheckConstraint("capacity > 0", name="ck_academic_offering_capacity"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("academic_courses.id"), nullable=False, index=True)
    discipline_id = Column(String, ForeignKey("academic_disciplines.id"), nullable=False, index=True)
    term_id = Column(String, ForeignKey("academic_terms.id"), nullable=False, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=False, index=True)
    capacity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="aberta")

    institution = relationship("Institution")
    course = relationship("AcademicCourse")
    discipline = relationship("AcademicDiscipline")
    term = relationship("AcademicTerm")
    campus = relationship("Campus")


class AcademicRoom(Base):
    __tablename__ = "academic_rooms"
    __table_args__ = (
        UniqueConstraint("campus_id", "code", name="uq_academic_room_code"),
        CheckConstraint("capacity > 0", name="ck_academic_room_capacity"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    campus_id = Column(String, ForeignKey("campuses.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    room_type = Column(String, nullable=False, default="sala")
    is_active = Column(Boolean, nullable=False, default=True)

    institution = relationship("Institution")
    campus = relationship("Campus")


class AcademicClass(Base):
    __tablename__ = "academic_classes"
    __table_args__ = (
        UniqueConstraint("offering_id", "code", name="uq_academic_class_code"),
        CheckConstraint("capacity > 0", name="ck_academic_class_capacity"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    offering_id = Column(String, ForeignKey("academic_offerings.id"), nullable=False, index=True)
    code = Column(String, nullable=False)
    teacher_id = Column(String, ForeignKey("academic_staff.id"), nullable=True, index=True)
    coordinator_id = Column(String, ForeignKey("academic_staff.id"), nullable=True, index=True)
    capacity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="planejada")

    institution = relationship("Institution")
    offering = relationship("AcademicOffering")
    teacher = relationship("AcademicStaff", foreign_keys=[teacher_id])
    coordinator = relationship("AcademicStaff", foreign_keys=[coordinator_id])


class AcademicClassSchedule(Base):
    __tablename__ = "academic_class_schedules"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_academic_schedule_times"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    class_id = Column(String, ForeignKey("academic_classes.id"), nullable=False, index=True)
    room_id = Column(String, ForeignKey("academic_rooms.id"), nullable=True, index=True)
    weekday = Column(Integer, nullable=False)
    starts_at = Column(Time, nullable=False)
    ends_at = Column(Time, nullable=False)

    institution = relationship("Institution")
    academic_class = relationship("AcademicClass")
    room = relationship("AcademicRoom")


class AcademicAssessment(Base):
    __tablename__ = "academic_assessments"
    __table_args__ = (
        CheckConstraint("max_score > 0", name="ck_academic_assessment_max_score"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    class_id = Column(String, ForeignKey("academic_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    description = Column(String(2000), nullable=True)
    max_score = Column(Float, nullable=False)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution")
    academic_class = relationship("AcademicClass")
    grades = relationship("AcademicGrade", cascade="all, delete-orphan", passive_deletes=True)


class AcademicGrade(Base):
    __tablename__ = "academic_grades"
    __table_args__ = (
        UniqueConstraint("assessment_id", "enrollment_id", name="uq_academic_grade_assessment_enrollment"),
        CheckConstraint("score >= 0", name="ck_academic_grade_score"),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    assessment_id = Column(String, ForeignKey("academic_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id = Column(String, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    comment = Column(String(2000), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution")
    assessment = relationship("AcademicAssessment")
    enrollment = relationship("Enrollment")


class AcademicAttendance(Base):
    __tablename__ = "academic_attendance"
    __table_args__ = (
        UniqueConstraint(
            "class_id",
            "enrollment_id",
            "attendance_date",
            name="uq_academic_attendance_class_enrollment_date",
        ),
        CheckConstraint(
            "status IN ('present', 'absent', 'justified', 'remote')",
            name="ck_academic_attendance_status",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False, index=True)
    class_id = Column(String, ForeignKey("academic_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id = Column(String, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False)
    note = Column(String(1000), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution")
    academic_class = relationship("AcademicClass")
    enrollment = relationship("Enrollment")
