"""Operational PostgreSQL and file-storage backup utilities."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess  # nosec B404 - database backup commands are explicit and controlled
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from app.config import settings
from app.storage import STORAGE_ROOT


def create_backup(destination: Path) -> Path:
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_dir = destination / f"backup-{timestamp}"
    archive_dir.mkdir()
    dump_path = archive_dir / "database.dump"
    storage_archive = archive_dir / "storage.tar.gz"

    _run_pg_dump(dump_path)
    with tarfile.open(storage_archive, "w:gz") as archive:
        archive.add(STORAGE_ROOT, arcname="storage")

    manifest = {
        "created_at": timestamp,
        "database_dump": dump_path.name,
        "storage_archive": storage_archive.name,
        "storage_root": str(STORAGE_ROOT.resolve()),
    }
    (archive_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return archive_dir


def restore_backup(backup_dir: Path, *, confirm: bool = False) -> None:
    if not confirm:
        raise ValueError("restore requires confirm=True because it replaces database and storage")
    backup_dir = backup_dir.resolve()
    manifest_path = backup_dir / "manifest.json"
    dump_path = backup_dir / "database.dump"
    storage_archive = backup_dir / "storage.tar.gz"
    if not manifest_path.is_file() or not dump_path.is_file() or not storage_archive.is_file():
        raise FileNotFoundError("backup manifest, database dump, and storage archive are required")

    _run_pg_restore(dump_path)
    staging = STORAGE_ROOT.with_name(f"{STORAGE_ROOT.name}.restore-staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with tarfile.open(storage_archive, "r:gz") as archive:
        archive.extractall(staging, members=_safe_tar_members(archive, staging))  # nosec B202 - members are explicitly validated before extraction
    extracted = staging / "storage"
    if not extracted.is_dir():
        raise ValueError("storage archive does not contain the expected storage directory")
    if STORAGE_ROOT.exists():
        shutil.rmtree(STORAGE_ROOT)
    extracted.replace(STORAGE_ROOT)
    staging.rmdir()


def _safe_tar_members(archive: tarfile.TarFile, destination: Path) -> list[tarfile.TarInfo]:
    destination_root = destination.resolve()
    safe_members: list[tarfile.TarInfo] = []

    for member in archive.getmembers():
        member_name = member.name.replace("\\", "/")
        if member_name.startswith("/") or ".." in member_name.split("/"):
            raise ValueError(f"unsafe archive member detected: {member_name!r}")

        candidate = (destination_root / member_name).resolve()
        if not str(candidate).startswith(str(destination_root)):
            raise ValueError(f"archive member escapes the restore directory: {member_name!r}")
        if member.issym() or member.islnk():
            raise ValueError(f"symbolic links are not allowed in restore archives: {member_name!r}")
        safe_members.append(member)

    return safe_members


def _database_dsn() -> str:
    url = settings.DATABASE_URL
    if "+psycopg" in url:
        return url.replace("+psycopg2", "").replace("+psycopg", "")
    return url


def _run_pg_dump(output: Path) -> None:
    _run_database_command(["pg_dump", "--format=custom", "--file", str(output)])


def _run_pg_restore(dump_path: Path) -> None:
    _run_command(["pg_restore", "--clean", "--if-exists", "--dbname", _database_dsn(), str(dump_path)])


def _run_database_command(command: list[str]) -> None:
    dsn = _database_dsn()
    command = [*command]
    if dsn not in command:
        command.append(dsn)
    _run_command(command)


def _run_command(command: list[str]) -> None:
    env = os.environ.copy()
    env["PGDATABASE_URL"] = settings.DATABASE_URL
    completed = subprocess.run(  # nosec B603 - command arguments are explicit and not derived from user input
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "database backup command failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or restore a LibreGED backup")
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("destination", type=Path)
    restore = subparsers.add_parser("restore")
    restore.add_argument("backup_dir", type=Path)
    restore.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if args.action == "create":
        print(create_backup(args.destination))
    else:
        restore_backup(args.backup_dir, confirm=args.confirm)


if __name__ == "__main__":
    main()
