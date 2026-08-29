import pytest
from sqlalchemy import event
from app.database import engine, SessionLocal
from app import models


@pytest.fixture(autouse=True)
def setup_db():
    """Clear all tables before each test."""
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)
