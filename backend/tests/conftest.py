import pytest
from app.database import engine
from app import models
from app import storage


@pytest.fixture(autouse=True)
def setup_db():
    """Clear all tables before each test."""
    existing_files = set(storage.STORAGE_ROOT.iterdir())
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)
    for created_file in set(storage.STORAGE_ROOT.iterdir()) - existing_files:
        if created_file.is_file():
            created_file.unlink()
