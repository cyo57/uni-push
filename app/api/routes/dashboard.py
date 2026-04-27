from datetime import UTC, datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.enums import DeliveryStatus
from app.db.session import get_session
from app.models.message import Delivery, Message
from app.models.user import User
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def start_of_today_utc() -> datetime:
    local_now = datetime.now().astimezone()
    local_start = datetime.combine(local_now.date(), time.min, tzinfo=local_now.tzinfo)
    return local_start.astimezone(UTC)


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    start = start_of_today_utc()
    message_query = select(func.count()).select_from(Message).where(Message.created_at >= start)
    success_query = (
        select(func.count())
        .select_from(Delivery)
        .where(
            Delivery.created_at >= start,
            Delivery.status == DeliveryStatus.SUCCESS,
        )
    )
    failed_query = (
        select(func.count())
        .select_from(Delivery)
        .where(
            Delivery.created_at >= start,
            Delivery.status == DeliveryStatus.FAILED,
        )
    )

    if current_user.role.value != "admin":
        message_query = message_query.where(Message.user_id == current_user.id)
        success_query = success_query.join(Message).where(Message.user_id == current_user.id)
        failed_query = failed_query.join(Message).where(Message.user_id == current_user.id)

    request_count = await session.scalar(message_query)
    success_count = await session.scalar(success_query)
    failed_count = await session.scalar(failed_query)
    return DashboardSummary(
        request_count=int(request_count or 0),
        success_count=int(success_count or 0),
        failed_count=int(failed_count or 0),
    )
