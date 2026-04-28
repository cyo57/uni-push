from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.models.user import User
from app.schemas.audit import AuditLogListOut
from app.services.audit import list_audit_logs
from app.services.serializers import audit_log_to_out

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=AuditLogListOut)
async def get_audit_logs(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None, min_length=1, max_length=64),
    target_type: str | None = Query(default=None, min_length=1, max_length=64),
    actor_user_id: str | None = Query(default=None, min_length=1, max_length=64),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AuditLogListOut:
    items, total = await list_audit_logs(
        session,
        offset=offset,
        limit=limit,
        action=action,
        target_type=target_type,
        actor_user_id=actor_user_id,
    )
    return AuditLogListOut(items=[audit_log_to_out(item) for item in items], total=total)
