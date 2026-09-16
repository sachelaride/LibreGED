from pathlib import Path

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine
from app.storage import STORAGE_ROOT

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def liveness():
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(response: Response):
    checks = {
        "database": _database_ready(),
        "storage": _storage_ready(),
    }
    ready = all(checks.values())
    if not ready:
        response.status_code = 503
    return {"status": "ok" if ready else "degraded", "checks": checks}


def _database_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def _storage_ready() -> bool:
    try:
        root = Path(STORAGE_ROOT).resolve()
        return root.is_dir() and root.exists() and _has_write_access(root)
    except OSError:
        return False


def _has_write_access(root: Path) -> bool:
    probe = root / ".healthcheck"
    try:
        probe.touch(exist_ok=True)
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False
