from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.base import AsyncSessionLocal
from app.models import Document, Process, Project, ProjectMember, User, UserRole
from app.websockets.manager import manager

router = APIRouter(tags=["ws"])


async def _user_from_token(token: str) -> User | None:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = int(payload["sub"])
    except Exception:
        return None
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.id == user_id))
        return res.scalar_one_or_none()


async def _can_access_doc(user: User, doc_id: int) -> bool:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Document).where(Document.id == doc_id))
        doc = res.scalar_one_or_none()
        if not doc:
            return False
        proc = (await db.execute(select(Process).where(Process.id == doc.process_id))).scalar_one()
        proj = (await db.execute(select(Project).where(Project.id == proc.project_id))).scalar_one()
        if user.role == UserRole.consultant or proj.owner_id == user.id:
            return True
        m = (await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == proj.id, ProjectMember.user_id == user.id
            )
        )).scalar_one_or_none()
        return m is not None


@router.websocket("/ws/documents/{doc_id}")
async def chat_socket(websocket: WebSocket, doc_id: int, token: str = Query(...)):
    user = await _user_from_token(token)
    if not user or not await _can_access_doc(user, doc_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    room = f"doc:{doc_id}"
    await manager.join_room(room, websocket)
    try:
        while True:
            await websocket.receive_text()  # client may send pings
    except WebSocketDisconnect:
        manager.leave_room(room, websocket)


@router.websocket("/ws/notifications")
async def notification_socket(websocket: WebSocket, token: str = Query(...)):
    user = await _user_from_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.join_user(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.leave_user(user.id, websocket)
