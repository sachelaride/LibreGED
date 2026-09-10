from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("EduGED Libre requires PostgreSQL; configure DATABASE_URL with a postgresql+psycopg URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
