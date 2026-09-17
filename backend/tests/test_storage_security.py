from sqlalchemy import text

from app.database import SessionLocal
from app.models_storage import StorageRule
from app.security_utils import decrypt_secret


def test_storage_rule_network_password_is_encrypted_at_rest():
    db = SessionLocal()
    try:
        rule = StorageRule(
            name="storage-prod",
            base_path="prod_01",
            network_password="SuperSecretPassword!123",
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        raw_value = db.execute(
            text("SELECT network_password FROM ged_storage_rules WHERE id = :rule_id"),
            {"rule_id": rule.id},
        ).scalar_one()

        assert raw_value != "SuperSecretPassword!123"
        assert raw_value.startswith("gAAAA")
        assert decrypt_secret(raw_value) == "SuperSecretPassword!123"

        reloaded = db.query(StorageRule).filter(StorageRule.id == rule.id).one()
        assert reloaded.network_password == "SuperSecretPassword!123"
    finally:
        db.close()
