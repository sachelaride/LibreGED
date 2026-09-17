import os
import pytest
os.environ["ENVIRONMENT"] = "test"
from app.database import engine, SessionLocal
from app import models
from app import storage
from app.main import app
from app.auth import get_current_active_user

def override_get_current_active_user():
    db = SessionLocal()
    try:
        institution = db.query(models.Institution).first()
        institution_id = institution.id if institution else None
    finally:
        db.close()
    return models.User(
        id="test-admin-id",
        username="admin_test",
        hashed_password="...",
        role="admin_global",
        institution_id=institution_id,
    )

app.dependency_overrides[get_current_active_user] = override_get_current_active_user


@pytest.fixture(autouse=True)
def setup_db(request):
    """Clear all tables before each test."""
    dependency_overrides = app.dependency_overrides.copy()
    if request.module.__name__ in {"test_admin", "test_filewatch"}:
        yield
        app.dependency_overrides.clear()
        app.dependency_overrides.update(dependency_overrides)
        return

    existing_files = set(storage.STORAGE_ROOT.iterdir())
    models.Base.metadata.drop_all(bind=engine, checkfirst=True)
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(
        models.User(
            id="test-admin-id",
            username="admin_test",
            hashed_password="...",
            role="admin_global",
        )
    )
    db.commit()
    db.close()
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(dependency_overrides)
        models.Base.metadata.drop_all(bind=engine, checkfirst=True)
        for created_file in set(storage.STORAGE_ROOT.iterdir()) - existing_files:
            if created_file.is_file():
                created_file.unlink()
