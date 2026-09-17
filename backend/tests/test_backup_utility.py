import json
import tarfile

from app import backup


def test_create_backup_generates_manifest_and_storage_archive(tmp_path, monkeypatch):
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    (storage_root / "sample.txt").write_text("backup content", encoding="utf-8")
    monkeypatch.setattr(backup, "STORAGE_ROOT", storage_root)

    def fake_run_pg_dump(output_path):
        output_path.write_bytes(b"pg_dump placeholder")

    monkeypatch.setattr(backup, "_run_pg_dump", fake_run_pg_dump)

    archive_dir = backup.create_backup(tmp_path / "backups")

    assert archive_dir.is_dir()
    manifest = json.loads((archive_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["database_dump"] == "database.dump"
    assert manifest["storage_archive"] == "storage.tar.gz"
    assert (archive_dir / "database.dump").read_bytes() == b"pg_dump placeholder"

    with tarfile.open(archive_dir / "storage.tar.gz", "r:gz") as archive:
        assert "storage/sample.txt" in archive.getnames()


def test_restore_backup_replaces_storage_root_and_keeps_manifest_valid(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backup-root"
    backup_dir.mkdir()
    storage_root = tmp_path / "storage-root"
    storage_root.mkdir()
    existing_file = storage_root / "old.txt"
    existing_file.write_text("old content", encoding="utf-8")

    (backup_dir / "database.dump").write_bytes(b"pg_restore placeholder")
    archive_path = backup_dir / "storage.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        payload = tmp_path / "incoming" / "new.txt"
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_text("restored content", encoding="utf-8")
        archive.add(payload, arcname="storage/new.txt")

    manifest = {
        "created_at": "2026-09-17T00:00:00Z",
        "database_dump": "database.dump",
        "storage_archive": "storage.tar.gz",
        "storage_root": str(storage_root),
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(backup, "STORAGE_ROOT", storage_root)
    monkeypatch.setattr(backup, "_run_pg_restore", lambda dump_path: None)

    backup.restore_backup(backup_dir, confirm=True)

    assert (storage_root / "new.txt").read_text(encoding="utf-8") == "restored content"
    assert not existing_file.exists()
