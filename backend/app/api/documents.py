from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_consultant
from app.api.projects import _get_project_for_user
from app.db.base import get_db
from app.models import Document, DocumentStatus, DocumentVersion, Notification, Process, ProjectMember, User, UserRole
from app.schemas.schemas import (
    DocumentCreate, DocumentOut, DocumentStatusUpdate, DocumentUpdate, DocumentVersionOut,
)
from app.services.audit import log_action
from app.services.notifications import notify_project_members
from app.websockets.manager import manager

router = APIRouter(tags=["documents"])


async def _get_document_for_user(db: AsyncSession, doc_id: int, user: User) -> Document:
    res = await db.execute(select(Document).where(Document.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    proc_res = await db.execute(select(Process).where(Process.id == doc.process_id))
    proc = proc_res.scalar_one()
    await _get_project_for_user(db, proc.project_id, user)
    return doc





@router.get("/processes/{process_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    process_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    res = await db.execute(select(Process).where(Process.id == process_id))
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(404, "Process not found")
    await _get_project_for_user(db, proc.project_id, user)
    res = await db.execute(
        select(Document).where(Document.process_id == process_id)
        .order_by(Document.updated_at.desc()).offset(skip).limit(limit)
    )
    return list(res.scalars().all())


@router.post("/processes/{process_id}/documents", response_model=DocumentOut, status_code=201)
async def create_document(
    process_id: int,
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    res = await db.execute(select(Process).where(Process.id == process_id))
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(404, "Process not found")
    await _get_project_for_user(db, proc.project_id, user)
    doc = Document(
        process_id=process_id,
        title=payload.title,
        description=payload.description,
        created_by=user.id,
    )
    db.add(doc)
    await db.flush()
    await log_action(db, user.id, "create", "document", doc.id, payload.title)
    await db.commit()
    await db.refresh(doc)
    # notify project members
    await notify_project_members(
        db, proc.project_id, user.id,
        title="📄 New document",
        body=payload.title,
        link=f"/documents/{doc.id}",
        payload={"type": "document_created", "document_id": doc.id}
    )
    await db.commit()
    return doc


@router.get("/documents/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _get_document_for_user(db, doc_id, user)


@router.get("/documents/{doc_id}/versions", response_model=list[DocumentVersionOut])
async def list_versions(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_document_for_user(db, doc_id, user)
    res = await db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.created_at.desc())
    )
    return list(res.scalars().all())


@router.post("/documents/{doc_id}/versions", response_model=DocumentVersionOut, status_code=201)
async def add_version(
    doc_id: int,
    version: str,
    file_url: str,
    file_name: str,
    note: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    doc = await _get_document_for_user(db, doc_id, user)
    
    # Check if a version already exists (restricting to one file as requested)
    res = await db.execute(select(DocumentVersion).where(DocumentVersion.document_id == doc_id))
    if res.scalars().first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A file is already uploaded for this document. Please delete it before uploading a new one.")

    v = DocumentVersion(
        document_id=doc_id, version=version, file_url=file_url,
        file_name=file_name, note=note, uploaded_by=user.id,
        status=DocumentStatus.draft,
    )
    db.add(v)
    doc.current_version = version
    doc.status = DocumentStatus.draft
    await log_action(db, user.id, "upload", "document_version", doc_id, version)
    await db.commit()
    await db.refresh(v)
    proc_res = await db.execute(select(Process).where(Process.id == doc.process_id))
    proc = proc_res.scalar_one()
    await notify_project_members(
        db, proc.project_id, user.id,
        title="📄 New document version",
        body=f"{doc.title} v{version}",
        link=f"/documents/{doc.id}",
        payload={"type": "version_added", "document_id": doc.id, "version": version}
    )
    await db.commit()
    return v


@router.patch("/documents/{doc_id}", response_model=DocumentOut)
async def update_document(
    doc_id: int,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    doc = await _get_document_for_user(db, doc_id, user)
    if payload.title is not None:
        doc.title = payload.title
    if payload.description is not None:
        doc.description = payload.description
    
    await log_action(db, user.id, "update", "document", doc_id)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.patch("/documents/{doc_id}/status", response_model=DocumentOut)
async def update_document_status(
    doc_id: int,
    payload: DocumentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    doc = await _get_document_for_user(db, doc_id, user)
    doc.status = payload.status
    if payload.status in [DocumentStatus.validated, DocumentStatus.approved]:
        doc.validated_at = datetime.now(timezone.utc)
    else:
        doc.validated_at = None

    # also stamp current version status
    res = await db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id, DocumentVersion.version == doc.current_version)
    )
    v = res.scalar_one_or_none()
    if v:
        v.status = payload.status
    await log_action(db, user.id, f"status_{payload.status.value}", "document", doc_id)
    await db.commit()
    await db.refresh(doc)
    proc_res = await db.execute(select(Process).where(Process.id == doc.process_id))
    proc = proc_res.scalar_one()
    await notify_project_members(
        db, proc.project_id, user.id,
        title=f"📄 Document {payload.status.value}",
        body=doc.title,
        link=f"/documents/{doc.id}",
        payload={"type": "status_changed", "document_id": doc.id, "status": payload.status.value}
    )
    await db.commit()
    return doc


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    doc = await _get_document_for_user(db, doc_id, user)
    await db.delete(doc)
    await log_action(db, user.id, "delete", "document", doc_id)
    proc_res = await db.execute(select(Process).where(Process.id == doc.process_id))
    proc = proc_res.scalar_one()
    await notify_project_members(
        db, proc.project_id, user.id,
        title="🗑️ Document deleted",
        body=f"The document '{doc.title}' has been deleted."
    )
    await db.commit()


@router.delete("/documents/versions/{version_id}", status_code=204)
async def delete_document_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    res = await db.execute(select(DocumentVersion).where(DocumentVersion.id == version_id))
    v = res.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")
    
    doc = await _get_document_for_user(db, v.document_id, user)
    await db.delete(v)
    
    # Update doc's current version to the next latest one
    res = await db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.created_at.desc())
    )
    latest = res.scalars().first()
    doc.current_version = latest.version if latest else "0.0"
    
    await log_action(db, user.id, "delete_version", "document", doc.id, v.version)
    await db.commit()
