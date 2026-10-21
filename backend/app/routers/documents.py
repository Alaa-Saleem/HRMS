"""Employee documents: local storage, list/download/delete, stub scan, retention metadata."""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.audit import log_audit
from app.config import settings
from app.deps import CurrentUser, DbSession
from app.models import Employee, EmployeeDocument
from app.rbac import can_manage_documents

router = APIRouter(prefix="/employees", tags=["documents"])

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def _ensure_upload_root() -> str:
    root = os.path.abspath(settings.upload_dir)
    os.makedirs(root, exist_ok=True)
    return root


def _abs_storage_path(storage_key: str) -> str:
    root = os.path.normpath(_ensure_upload_root())
    rel = (storage_key or "").replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid storage key")
    dest = os.path.normpath(os.path.join(root, *rel.split("/")))
    if not dest.startswith(root + os.sep):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid storage path")
    return dest


@router.get("/{employee_id}/documents", response_model=dict)
def list_documents(db: DbSession, user: CurrentUser, employee_id: int):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    if not can_manage_documents(user, emp, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    rows = (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.employee_id == employee_id)
        .order_by(EmployeeDocument.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "label": r.label,
                "mime_type": r.mime_type,
                "size_bytes": r.size_bytes,
                "scan_status": r.scan_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "retention_until": r.retention_until.isoformat() if r.retention_until else None,
            }
            for r in rows
        ]
    }


@router.get("/{employee_id}/documents/{doc_id}/file")
def download_document(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    employee_id: int,
    doc_id: int,
):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    if not can_manage_documents(user, emp, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    row = db.get(EmployeeDocument, doc_id)
    if not row or row.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    path = _abs_storage_path(row.storage_key)
    if not os.path.isfile(path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing on disk")

    log_audit(
        db,
        actor_id=user.id,
        action="document.download",
        entity_type="employee_document",
        entity_id=row.id,
        payload={"employee_id": employee_id, "label": row.label},
        request=request,
    )
    db.commit()

    safe_label = _SAFE_NAME.sub("_", row.label)[:80] or "document"
    fname = f"{safe_label}_{row.id}"
    return FileResponse(
        path,
        filename=fname,
        media_type=row.mime_type or "application/octet-stream",
    )


@router.delete("/{employee_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    employee_id: int,
    doc_id: int,
):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    if not can_manage_documents(user, emp, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    row = db.get(EmployeeDocument, doc_id)
    if not row or row.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    path = _abs_storage_path(row.storage_key)
    log_audit(
        db,
        actor_id=user.id,
        action="document.delete",
        entity_type="employee_document",
        entity_id=row.id,
        payload={"employee_id": employee_id},
        request=request,
    )
    db.delete(row)
    db.commit()
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


@router.post("/{employee_id}/documents", response_model=dict)
async def upload_document(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    employee_id: int,
    label: str = Form("document"),
    file: UploadFile = File(...),
):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    if not can_manage_documents(user, emp, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")

    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File too large")

    mime = file.content_type or "application/octet-stream"
    ext = os.path.splitext(file.filename or "")[1][:12] or ".bin"
    safe_label = _SAFE_NAME.sub("_", label)[:80] or "doc"
    key = f"{employee_id}/{uuid.uuid4().hex}{ext}"
    root = _ensure_upload_root()
    dest_path = os.path.join(root, key.replace("/", os.sep))
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(raw)

    scan_status = "clean"
    if raw.startswith(b"MZ") or raw.startswith(b"\x7fELF"):
        scan_status = "blocked_executable_stub"

    years = max(1, int(settings.document_retention_years))
    retention = datetime.now(timezone.utc) + timedelta(days=365 * years)
    row = EmployeeDocument(
        employee_id=employee_id,
        label=safe_label,
        storage_key=key,
        mime_type=mime[:120],
        size_bytes=len(raw),
        scan_status=scan_status,
        retention_until=retention,
    )
    db.add(row)
    db.flush()
    log_audit(
        db,
        actor_id=user.id,
        action="document.upload",
        entity_type="employee_document",
        entity_id=row.id,
        payload={
            "employee_id": employee_id,
            "label": safe_label,
            "size_bytes": len(raw),
            "scan_status": scan_status,
        },
        request=request,
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "label": row.label,
        "mime_type": row.mime_type,
        "size_bytes": row.size_bytes,
        "scan_status": row.scan_status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "retention_until": row.retention_until.isoformat() if row.retention_until else None,
    }
