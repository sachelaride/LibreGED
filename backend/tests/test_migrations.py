import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from app.config import settings

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
import psycopg


BACKEND_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_CONFIG = BACKEND_ROOT / "alembic.ini"
EXPECTED_TABLES = {
    "alembic_version",
    "audit_events",
    "ged_documents",
    "ged_document_categories",
    "enrollments",
    "guardians",
    "institutions",
    "academic_courses",
    "academic_departments",
    "academic_disciplines",
    "academic_terms",
    "academic_curricula",
    "academic_curriculum_disciplines",
    "academic_curriculum_equivalences",
    "academic_curriculum_elective_groups",
    "academic_curriculum_elective_disciplines",
    "academic_curriculum_prerequisites",
    "academic_credit_recognitions",
    "institution_transcript_profiles",
    "course_transcript_profiles",
    "student_course_transcript_profiles",
    "academic_staff",
    "academic_coordinator_assignments",
    "academic_coordination_actions",
    "academic_assessments",
    "academic_grades",
    "academic_attendance",
    "academic_sectors",
    "academic_offerings",
    "academic_rooms",
    "academic_classes",
    "academic_class_schedules",
    "ged_schema_versions",
    "students",
    "users",
}


def run_alembic(database_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_CONFIG), *arguments],
        cwd=BACKEND_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_migration_upgrade_matches_models_and_downgrades_cleanly():
    base_url = settings.DATABASE_URL
    if not base_url or not base_url.startswith("postgresql"):
        raise RuntimeError("TEST_DATABASE_URL must point to PostgreSQL")

    base = make_url(base_url)
    database_name = f"eduged_libre_migration_{uuid4().hex[:12]}"
    database_url = base.set(database=database_name).render_as_string(hide_password=False)
    admin_url = base.set(database="postgres").render_as_string(hide_password=False)
    admin_url = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)

    with psycopg.connect(admin_url, autocommit=True) as admin_connection:
        admin_connection.execute(f'CREATE DATABASE "{database_name}"')

    try:
        run_alembic(database_url, "upgrade", "head")

        engine = create_engine(database_url)
        try:
            assert EXPECTED_TABLES.issubset(set(inspect(engine).get_table_names()))
            staff_columns = {column["name"] for column in inspect(engine).get_columns("academic_staff")}
            assert {"transcript_title", "transcript_cpf", "transcript_lattes"} <= staff_columns
            assignment_columns = {
                column["name"]
                for column in inspect(engine).get_columns("academic_coordinator_assignments")
            }
            assert {
                "coordinator_id",
                "course_id",
                "campus_id",
                "starts_on",
                "ends_on",
            } <= assignment_columns
            assert "user_id" in staff_columns
            action_columns = {
                column["name"]
                for column in inspect(engine).get_columns("academic_coordination_actions")
            }
            assert {
                "institution_id",
                "student_id",
                "course_id",
                "campus_id",
                "issue",
                "priority",
                "status",
                "created_by",
                "resolved_by",
                "resolved_at",
            } <= action_columns
        finally:
            engine.dispose()

        check_result = run_alembic(database_url, "check")
        assert "No new upgrade operations detected" in check_result.stdout

        try:
            run_alembic(database_url, "downgrade", "base")
        except subprocess.CalledProcessError as e:
            print("DOWNGRADE FAILED WITH STDERR:")
            print(e.stderr)
            raise

        engine = create_engine(database_url)
        try:
            assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
        finally:
            engine.dispose()
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin_connection:
            admin_connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
