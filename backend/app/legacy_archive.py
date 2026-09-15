"""Safe, diagnostic reconciliation for installations with legacy tables."""

from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models_ged import GEDDocument
from app.storage import STORAGE_ROOT


def reconcile_legacy_archive(db: Session, root: Path = STORAGE_ROOT) -> dict[str, Any]:
    inspector = inspect(db.bind)
    tables = set(inspector.get_table_names())
    legacy_tables = sorted(tables.intersection({"documents", "document_versions"}))
    report: dict[str, Any] = {
        "legacy_tables_detected": legacy_tables,
        "legacy_records": {},
        "unmigrated_records": [],
        "ged_documents_checked": 0,
        "missing_files": [],
        "orphan_files": [],
        "safe_to_migrate": not legacy_tables,
        "consistent": True,
    }

    for table in legacy_tables:
        count = db.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
        report["legacy_records"][table] = count
        if count:
            report["safe_to_migrate"] = False
            report["consistent"] = False
            report["unmigrated_records"].append({
                "table": table,
                "count": count,
                "action": "review_mapping_before_import",
            })

    referenced = set()
    for document in db.query(GEDDocument).all():
        report["ged_documents_checked"] += 1
        path = Path(document.file_path).resolve()
        if path.is_file():
            referenced.add(path)
        else:
            report["missing_files"].append({
                "document_id": document.id,
                "file_path": document.file_path,
            })

    root = root.resolve()
    report["orphan_files"] = [
        str(path) for path in root.rglob("*")
        if path.is_file()
        and not path.name.startswith(".exclusao-")
        and path.resolve() not in referenced
    ]
    report["consistent"] = report["consistent"] and not report["missing_files"] and not report["orphan_files"]
    return report
