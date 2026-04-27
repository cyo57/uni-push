from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import DeliveryStatus, MessageStatus, MessageType


class PushRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    type: MessageType
    channel_ids: list[str] | None = None


class PushResponseData(BaseModel):
    message_id: str


class PushResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: PushResponseData


class DeliveryAttemptOut(BaseModel):
    at: datetime
    status_code: int | None
    response_body: str | None
    error: str | None
    retry_scheduled_in_seconds: int | None


class DeliveryOut(BaseModel):
    id: str
    channel_id: str
    channel_name: str
    channel_type: str
    status: DeliveryStatus
    attempt_count: int
    next_retry_at: datetime | None
    delivered_at: datetime | None
    final_error: str | None
    last_response_status: int | None
    last_response_body: str | None
    adapter_payload: dict
    attempt_logs: list[DeliveryAttemptOut]


class MessageListItem(BaseModel):
    id: str
    push_key_id: str
    push_key_business_name: str
    title: str
    message_type: MessageType
    status: MessageStatus
    created_at: datetime
    delivery_count: int
    success_count: int
    failed_count: int


class MessageListOut(BaseModel):
    items: list[MessageListItem]
    total: int


class MessageDetailOut(BaseModel):
    id: str
    push_key_id: str
    push_key_business_name: str
    source: str
    title: str
    content: str
    message_type: MessageType
    status: MessageStatus
    requested_channel_ids: list[str]
    request_payload: dict
    created_at: datetime
    deliveries: list[DeliveryOut]
