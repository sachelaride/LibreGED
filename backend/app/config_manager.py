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
                "antimalware_enabled": settings.antimalware_enabled,
                "quarantine_enabled": settings.quarantine_enabled,
                "quarantine_policy": settings.quarantine_policy
            }
        else:
            # Fallback default se não existir no banco
            config_dict = {
                "max_upload_size_mb": 10,
                "allowed_mime_types": "application/pdf,image/png,image/jpeg",
                "antimalware_enabled": False,
                "quarantine_enabled": False,
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
