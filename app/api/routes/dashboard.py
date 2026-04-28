from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.enums import DeliveryStatus
from app.db.session import get_session
from app.models.channel import Channel
from app.models.message import Delivery, Message
from app.models.push_key import PushKey
from app.models.user import User
from app.schemas.dashboard import (
    ChannelPerformanceStat,
    ChannelUsage,
    DailyRequest,
    DashboardStats,
    DashboardSummary,
    ErrorReasonStat,
    HotPushKeyStat,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _days_ago(days: int) -> datetime:
    now = datetime.now(UTC)
    return now - timedelta(days=days)


def _format_date(dt: datetime) -> str:
    return dt.strftime("%m.%d")


def _day_bucket_expression(session: AsyncSession):
    dialect = session.bind.dialect.name if session.bind is not None else ""
    if dialect == "postgresql":
        return func.to_char(func.date_trunc("day", Message.created_at), "YYYY-MM-DD")
    if dialect == "mysql":
        return func.date_format(Message.created_at, "%Y-%m-%d")
    return func.strftime("%Y-%m-%d", Message.created_at)


def _apply_message_user_scope(query, current_user: User):
    if current_user.role.value != "admin":
        query = query.where(Message.user_id == current_user.id)
    return query


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
        select(func.count()).select_from(Channel).where(Channel.is_deleted.is_(False))
    )
    total_messages_query = select(func.count()).select_from(Message)
    recent_requests_query = (
        select(func.count()).select_from(Message).where(Message.created_at >= cutoff)
    )

    if current_user.role.value != "admin":
        from app.services.channels import list_authorized_channel_ids

        total_users_query = total_users_query.where(User.id == current_user.id)
        total_messages_query = total_messages_query.where(Message.user_id == current_user.id)
        recent_requests_query = recent_requests_query.where(Message.user_id == current_user.id)
        total_channels_query = total_channels_query.where(
            Channel.id.in_(await list_authorized_channel_ids(session, current_user.id))
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

    day_bucket = _day_bucket_expression(session)
    query = (
        select(
            day_bucket.label("date"),
            func.count().label("count"),
        )
        .where(Message.created_at >= cutoff)
        .group_by(day_bucket)
        .order_by(day_bucket)
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
        bucket = d.date().isoformat()
        filled.append(DailyRequest(date=_format_date(d), value=date_counts.get(bucket, 0)))

    return filled


_CHANNEL_COLORS = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#8b5cf6",
    "#ef4444",
    "#06b6d4",
    "#f97316",
    "#84cc16",
]


@router.get("/channels", response_model=list[ChannelUsage])
async def get_dashboard_channels(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChannelUsage]:
    query = (
        select(
            Channel.id.label("channel_id"),
            Channel.name.label("channel_name"),
            func.count().label("count"),
        )
        .join(Delivery, Delivery.channel_id == Channel.id)
        .where(
            Channel.is_deleted.is_(False),
            Channel.is_enabled.is_(True),
        )
        .group_by(Channel.id, Channel.name)
        .order_by(func.count().desc(), Channel.name.asc())
    )

    if current_user.role.value != "admin":
        query = query.join(Message, Message.id == Delivery.message_id).where(
            Message.user_id == current_user.id
        )

    result = await session.execute(query)
    rows = result.all()

    return [
        ChannelUsage(
            name=row.channel_name,
            value=row.count,
            color=_CHANNEL_COLORS[index % len(_CHANNEL_COLORS)],
        )
        for index, row in enumerate(rows)
    ]


@router.get("/error-reasons", response_model=list[ErrorReasonStat])
async def get_dashboard_error_reasons(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ErrorReasonStat]:
    cutoff = _days_ago(days)
    query = (
        select(
            func.coalesce(Delivery.final_error, "Unknown error").label("reason"),
            func.count().label("count"),
        )
        .join(Message, Message.id == Delivery.message_id)
        .where(
            Delivery.created_at >= cutoff,
            Delivery.status.in_([DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]),
        )
        .group_by("reason")
        .order_by(func.count().desc(), "reason")
        .limit(5)
    )
    query = _apply_message_user_scope(query, current_user)
    rows = (await session.execute(query)).all()
    return [ErrorReasonStat(reason=row.reason, count=row.count) for row in rows]


@router.get("/hot-keys", response_model=list[HotPushKeyStat])
async def get_dashboard_hot_keys(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[HotPushKeyStat]:
    cutoff = _days_ago(days)
    query = (
        select(
            PushKey.business_name.label("business_name"),
            func.count(Message.id).label("count"),
        )
        .join(PushKey, PushKey.id == Message.push_key_id)
        .where(Message.created_at >= cutoff)
        .group_by(PushKey.business_name)
        .order_by(func.count(Message.id).desc(), PushKey.business_name.asc())
        .limit(5)
    )
    query = _apply_message_user_scope(query, current_user)
    rows = (await session.execute(query)).all()
    return [HotPushKeyStat(business_name=row.business_name, count=row.count) for row in rows]


@router.get("/channel-performance", response_model=list[ChannelPerformanceStat])
async def get_dashboard_channel_performance(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ChannelPerformanceStat]:
    cutoff = _days_ago(days)
    query = (
        select(
            Channel.name.label("channel_name"),
            Channel.type.label("channel_type"),
            func.sum(case((Delivery.status == DeliveryStatus.SUCCESS, 1), else_=0)).label(
                "success_count"
            ),
            func.sum(
                case(
                    (
                        Delivery.status.in_([DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]),
                        1,
                    ),
                    else_=0,
                )
            ).label("failed_count"),
        )
        .join(Delivery, Delivery.channel_id == Channel.id)
        .join(Message, Message.id == Delivery.message_id)
        .where(Delivery.created_at >= cutoff)
        .group_by(Channel.id, Channel.name, Channel.type)
        .order_by(Channel.name.asc())
    )
    query = _apply_message_user_scope(query, current_user)
    rows = (await session.execute(query)).all()
    result: list[ChannelPerformanceStat] = []
    for row in rows:
        success_count = int(row.success_count or 0)
        failed_count = int(row.failed_count or 0)
        total = success_count + failed_count
        result.append(
            ChannelPerformanceStat(
                channel_name=row.channel_name,
                channel_type=row.channel_type,
                success_count=success_count,
                failed_count=failed_count,
                success_rate=round((success_count / total) * 100, 2) if total > 0 else 0.0,
            )
        )
    return result
