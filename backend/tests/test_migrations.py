import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import create_engine, inspect


BACKEND_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_CONFIG = BACKEND_ROOT / "alembic.ini"
EXPECTED_TABLES = {
    "alembic_version",
    "audit_events",
    "document_versions",
    "documents",
    "enrollments",
    "guardians",
    "institutions",
    "schema_versions",
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
    database_path = BACKEND_ROOT / f"migration-test-{uuid4()}.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

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
        database_path.unlink(missing_ok=True)
