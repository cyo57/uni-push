from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.enums import DeliveryStatus
from app.db.session import get_session
from app.models.channel import Channel
from app.models.message import Delivery, Message
from app.models.user import User
from app.schemas.dashboard import (
    ChannelUsage,
    DailyRequest,
    DashboardStats,
    DashboardSummary,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _days_ago(days: int) -> datetime:
    now = datetime.now(UTC)
    return now - timedelta(days=days)


def _format_date(dt: datetime) -> str:
    return dt.strftime("%m.%d")


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    from datetime import time as dt_time

    local_now = datetime.now().astimezone()
    local_start = datetime.combine(local_now.date(), dt_time.min, tzinfo=local_now.tzinfo)
    start = local_start.astimezone(UTC)

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


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardStats:
    cutoff = _days_ago(days)

    total_users_query = select(func.count()).select_from(User)
    total_channels_query = (
        select(func.count()).select_from(Channel).where(Channel.is_deleted == False)  # noqa: E712
    )
    total_messages_query = select(func.count()).select_from(Message)
    recent_requests_query = select(func.count()).select_from(Message).where(Message.created_at >= cutoff)

    if current_user.role.value != "admin":
        total_users_query = total_users_query.where(User.id == current_user.id)
        total_messages_query = total_messages_query.where(Message.user_id == current_user.id)
        recent_requests_query = recent_requests_query.where(Message.user_id == current_user.id)
        # 非管理员只能看到自己创建的通道
        total_channels_query = total_channels_query.where(
            Channel.created_by_id == current_user.id
        )

    total_users = await session.scalar(total_users_query)
    total_channels = await session.scalar(total_channels_query)
    total_messages = await session.scalar(total_messages_query)
    recent_requests = await session.scalar(recent_requests_query)

    return DashboardStats(
        total_users=int(total_users or 0),
        total_channels=int(total_channels or 0),
        total_messages=int(total_messages or 0),
        recent_requests=int(recent_requests or 0),
    )


@router.get("/requests", response_model=list[DailyRequest])
async def get_dashboard_requests(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DailyRequest]:
    cutoff = _days_ago(days)

    # SQLite strftime 分组
    query = (
        select(
            func.strftime("%m.%d", Message.created_at).label("date"),
            func.count().label("count"),
        )
        .where(Message.created_at >= cutoff)
        .group_by(func.strftime("%m.%d", Message.created_at))
        .order_by(func.strftime("%m.%d", Message.created_at))
    )

    if current_user.role.value != "admin":
        query = query.where(Message.user_id == current_user.id)

    result = await session.execute(query)
    rows = result.all()

    # 填充没有数据的日期为 0
    date_counts = {row.date: row.count for row in rows}
    filled: list[DailyRequest] = []
    for i in range(days - 1, -1, -1):
        d = _days_ago(i)
        date_str = _format_date(d)
        filled.append(DailyRequest(date=date_str, value=date_counts.get(date_str, 0)))

    return filled


_CHANNEL_COLORS: dict[str, str] = {
    "wecom_bot": "#3b82f6",
    "dingtalk_bot": "#10b981",
}


@router.get("/channels", response_model=list[ChannelUsage])
async def get_dashboard_channels(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChannelUsage]:
    query = (
        select(
            Channel.type.label("channel_type"),
            func.count().label("count"),
        )
        .join(Delivery, Delivery.channel_id == Channel.id)
        .where(
            Channel.is_deleted == False,  # noqa: E712
            Channel.is_enabled == True,  # noqa: E712
        )
        .group_by(Channel.type)
    )

    if current_user.role.value != "admin":
        query = query.join(Message, Message.id == Delivery.message_id).where(
            Message.user_id == current_user.id
        )

    result = await session.execute(query)
    rows = result.all()

    return [
        ChannelUsage(
            name=row.channel_type,
            value=row.count,
            color=_CHANNEL_COLORS.get(row.channel_type, "#8b5cf6"),
        )
        for row in rows
    ]
