from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.api.documents import _get_document_for_user
from app.services.notifications import notify_project_members
from app.db.base import get_db
from app.models import Attachment, Message, MessageHidden, Notification, Process, User, UserRole
from app.schemas.schemas import MessageCreate, MessageOut
from app.services.audit import log_action
from app.services.storage import upload_bytes
from app.websockets.manager import manager

router = APIRouter(tags=["messages"])


@router.get("/documents/{doc_id}/messages", response_model=list[MessageOut])
async def list_messages(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    await _get_document_for_user(db, doc_id, user)
    res = await db.execute(
        select(Message).where(Message.document_id == doc_id)
        .where(~Message.id.in_(
            select(MessageHidden.message_id).where(MessageHidden.user_id == user.id)
        ))
        .options(selectinload(Message.attachments))
        .order_by(Message.created_at.asc()).offset(skip).limit(limit)
    )
    return list(res.scalars().all())


@router.post("/documents/{doc_id}/messages", response_model=MessageOut, status_code=201)
async def post_message(
    doc_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await _get_document_for_user(db, doc_id, user)
    msg = Message(document_id=doc_id, user_id=user.id, body=payload.body)
    db.add(msg)
    await db.flush()
    await log_action(db, user.id, "post", "message", msg.id)
    await db.commit()
    res = await db.execute(
        select(Message).where(Message.id == msg.id).options(selectinload(Message.attachments))
    )
    msg = res.scalar_one()

    out = MessageOut.model_validate(msg).model_dump()
    await manager.broadcast_room(f"doc:{doc_id}", {"type": "message", "data": out})

    proc_res = await db.execute(select(Process).where(Process.id == doc.process_id))
    proc = proc_res.scalar_one()
    snippet = payload.body.strip().replace("\n", " ")[:140]
    title = f"💬 {user.full_name} · {doc.title}"
    await notify_project_members(
        db, proc.project_id, user.id,
        title=title,
        body=snippet,
        link=f"/documents/{doc_id}",
        payload={"type": "new_message", "document_id": doc_id}
    )
    await db.commit()
    return msg


@router.post("/documents/{doc_id}/messages/upload", response_model=MessageOut, status_code=201)
async def post_message_with_files(
    doc_id: int,
    body: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a chat message with file attachments in a single multipart request."""
    doc = await _get_document_for_user(db, doc_id, user)
    text = (body or "").strip()
    if not text and not files:
        from fastapi import HTTPException
        raise HTTPException(400, "Message must have text or at least one attachment")
    msg = Message(document_id=doc_id, user_id=user.id, body=text or "(file)")
    db.add(msg)
    await db.flush()
    for f in files or []:
        data = await f.read()
        url = await upload_bytes(f.filename or "file", data, f.content_type or "application/octet-stream")
        db.add(Attachment(
            message_id=msg.id, file_url=url,
            file_name=f.filename or "file",
            content_type=f.content_type or "application/octet-stream",
        ))
    await log_action(db, user.id, "post", "message", msg.id, f"{len(files or [])} attachment(s)")
    await db.commit()

    res = await db.execute(
        select(Message).where(Message.id == msg.id).options(selectinload(Message.attachments))
    )
    msg = res.scalar_one()
    out = MessageOut.model_validate(msg).model_dump(mode="json")
    await manager.broadcast_room(f"doc:{doc_id}", {"type": "message", "data": out})

    proc_res = await db.execute(select(Process).where(Process.id == doc.process_id))
    proc = proc_res.scalar_one()
    snippet = (text or f"📎 {len(files or [])} file(s)")[:140]
    title = f"💬 {user.full_name} · {doc.title}"
    await notify_project_members(
        db, proc.project_id, user.id,
        title=title,
        body=snippet,
        link=f"/documents/{doc_id}",
        payload={"type": "new_message", "document_id": doc_id}
    )
    await db.commit()
    return msg


@router.post("/messages/{message_id}/attachments")
async def attach_to_message(
    message_id: int,
    file_url: str,
    file_name: str,
    content_type: str = "application/octet-stream",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Message).where(Message.id == message_id))
    msg = res.scalar_one_or_none()
    if not msg:
        from fastapi import HTTPException
        raise HTTPException(404, "Message not found")
    await _get_document_for_user(db, msg.document_id, user)
    att = Attachment(message_id=message_id, file_url=file_url, file_name=file_name, content_type=content_type)
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return {"id": att.id, "file_url": att.file_url, "file_name": att.file_name, "content_type": att.content_type}


@router.delete("/messages/{message_id}", status_code=204)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Message).where(Message.id == message_id))
    msg = res.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")

    await _get_document_for_user(db, msg.document_id, user)

    if user.role == UserRole.consultant:
        doc_id = msg.document_id
        await db.delete(msg)
        await log_action(db, user.id, "delete_global", "message", message_id)
        await manager.broadcast_room(f"doc:{doc_id}", {"type": "message_deleted", "data": {"message_id": message_id}})
    else:
        # Hide for this user only
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        # Use insert or ignore to avoid duplicates
        await db.execute(
            sqlite_insert(MessageHidden).values(message_id=message_id, user_id=user.id).on_conflict_do_nothing()
        )
        await log_action(db, user.id, "delete_local", "message", message_id)

    await db.commit()


@router.delete("/documents/{doc_id}/messages", status_code=204)
async def clear_document_chat(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_document_for_user(db, doc_id, user)

    if user.role == UserRole.consultant:
        # Global delete
        from sqlalchemy import delete
        await db.execute(delete(Message).where(Message.document_id == doc_id))
        await log_action(db, user.id, "clear_chat_global", "document", doc_id)
        await manager.broadcast_room(f"doc:{doc_id}", {"type": "chat_cleared"})
    else:
        # Local hide for all current messages
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        # Get all current message IDs for this document
        msg_ids_res = await db.execute(select(Message.id).where(Message.document_id == doc_id))
        msg_ids = msg_ids_res.scalars().all()
        for mid in msg_ids:
            await db.execute(
                sqlite_insert(MessageHidden).values(message_id=mid, user_id=user.id).on_conflict_do_nothing()
            )
        await log_action(db, user.id, "clear_chat_local", "document", doc_id)

    await db.commit()
