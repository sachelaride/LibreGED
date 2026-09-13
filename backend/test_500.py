import sys
import traceback

try:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import SessionLocal
    from app.models import User
    from app.auth import create_access_token

    client = TestClient(app)
    db = SessionLocal()
    user = db.query(User).filter_by(role="admin_global").first()
    if not user:
        print("No admin_global user found")
        sys.exit(1)
        
    token = create_access_token(data={"sub": user.username})
    headers = {"Authorization": f"Bearer {token}"}

    print("Testing /api/indices...")
    try:
        response = client.get("/api/indices?page=1&size=100", headers=headers)
        print("Indices:", response.status_code, response.text)
    except Exception as e:
        traceback.print_exc()

    print("\nTesting /api/admin/settings...")
    try:
        response = client.get("/api/admin/settings", headers=headers)
        print("Settings:", response.status_code, response.text)
    except Exception as e:
        traceback.print_exc()

    print("\nTesting /api/admin/ingestions...")
    try:
        response = client.get("/api/admin/ingestions", headers=headers)
        print("Ingestions:", response.status_code, response.text)
    except Exception as e:
        traceback.print_exc()
        
except Exception as e:
    traceback.print_exc()
