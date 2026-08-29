from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def save_file(file_name: str, content: bytes) -> str:
    safe_name = Path(file_name).name
    if not safe_name or safe_name != file_name:
        raise ValueError("file_name must not contain path components")

    target = STORAGE_ROOT / safe_name
    target.write_bytes(content)
    return str(target)


def load_file(file_name: str) -> bytes:
    return (STORAGE_ROOT / file_name).read_bytes()


def delete_file(stored_path: str) -> None:
    target = Path(stored_path).resolve()
    if target.parent != STORAGE_ROOT.resolve():
        raise ValueError("stored_path is outside the storage root")
    target.unlink(missing_ok=True)
