import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TYPE geddocumentstatus ADD VALUE IF NOT EXISTS 'QUARENTENA';"))
        conn.commit()
        print("Enum updated successfully.")
    except Exception as e:
        print(f"Error: {e}")
