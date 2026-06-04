from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models import Document, DocumentStatus, Notification, Process, Project, ProjectMember, User, UserRole
from app.schemas.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def stats(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    accessible = select(Project.id).join(ProjectMember, ProjectMember.project_id == Project.id, isouter=True).where(
        (Project.owner_id == user.id) | (ProjectMember.user_id == user.id)
    ).distinct().subquery()
    
    proj_q = select(func.count()).select_from(accessible)
    proc_q = select(func.count(Process.id)).where(Process.project_id.in_(select(accessible.c.id)))
    doc_q = select(func.count(Document.id)).join(Process, Process.id == Document.process_id).where(
        Process.project_id.in_(select(accessible.c.id))
    )
    validate_q = doc_q.where(Document.status == DocumentStatus.draft)

    notif_q = select(func.count(Notification.id)).where(
        Notification.user_id == user.id, Notification.read.is_(False)
    )

    return DashboardStats(
        total_projects=(await db.execute(proj_q)).scalar_one() or 0,
        total_processes=(await db.execute(proc_q)).scalar_one() or 0,
        total_documents=(await db.execute(doc_q)).scalar_one() or 0,
        documents_to_validate=(await db.execute(validate_q)).scalar_one() or 0,
        unread_notifications=(await db.execute(notif_q)).scalar_one() or 0,
    )
