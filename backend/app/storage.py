from pathlib import Path

STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def save_file(file_name: str, content: bytes) -> str:
    target = STORAGE_ROOT / file_name
    target.write_bytes(content)
    return str(target)


def load_file(file_name: str) -> bytes:
    return (STORAGE_ROOT / file_name).read_bytes()
