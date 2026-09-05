from pathlib import Path
import os
import uuid
from sqlalchemy.orm import Session
from app.models_storage import StoragePartition

STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

def save_file(file_name: str, content: bytes, db: Session = None, partition_name: str = None) -> str:
    safe_name = Path(file_name).name
    if not safe_name or safe_name != file_name:
        raise ValueError("file_name must not contain path components")

    target_dir = STORAGE_ROOT
    
    if db:
        # Find active partition
        query = db.query(StoragePartition).filter(StoragePartition.is_active == True)
        if partition_name:
            query = query.filter(StoragePartition.name == partition_name)
        
        partition = query.first()
        
        if partition:
            # Check limits
            content_size = len(content)
            size_gb = (partition.current_size_bytes + content_size) / (1024**3)
            
            if (partition.current_file_count >= partition.max_files) or (size_gb >= partition.max_size_gb):
                # Rollover needed
                partition.is_active = False
                
                # Extract number if exists, else append _02
                parts = partition.base_path.rsplit("_", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    next_num = int(parts[1]) + 1
                    new_base = f"{parts[0]}_{next_num:02d}"
                else:
                    new_base = f"{partition.base_path}_02"
                
                new_partition = StoragePartition(
                    area_id=partition.area_id,
                    name=partition.name,
                    max_files=partition.max_files,
                    max_size_gb=partition.max_size_gb,
                    base_path=new_base,
                    network_domain=partition.network_domain,
                    network_user=partition.network_user,
                    network_password=partition.network_password,
                    current_file_count=1,
                    current_size_bytes=content_size,
                    is_active=True
                )
                db.add(new_partition)
                db.commit()
                db.refresh(new_partition)
                
                target_dir = STORAGE_ROOT / new_partition.base_path
                target_dir.mkdir(parents=True, exist_ok=True)
            else:
                partition.current_file_count += 1
                partition.current_size_bytes += content_size
                db.commit()
                
                target_dir = STORAGE_ROOT / partition.base_path
                target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / safe_name
    target.write_bytes(content)
    return str(target)


def load_file(stored_path: str) -> bytes:
    return Path(stored_path).read_bytes()


def delete_file(stored_path: str) -> None:
    target = Path(stored_path).resolve()
    target.unlink(missing_ok=True)
