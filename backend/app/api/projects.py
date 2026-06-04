from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from datetime import datetime, timezone

from app.api.deps import get_current_user, require_consultant
from app.db.base import get_db
from app.models import Notification, Project, ProjectMember, User, UserRole
from app.schemas.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.audit import log_action
from app.services.notifications import notify_project_members
from app.websockets.manager import manager

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_out(p: Project) -> ProjectOut:
    out = ProjectOut.model_validate(p)
    out.member_ids = [m.user_id for m in p.members]
    return out


async def _get_project_for_user(db: AsyncSession, project_id: int, user: User) -> Project:
    res = await db.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.members))
    )
    proj = res.scalar_one_or_none()
    if not proj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    
    # Check ownership or membership first
    if proj.owner_id != user.id and not any(m.user_id == user.id for m in proj.members):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this project")
        
    # If project is validated/archived, only consultants can access it
    if proj.is_validated and user.role != UserRole.consultant:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This project is archived and read-only for the consultant only.")
        
    return proj


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    archived: bool = Query(False),
):
    stmt = (
        select(Project)
        .options(selectinload(Project.members))
        .join(ProjectMember, ProjectMember.project_id == Project.id, isouter=True)
        .where(
            (Project.owner_id == user.id) | (ProjectMember.user_id == user.id)
        )
        .order_by(Project.created_at.desc())
    )
    if user.role != UserRole.consultant:
        # Hide validated projects from non-consultants
        stmt = stmt.where(Project.is_validated == False)  # noqa: E712
    else:
        # For consultants, filter by archived status
        stmt = stmt.where(Project.is_validated == archived)
        
    stmt = stmt.distinct().offset(skip).limit(limit)
    res = await db.execute(stmt)
    return [_to_out(p) for p in res.scalars().unique().all()]


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    proj = Project(
        company_name=payload.company_name,
        company_role=payload.company_role,
        activity_sector=payload.activity_sector,
        product=payload.product,
        market=payload.market,
        standards=payload.standards,
        owner_id=user.id,
    )
    db.add(proj)
    await db.flush()
    for uid in payload.member_ids:
        db.add(ProjectMember(project_id=proj.id, user_id=uid))
    await log_action(db, user.id, "create", "project", proj.id, payload.company_name)
    await db.commit()
    # Notify members added to the project
    await notify_project_members(
        db, proj.id, user.id,
        title="📂 New project",
        body=f"You have been added to the project: {payload.company_name}",
        link=f"/projects/{proj.id}"
    )
    await db.commit()
    res = await db.execute(
        select(Project).where(Project.id == proj.id).options(selectinload(Project.members))
    )
    return _to_out(res.scalar_one())


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    proj = await _get_project_for_user(db, project_id, user)
    return _to_out(proj)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    proj = await _get_project_for_user(db, project_id, user)
    data = payload.model_dump(exclude_unset=True)
    member_ids = data.pop("member_ids", None)
    for k, v in data.items():
        setattr(proj, k, v)
    if member_ids is not None:
        await db.execute(delete(ProjectMember).where(ProjectMember.project_id == proj.id))
        for uid in member_ids:
            db.add(ProjectMember(project_id=proj.id, user_id=uid))
    await log_action(db, user.id, "update", "project", proj.id)
    await db.commit()
    # Notify members of the update
    await notify_project_members(
        db, proj.id, user.id,
        title="📝 Project updated",
        body=f"The project {proj.company_name} has been updated.",
        link=f"/projects/{proj.id}"
    )
    await db.commit()
    res = await db.execute(
        select(Project).where(Project.id == proj.id).options(selectinload(Project.members))
    )
    return _to_out(res.scalar_one())


@router.post("/{project_id}/validate", response_model=ProjectOut)
async def validate_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    proj = await _get_project_for_user(db, project_id, user)
    proj.is_validated = True
    proj.validated_at = datetime.now(timezone.utc)
    
    await log_action(db, user.id, "validate", "project", proj.id, proj.company_name)
    
    # notify all members that project is locked
    await notify_project_members(
        db, proj.id, user.id,
        title="🔒 Project validated",
        body=f"{proj.company_name} is now validated and read-only.",
        link=f"/projects/{proj.id}",
        payload={"type": "project_validated", "project_id": proj.id}
    )

    # Find processes and documents to delete their notifications too
    from app.models import Process, Document
    from sqlalchemy import or_

    processes_res = await db.execute(select(Process.id).where(Process.project_id == project_id))
    process_ids = processes_res.scalars().all()
    
    doc_ids = []
    if process_ids:
        docs_res = await db.execute(select(Document.id).where(Document.process_id.in_(process_ids)))
        doc_ids = docs_res.scalars().all()

    # Build conditions
    conditions = [
        Notification.link == f"/projects/{project_id}",
        Notification.link.like(f"/projects/{project_id}/%")
    ]
    for pid in process_ids:
        conditions.append(Notification.link == f"/processes/{pid}")
        conditions.append(Notification.link.like(f"/processes/{pid}/%"))
    for did in doc_ids:
        conditions.append(Notification.link == f"/documents/{did}")
        conditions.append(Notification.link.like(f"/documents/{did}/%"))

    # Delete all notifications for this project for all users except the consultant (owner)
    # This includes the one we just sent above
    await db.execute(
        delete(Notification)
        .where(or_(*conditions))
        .where(Notification.user_id != proj.owner_id)
    )
    
    await db.commit()
    res = await db.execute(
        select(Project).where(Project.id == proj.id).options(selectinload(Project.members))
    )
    return _to_out(res.scalar_one())


@router.post("/{project_id}/unvalidate", response_model=ProjectOut)
async def unvalidate_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    proj = await _get_project_for_user(db, project_id, user)
    proj.is_validated = False
    proj.validated_at = None
    await log_action(db, user.id, "unvalidate", "project", proj.id)
    await db.commit()
    res = await db.execute(
        select(Project).where(Project.id == proj.id).options(selectinload(Project.members))
    )
    return _to_out(res.scalar_one())


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    proj = await _get_project_for_user(db, project_id, user)
    await db.delete(proj)
    await log_action(db, user.id, "delete", "project", project_id)
    await db.commit()


@router.get("/{project_id}/members")
async def list_project_members(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return full user info for all members of a project, including the owner."""
    proj = await _get_project_for_user(db, project_id, user)
    res = await db.execute(
        select(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project_id)
        .order_by(User.full_name)
    )
    members = res.scalars().all()
    result = [
        {"id": m.id, "full_name": m.full_name, "email": m.email, "role": m.role}
        for m in members
    ]
    # Include the project owner if not already in the members list
    owner_ids = {m.id for m in members}
    if proj.owner_id not in owner_ids:
        owner_res = await db.execute(select(User).where(User.id == proj.owner_id))
        owner = owner_res.scalar_one_or_none()
        if owner:
            result.append({"id": owner.id, "full_name": owner.full_name, "email": owner.email, "role": owner.role})
    return result


@router.post("/{project_id}/members", status_code=204)
async def add_project_member(
    project_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Add a user to a project by their email address."""
    await _get_project_for_user(db, project_id, user)

    email = payload.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "Email requis")

    # Find user by email
    res = await db.execute(select(User).where(User.email == email))
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(404, f"Aucun utilisateur trouvé avec l'email : {email}")

    # Check not already a member
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Cet utilisateur est déjà membre du projet")

    db.add(ProjectMember(project_id=project_id, user_id=member.id))
    await log_action(db, user.id, "assign_member", "project", project_id, email)
    await db.commit()

    # Notify the added member
    from app.services.notifications import send_notification
    proj_res = await db.execute(select(Project).where(Project.id == project_id))
    proj = proj_res.scalar_one()
    await send_notification(
        db, member.id,
        title="📂 Nouveau projet assigné",
        body=f"Vous avez été ajouté au projet : {proj.company_name}",
        link=f"/projects/{project_id}"
    )
    await db.commit()


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_project_member(
    project_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Remove a user from a project."""
    await _get_project_for_user(db, project_id, user)
    m = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
    )
    member = m.scalar_one_or_none()
    if member:
        await db.delete(member)
        await log_action(db, user.id, "remove_member", "project", project_id, str(user_id))
        await db.commit()

