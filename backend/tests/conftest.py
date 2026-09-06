import os
import pytest
os.environ["ENVIRONMENT"] = "test"
from app.database import engine
from app import models
from app import storage
from app.main import app
from app.auth import get_current_active_user

def override_get_current_active_user():
    return models.User(
        id="test-admin-id",
        username="admin_test",
        hashed_password="...",
        role="admin_global",
        institution_id=None
    )

app.dependency_overrides[get_current_active_user] = override_get_current_active_user


@pytest.fixture(autouse=True)
def setup_db():
    """Clear all tables before each test."""
    existing_files = set(storage.STORAGE_ROOT.iterdir())
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    
    # Criar a tabela virtual FTS5 para o SQLite durante os testes
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS ged_documents_fts USING fts5(
                document_id, title, content, indices_data
            );
        """))
    yield
    models.Base.metadata.drop_all(bind=engine)
    for created_file in set(storage.STORAGE_ROOT.iterdir()) - existing_files:
        if created_file.is_file():
            created_file.unlink()
