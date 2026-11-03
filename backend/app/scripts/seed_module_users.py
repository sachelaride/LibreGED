r"""Seed demo users for each operational module.

Run from backend:
    ..\.venv\Scripts\python.exe -m app.scripts.seed_module_users
"""

from __future__ import annotations

import uuid

from app import auth, models
from app.database import SessionLocal
import app.models_ged  # noqa: F401 - register GED model metadata before querying
import app.models_ged_config  # noqa: F401
import app.models_workflow  # noqa: F401
import app.models_representation  # noqa: F401
import app.models_academic_dossier  # noqa: F401

USERS = [
    {"username": "admin", "password": "admin123", "role": "admin_global"},
    {"username": "secretaria", "password": "secretaria123", "role": "secretaria"},
    {"username": "professor", "password": "professor123", "role": "professor"},
    {"username": "ged", "password": "ged123", "role": "auditor"},
    {"username": "financeiro", "password": "financeiro123", "role": "operador"},
    {"username": "coordenacao", "password": "coordenacao123", "role": "coordenador"},
    {"username": "tutor", "password": "tutor123", "role": "tutor"},
    {"username": "aluno", "password": "aluno123", "role": "aluno"},
]


def ensure_institution(db):
    institution = db.query(models.Institution).first()
    if institution is None:
        institution = models.Institution(
            id=str(uuid.uuid4()),
            name="Instituto de Ensino Superior EduGED",
            cnpj="00.000.000/0001-91",
            legal_name="EduGED Libre Instituição de Ensino Superior LTDA",
        )
        db.add(institution)
        db.flush()
    return institution


def seed() -> None:
    db = SessionLocal()
    try:
        institution = ensure_institution(db)

        for user_data in USERS:
            existing = db.query(models.User).filter(models.User.username == user_data["username"]).first()
            if existing:
                continue
            user = models.User(
                id=str(uuid.uuid4()),
                username=user_data["username"],
                hashed_password=auth.get_password_hash(user_data["password"]),
                role=user_data["role"],
                institution_id=institution.id,
                campus_id=None,
                is_active=True,
            )
            db.add(user)

        db.commit()
        print("Seeded demo module users:")
        for user_data in USERS:
            print(f"- {user_data['username']} / {user_data['password']} / {user_data['role']}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
