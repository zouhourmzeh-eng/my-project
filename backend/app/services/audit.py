from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_action(
    db: AsyncSession,
    user_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None = None,
    detail: str = "",
) -> None:
    db.add(AuditLog(
        user_id=user_id, action=action, entity=entity,
        entity_id=entity_id, detail=detail,
    ))
    await db.flush()
