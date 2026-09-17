import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, event
from sqlalchemy.orm import Session
from app.models import Base, utc_now
from app.security_utils import decrypt_secret, encrypt_secret


class StorageRule(Base):
    __tablename__ = "ged_storage_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    document_type_id = Column(String, nullable=True)  # Optional link to a document type

    storage_type = Column(String, default="Local")
    base_path = Column(String, nullable=False)

    max_files_per_folder = Column(Integer, default=10000)
    max_gb_per_folder = Column(Float, default=100.0)

    enable_duplication = Column(Boolean, default=False)
    secondary_storage_type = Column(String, nullable=True)
    secondary_base_path = Column(String, nullable=True)

    network_domain = Column(String, nullable=True)
    network_user = Column(String, nullable=True)
    _network_password = Column("network_password", String, nullable=True)

    current_file_count = Column(Integer, default=0)
    current_size_bytes = Column(Integer, default=0)

    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    @staticmethod
    def _encrypt_password(value: str | None) -> str | None:
        if value is None:
            return None
        raw_value = str(value).strip()
        if not raw_value:
            return None
        if raw_value.startswith("gAAAA"):
            return raw_value
        return encrypt_secret(raw_value)

    @staticmethod
    def _decrypt_password(value: str | None) -> str | None:
        if value is None:
            return None
        raw_value = str(value).strip()
        if not raw_value:
            return None
        if raw_value.startswith("gAAAA"):
            try:
                return decrypt_secret(raw_value)
            except ValueError:
                return raw_value
        return raw_value

    @property
    def network_password(self) -> str | None:
        return self._decrypt_password(self._network_password)

    @network_password.setter
    def network_password(self, value: str | None) -> None:
        self._network_password = self._encrypt_password(value)


@event.listens_for(Session, "before_flush", propagate=True)
def _encrypt_storage_rule_password_before_flush(session, flush_context, instances):
    for instance in list(session.dirty) + list(session.new):
        if not isinstance(instance, StorageRule):
            continue
        if instance._network_password is None:
            continue
        if instance._network_password.startswith("gAAAA"):
            continue
        instance._network_password = instance._encrypt_password(instance._network_password)
