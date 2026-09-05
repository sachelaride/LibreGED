from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash
import uuid

db = SessionLocal()
existing = db.query(User).filter_by(username='recepcao').first()
if not existing:
    u = User(
        id=str(uuid.uuid4()),
        username='recepcao',
        hashed_password=get_password_hash('recepcao'),
        role='recepcao'
    )
    db.add(u)
    db.commit()
    print("User recepcao created")
else:
    print("User recepcao already exists")
