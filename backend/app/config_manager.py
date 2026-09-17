import json
from typing import Dict, Any

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._cache = {}
        return cls._instance

    def get_settings(self, db, institution_id: str) -> Dict[str, Any]:
        """
        Retorna as configurações da instituição usando o cache em memória (Hot Reload).
        Se não estiver no cache, busca do banco de dados.
        """
        if institution_id in self._cache:
            return self._cache[institution_id]
            
        from app.models import InstitutionSettings
        settings = db.query(InstitutionSettings).filter(InstitutionSettings.institution_id == institution_id).first()
        
        if settings:
            config_dict = {
                "max_upload_size_mb": settings.max_upload_size_mb,
                "allowed_mime_types": settings.allowed_mime_types,
                # Older rows may contain NULL because these columns were added
                # as nullable; missing security settings must fail closed.
                "antimalware_enabled": (
                    True if settings.antimalware_enabled is None
                    else settings.antimalware_enabled
                ),
                "quarantine_enabled": (
                    True if settings.quarantine_enabled is None
                    else settings.quarantine_enabled
                ),
                "quarantine_policy": settings.quarantine_policy or "manual",
            }
        else:
            # Secure defaults when settings have not been provisioned yet.
            config_dict = {
                "max_upload_size_mb": 10,
                "allowed_mime_types": "application/pdf,image/png,image/jpeg",
                "antimalware_enabled": True,
                "quarantine_enabled": True,
                "quarantine_policy": "manual"
            }
            
        self._cache[institution_id] = config_dict
        return config_dict

    def invalidate(self, institution_id: str):
        """
        Invalida o cache para uma instituição específica.
        Força a próxima chamada a buscar os dados frescos do banco.
        """
        if institution_id in self._cache:
            del self._cache[institution_id]
            
    def invalidate_all(self):
        self._cache.clear()

# Singleton global instance
config_manager = ConfigManager()
