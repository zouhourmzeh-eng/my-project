from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_consultant
from app.api.projects import _get_project_for_user
from app.db.base import get_db
from app.models import Process, User
from app.schemas.schemas import ProcessCreate, ProcessOut, ProcessUpdate
from app.services.audit import log_action
from app.services.notifications import notify_project_members

router = APIRouter(tags=["processes"])


@router.get("/projects/{project_id}/processes", response_model=list[ProcessOut])
async def list_processes(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_project_for_user(db, project_id, user)
    res = await db.execute(
        select(Process).where(Process.project_id == project_id).order_by(Process.created_at.desc())
    )
    return list(res.scalars().all())


@router.post("/projects/{project_id}/processes", response_model=ProcessOut, status_code=201)
async def create_process(
    project_id: int,
    payload: ProcessCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    await _get_project_for_user(db, project_id, user)
    proc = Process(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        version=payload.version,
    )
    db.add(proc)
    await db.flush()
    await log_action(db, user.id, "create", "process", proc.id, payload.name)
    await db.commit()
    await notify_project_members(
        db, project_id, user.id,
        title="⚙️ New process",
        body=f"A new process '{payload.name}' has been added to the project.",
        link=f"/processes/{proc.id}"
    )
    await db.commit()
    await db.refresh(proc)
    return proc


@router.get("/processes/{process_id}", response_model=ProcessOut)
async def get_process(
    process_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Process).where(Process.id == process_id))
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Process not found")
    await _get_project_for_user(db, proc.project_id, user)
    return proc


@router.patch("/processes/{process_id}", response_model=ProcessOut)
async def update_process(
    process_id: int,
    payload: ProcessUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    res = await db.execute(select(Process).where(Process.id == process_id))
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Process not found")
    await _get_project_for_user(db, proc.project_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(proc, k, v)
    await log_action(db, user.id, "update", "process", process_id)
    await db.commit()
    await notify_project_members(
        db, proc.project_id, user.id,
        title="📝 Process updated",
        body=f"The process '{proc.name}' has been updated.",
        link=f"/processes/{proc.id}"
    )
    await db.commit()
    await db.refresh(proc)
    return proc


@router.post("/processes/{process_id}/file", response_model=ProcessOut)
async def attach_process_file(
    process_id: int,
    file_url: str,
    file_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    res = await db.execute(select(Process).where(Process.id == process_id))
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Process not found")
    await _get_project_for_user(db, proc.project_id, user)
    proc.file_url = file_url
    proc.file_name = file_name
    await log_action(db, user.id, "upload", "process", process_id, file_name)
    await db.commit()
    await db.refresh(proc)
    return proc


@router.delete("/processes/{process_id}", status_code=204)
async def delete_process(
    process_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    res = await db.execute(select(Process).where(Process.id == process_id))
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Process not found")
    await _get_project_for_user(db, proc.project_id, user)
    await db.delete(proc)
    await log_action(db, user.id, "delete", "process", process_id)
    await notify_project_members(
        db, proc.project_id, user.id,
        title="🗑️ Process deleted",
        body=f"The process '{proc.name}' has been removed from the project."
    )
    await db.commit()
