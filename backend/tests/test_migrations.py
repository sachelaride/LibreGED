import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

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
    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
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
