from pathlib import Path
from typing import Any
import os
import uuid
from sqlalchemy.orm import Session
from app.models_storage import StorageRule

STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

def _rule_directory(base_path: str) -> Path:
    configured_path = Path(base_path)
    if configured_path.is_absolute():
        return configured_path
    return STORAGE_ROOT / configured_path


def save_file(
    file_name: str,
    content: bytes,
    db: Session = None,
    rule_name: str = None,
    partition_name: str = None,
) -> str:
    safe_name = Path(file_name).name
    if not safe_name or safe_name != file_name:
        raise ValueError("file_name must not contain path components")

    target_dir = STORAGE_ROOT
    
    if db:
        # Find active rule
        query = db.query(StorageRule).filter(StorageRule.is_active == True)
        if rule_name:
            query = query.filter((StorageRule.id == rule_name) | (StorageRule.name == rule_name))
        
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
                
                target_dir = _rule_directory(new_rule.base_path)
                target_dir.mkdir(parents=True, exist_ok=True)
            else:
                rule.current_file_count += 1
                rule.current_size_bytes += content_size
                db.commit()
                
                target_dir = _rule_directory(rule.base_path)
                target_dir.mkdir(parents=True, exist_ok=True)

            if partition_name:
                safe_partition = Path(partition_name).name
                if safe_partition != partition_name or safe_partition in {"", ".", ".."}:
                    raise ValueError("partition_name must be a single safe directory name")
                target_dir = target_dir / safe_partition
                target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / safe_name
    target.write_bytes(content)
    return str(target)


def load_file(stored_path: str) -> bytes:
    return Path(stored_path).read_bytes()


def delete_file(stored_path: str) -> None:
    target = Path(stored_path).resolve()
    target.unlink(missing_ok=True)


def cleanup_pending_deletions(root: Path = STORAGE_ROOT, db: Any = None) -> dict[str, int]:
    """Remove files left after a committed document deletion.

    The deletion endpoint renames the payload before committing the database
    transaction. A process interruption after commit leaves a uniquely named
    pending file, which is safe to remove on the next cleanup pass.
    """
    removed = 0
    failed = 0
    for pending in root.resolve().rglob(".exclusao-*.pending"):
        if not pending.is_file():
            continue
        try:
            pending.unlink()
            removed += 1
        except OSError:
            failed += 1
    if db is not None and removed:
        from app.main import add_audit
        add_audit(db, "storage", str(root.resolve()), "pending_deletions_cleaned",
                  f"{removed} arquivo(s) pendente(s) removido(s); {failed} falha(s).")
        db.commit()
    return {"removed": removed, "failed": failed}


def reconcile_document_storage(db: Any, root: Path = STORAGE_ROOT) -> dict[str, Any]:
    """Report mismatches between GED records and the database-backed index."""
    from app.models_ged import GEDDocument

    root = root.resolve()
    documents = db.query(GEDDocument).all()
    referenced_paths = set()
    missing_documents = []
    for document in documents:
        path = Path(document.file_path).resolve()
        if path.is_relative_to(root):
            referenced_paths.add(path)
        if not path.is_file():
            missing_documents.append({
                "document_id": document.id,
                "file_path": document.file_path,
            })

    pending = [
        str(path) for path in root.rglob(".exclusao-*.pending")
        if path.is_file()
    ]
    orphan_files = [
        str(path) for path in root.rglob("*")
        if path.is_file()
        and not path.name.startswith(".exclusao-")
        and path.resolve() not in referenced_paths
    ]
    return {
        "index_mode": "postgresql_document_fields",
        "index_consistent": True,
        "documents_checked": len(documents),
        "missing_documents": missing_documents,
        "orphan_files": orphan_files,
        "pending_deletions": pending,
        "consistent": not missing_documents and not orphan_files and not pending,
    }
