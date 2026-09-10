from pathlib import Path
import os
import uuid
from sqlalchemy.orm import Session
from app.models_storage import StorageRule

STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

def save_file(file_name: str, content: bytes, db: Session = None, rule_name: str = None) -> str:
    safe_name = Path(file_name).name
    if not safe_name or safe_name != file_name:
        raise ValueError("file_name must not contain path components")

    target_dir = STORAGE_ROOT
    
    if db:
        # Find active rule
        query = db.query(StorageRule).filter(StorageRule.is_active == True)
        if rule_name:
            query = query.filter(StorageRule.name == rule_name)
        
        rule = query.first()
        
        if rule:
            # Check limits
            content_size = len(content)
            size_gb = (rule.current_size_bytes + content_size) / (1024**3)
            
            if (rule.current_file_count >= rule.max_files_per_folder) or (size_gb >= rule.max_gb_per_folder):
                # Rollover needed
                rule.is_active = False
                
                # Extract number if exists, else append _02
                parts = rule.base_path.rsplit("_", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    next_num = int(parts[1]) + 1
                    new_base = f"{parts[0]}_{next_num:02d}"
                else:
                    new_base = f"{rule.base_path}_02"
                
                new_rule = StorageRule(
                    name=rule.name,
                    document_type_id=rule.document_type_id,
                    storage_type=rule.storage_type,
                    base_path=new_base,
                    max_files_per_folder=rule.max_files_per_folder,
                    max_gb_per_folder=rule.max_gb_per_folder,
                    enable_duplication=rule.enable_duplication,
                    secondary_storage_type=rule.secondary_storage_type,
                    secondary_base_path=rule.secondary_base_path,
                    network_domain=rule.network_domain,
                    network_user=rule.network_user,
                    network_password=rule.network_password,
                    current_file_count=1,
                    current_size_bytes=content_size,
                    is_active=True
                )
                db.add(new_rule)
                db.commit()
                db.refresh(new_rule)
                
                target_dir = STORAGE_ROOT / new_rule.base_path
                target_dir.mkdir(parents=True, exist_ok=True)
            else:
                rule.current_file_count += 1
                rule.current_size_bytes += content_size
                db.commit()
                
                target_dir = STORAGE_ROOT / rule.base_path
                target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / safe_name
    target.write_bytes(content)
    return str(target)


def load_file(stored_path: str) -> bytes:
    return Path(stored_path).read_bytes()


def delete_file(stored_path: str) -> None:
    target = Path(stored_path).resolve()
    target.unlink(missing_ok=True)
