from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.models import User, RegulatorySource, RegulatoryUpdate, RegulatoryImpact, ProjectRegulation, Project, ProjectMember
from app.api.deps import require_consultant, get_current_user
from app.api.projects import _get_project_for_user
from app.schemas.regulatory import (
    RegulatorySourceCreate, RegulatorySourceOut,
    RegulatoryUpdateOut, RegulatoryImpactOut
)

router = APIRouter()


def _build_impact_dict(imp: RegulatoryImpact) -> dict:
    """Serialize a RegulatoryImpact object to a response dict."""
    return {
        "id": imp.id,
        "update_id": imp.update_id,
        "project_id": imp.project_id,
        "impact_summary": imp.impact_summary,
        "impact_justification": imp.impact_justification,
        "impacted_areas": imp.impacted_areas,
        "standards_updated": imp.standards_updated,
        "procedures_impacted": imp.procedures_impacted,
        "suggested_actions": imp.suggested_actions,
        "capa_recommendations": imp.capa_recommendations,
        "status": imp.status,
        "created_at": imp.created_at,
        "update": imp.update,
        "project": {"company_name": imp.project.company_name} if imp.project else None
    }


def _accessible_projects_subquery(user: User):
    """Returns a subquery of project IDs accessible to the given user."""
    return (
        select(Project.id)
        .join(ProjectMember, ProjectMember.project_id == Project.id, isouter=True)
        .where((Project.owner_id == user.id) | (ProjectMember.user_id == user.id))
        .distinct()
        .subquery()
    )


# --- Sources ---

@router.post("/sources", response_model=RegulatorySourceOut)
async def create_regulatory_source(
    source_in: RegulatorySourceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    source = RegulatorySource(**source_in.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source

@router.get("/sources", response_model=List[RegulatorySourceOut])
async def get_regulatory_sources(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    result = await db.execute(select(RegulatorySource).order_by(RegulatorySource.id.desc()))
    return result.scalars().all()


# --- Updates (History) ---
# Regulatory updates (fetched from public sources) are global — no per-user filter needed here.
# The user-specific filtering happens at the Impact level (impacts are tied to projects).

@router.get("/updates", response_model=List[RegulatoryUpdateOut])
async def get_regulatory_updates(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Get the history of regulatory updates."""
    result = await db.execute(
        select(RegulatoryUpdate)
        .order_by(RegulatoryUpdate.publication_date.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


# --- Impacts ---

@router.get("/projects/{project_id}/impacts", response_model=List[RegulatoryImpactOut])
async def get_project_impacts(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Get impacts for a specific project — only if the user owns or is member of that project."""
    # Verify the user has access to this project
    await _get_project_for_user(db, project_id, user)

    from app.models import RegulatoryUpdate
    result = await db.execute(
        select(RegulatoryImpact)
        .options(
            selectinload(RegulatoryImpact.update).selectinload(RegulatoryUpdate.source),
            selectinload(RegulatoryImpact.project)
        )
        .where(RegulatoryImpact.project_id == project_id)
        .order_by(RegulatoryImpact.created_at.desc())
    )
    impacts = result.scalars().all()
    return [_build_impact_dict(imp) for imp in impacts]


@router.get("/impacts", response_model=List[RegulatoryImpactOut])
async def get_all_impacts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Get all impacts — filtered to only the current user's accessible projects."""
    from app.models import RegulatoryUpdate

    accessible = _accessible_projects_subquery(user)

    result = await db.execute(
        select(RegulatoryImpact)
        .options(
            selectinload(RegulatoryImpact.update).selectinload(RegulatoryUpdate.source),
            selectinload(RegulatoryImpact.project)
        )
        # Only impacts belonging to projects this user can access
        .where(RegulatoryImpact.project_id.in_(select(accessible.c.id)))
        .order_by(RegulatoryImpact.created_at.desc())
        .limit(100)
    )
    impacts = result.scalars().all()
    return [_build_impact_dict(imp) for imp in impacts]


@router.get("/chat/{impact_id}")
async def get_impact_chat_history(
    impact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Get the persistent chat history for a specific regulatory impact."""
    from app.models import ChatMessage

    # Verify impact exists and belongs to a project the user can access
    impact = await db.scalar(select(RegulatoryImpact).where(RegulatoryImpact.id == impact_id))
    if not impact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Impact not found")

    await _get_project_for_user(db, impact.project_id, user)

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == f"regulatory_impact_{impact_id}")
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]


@router.post("/chat")
async def chat_about_impact(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Interactive chat with AI about a specific regulatory impact."""
    from app.models import ChatMessage

    impact_id = payload.get("impact_id")
    message = payload.get("message")

    if not impact_id or not message:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing impact_id or message")

    # Fetch impact and related update/project
    result = await db.execute(select(RegulatoryImpact).where(RegulatoryImpact.id == impact_id))
    impact = result.scalar_one_or_none()
    if not impact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Impact not found")

    # Ensure the user can access the project this impact belongs to
    await _get_project_for_user(db, impact.project_id, user)

    from app.services.ai import chat_with_ai

    project_result = await db.execute(select(Project).where(Project.id == impact.project_id))
    project = project_result.scalar_one_or_none()

    update_result = await db.execute(select(RegulatoryUpdate).where(RegulatoryUpdate.id == impact.update_id))
    update = update_result.scalar_one_or_none()

    session_id = f"regulatory_impact_{impact_id}"

    # Fetch full history from DB
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    db_history = history_result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in db_history]

    # Save user message
    user_msg = ChatMessage(project_id=project.id, session_id=session_id, role="user", content=message)
    db.add(user_msg)
    await db.commit()

    project_data = {
        "company_name": project.company_name,
        "company_role": project.company_role,
        "activity_sector": project.activity_sector,
        "product": project.product,
        "market": project.market,
        "standards": project.standards
    }

    context_message = f"""
    [CONTEXTE RÉGLEMENTAIRE SPÉCIFIQUE]
    Mise à jour : {update.title}
    Résumé : {update.summary}
    Impact identifié : {impact.impact_summary}
    Normes mises à jour : {impact.standards_updated}
    Procédures impactées : {impact.procedures_impacted}
    Actions suggérées : {impact.suggested_actions}
    
    QUESTION DU CONSULTANT : {message}
    """

    reply = await chat_with_ai(project_data, history, context_message)

    # Save assistant message
    ai_msg = ChatMessage(project_id=project.id, session_id=session_id, role="assistant", content=reply)
    db.add(ai_msg)
    await db.commit()

    return {"reply": reply}


@router.post("/sync")
async def sync_regulatory_updates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_consultant),
):
    """Manually trigger fetching regulatory updates."""
    import logging
    logger = logging.getLogger(__name__)
    from app.modules.regulatory_watch.workers import fetch_regulatory_updates
    
    logger.info(f"Manual sync triggered by user: {user.email}")
    try:
        await fetch_regulatory_updates()
        return {"status": "success", "message": "Regulatory updates synchronized successfully."}
    except Exception as e:
        logger.error(f"Error during manual sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to synchronize regulatory updates: {str(e)}"
        )
