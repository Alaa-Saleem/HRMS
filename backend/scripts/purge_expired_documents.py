#!/usr/bin/env python3
"""Delete document rows past retention_until and remove files from UPLOAD_DIR.

Run from `backend/`:

  PYTHONPATH=. python scripts/purge_expired_documents.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import EmployeeDocument  # noqa: E402


def main() -> None:
    now = datetime.now(timezone.utc)
    upload_root = os.path.abspath(settings.upload_dir)
    db = SessionLocal()
    removed = 0
    try:
        rows = (
            db.query(EmployeeDocument)
            .filter(EmployeeDocument.retention_until.is_not(None))
            .filter(EmployeeDocument.retention_until < now)
            .all()
        )
        for r in rows:
            rel = (r.storage_key or "").replace("\\", "/").lstrip("/")
            if rel and ".." not in rel.split("/"):
                path = os.path.normpath(os.path.join(upload_root, *rel.split("/")))
                if path.startswith(upload_root + os.sep) and os.path.isfile(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            db.delete(r)
            removed += 1
        db.commit()
        print(f"purge_expired_documents: removed {removed} record(s)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
