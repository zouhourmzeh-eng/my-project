from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.api.deps import get_current_user, get_db
from app.models import User, ChatMessage
from app.services.ai import analyze_standards_ai, chat_with_ai
from app.api.projects import _get_project_for_user

router = APIRouter(prefix="/ai", tags=["ai"])

@router.get("/projects/{project_id}/sessions")
async def get_chat_sessions(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    await _get_project_for_user(db, project_id, user)
    # Group by session_id to get the first message of each session
    # A simple way is to fetch all messages and group in python, or use a window function/distinct.
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    sessions = {}
    for m in messages:
        if m.session_id not in sessions:
            # use the first user message or first assistant message as title
            sessions[m.session_id] = {
                "id": m.session_id,
                "title": m.content[:50] + "..." if len(m.content) > 50 else m.content,
                "created_at": m.created_at.isoformat()
            }
    # return list of sessions, most recent first
    return sorted(list(sessions.values()), key=lambda x: x["created_at"], reverse=True)

@router.get("/projects/{project_id}/chat-history")
async def get_chat_history(
    project_id: int,
    session_id: str = "default",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    await _get_project_for_user(db, project_id, user)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]

@router.delete("/projects/{project_id}/chat-history")
async def clear_chat_history(
    project_id: int,
    session_id: str = "default",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    await _get_project_for_user(db, project_id, user)
    await db.execute(delete(ChatMessage).where(ChatMessage.project_id == project_id).where(ChatMessage.session_id == session_id))
    
    greeting = "Bonjour ! J'ai analysé votre projet. Voici les normes recommandées pour votre secteur et produit. Avez-vous des questions sur ces normes ou souhaitez-vous des explications ?"
    msg = ChatMessage(project_id=project_id, session_id=session_id, role="assistant", content=greeting)
    db.add(msg)
    
    await db.commit()
    return {"message": "Chat history cleared"}

@router.post("/analyze")
async def analyze_standards(
    project_data: dict = Body(...),
    session_id: str = Body("default"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project_id = project_data.get("id")
    if project_id:
        await _get_project_for_user(db, project_id, user)
        
    standards = await analyze_standards_ai(project_data)
    
    if project_id:
        # Store mappings in ProjectRegulation table
        from app.models import ProjectRegulation
        # Clear existing ones for this project
        await db.execute(delete(ProjectRegulation).where(ProjectRegulation.project_id == project_id))
        
        for std_name in standards:
            reg = ProjectRegulation(
                project_id=project_id,
                regulation_name=std_name,
                justification="Identified by AI Assistant during project analysis."
            )
            db.add(reg)
            
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.project_id == project_id)
            .where(ChatMessage.session_id == session_id)
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            greeting = "Bonjour ! J'ai analysé votre projet. Voici les normes recommandées pour votre secteur et produit. Avez-vous des questions sur ces normes ou souhaitez-vous des explications ?"
            msg = ChatMessage(project_id=project_id, session_id=session_id, role="assistant", content=greeting)
            db.add(msg)
            
        await db.commit()
            
    return {"standards": standards}

@router.post("/chat")
async def chat(
    project_data: dict = Body(...),
    message: str = Body(...),
    session_id: str = Body("default"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project_id = project_data.get("id")
    if project_id:
        await _get_project_for_user(db, project_id, user)
        
        user_msg = ChatMessage(project_id=project_id, session_id=session_id, role="user", content=message)
        db.add(user_msg)
        await db.commit()
    
    history = []
    if project_id:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.project_id == project_id)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        history_msgs = result.scalars().all()
        if history_msgs:
            history = [{"role": m.role, "content": m.content} for m in history_msgs[:-1]]
    
    response = await chat_with_ai(project_data, history, message)
    
    if project_id:
        assistant_msg = ChatMessage(project_id=project_id, session_id=session_id, role="assistant", content=response)
        db.add(assistant_msg)
        await db.commit()
        
    return {"response": response}
