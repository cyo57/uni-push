from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.sanitization import sanitize_for_storage
from app.models.audit import AuditLog
from app.models.user import User


async def record_audit_log(
    session: AsyncSession,
    *,
    actor: User | None,
    action: str,
    target_type: str,
    target_id: str | None = None,
    detail: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor.id if actor is not None else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=sanitize_for_storage(detail or {}),
    )
    session.add(entry)
    return entry


async def list_audit_logs(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
    action: str | None = None,
    target_type: str | None = None,
    actor_user_id: str | None = None,
) -> tuple[list[AuditLog], int]:
    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if target_type:
        query = query.where(AuditLog.target_type == target_type)
        count_query = count_query.where(AuditLog.target_type == target_type)
    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
        count_query = count_query.where(AuditLog.actor_user_id == actor_user_id)

    total = await session.scalar(count_query)
    result = await session.scalars(
        query.options(selectinload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result), int(total or 0)
