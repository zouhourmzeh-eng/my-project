from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Notification, ProjectMember
from app.websockets.manager import manager

async def send_notification(
    db: AsyncSession,
    user_id: int,
    title: str,
    body: str = "",
    link: str = "",
    payload: dict[str, Any] | None = None
):
    """Save notification to DB and send via WebSocket."""
    notif = Notification(
        user_id=user_id,
        title=title,
        body=body,
        link=link
    )
    db.add(notif)
    
    ws_payload = {
        "type": "notification",
        "title": title,
        "body": body,
        "link": link
    }
    if payload:
        ws_payload.update(payload)
        
    await manager.notify_user(user_id, ws_payload)

async def notify_project_members(
    db: AsyncSession,
    project_id: int,
    exclude_user_id: int,
    title: str,
    body: str = "",
    link: str = "",
    payload: dict[str, Any] | None = None
):
    """Notify all members AND the owner of a project except the initiator."""
    from app.models import Project
    # Get project owner
    proj_res = await db.execute(select(Project.owner_id).where(Project.id == project_id))
    owner_id = proj_res.scalar_one_or_none()

    # Get members
    res = await db.execute(
        select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)
    )
    uids = {r[0] for r in res.all()}
    if owner_id:
        uids.add(owner_id)
    
    for uid in uids:
        if uid != exclude_user_id:
            await send_notification(db, uid, title, body, link, payload)
