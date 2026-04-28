from pydantic import BaseModel


class DashboardSummary(BaseModel):
    request_count: int
    success_count: int
    failed_count: int


class DashboardStats(BaseModel):
    total_users: int
    total_channels: int
    total_messages: int
    recent_requests: int


class DailyRequest(BaseModel):
    date: str
    value: int


class ChannelUsage(BaseModel):
    name: str
    value: int
    color: str


class ErrorReasonStat(BaseModel):
    reason: str
    count: int


class HotPushKeyStat(BaseModel):
    business_name: str
    count: int


class ChannelPerformanceStat(BaseModel):
    channel_name: str
    channel_type: str
    success_count: int
    failed_count: int
    success_rate: float
