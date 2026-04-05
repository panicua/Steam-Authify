from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_audit(
    session: AsyncSession,
    *,
    actor_type: str,
    actor_id: str,
    entity_type: str,
    entity_id: int | None,
    action: str,
    payload: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        payload=payload,
    )
    session.add(entry)
    await session.flush()
    return entry
