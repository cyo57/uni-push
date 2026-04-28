from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class ChannelType(StrEnum):
    WECOM_BOT = "wecom_bot"
    DINGTALK_BOT = "dingtalk_bot"
    FEISHU_BOT = "feishu_bot"
    GENERIC_WEBHOOK = "generic_webhook"


class MessageType(StrEnum):
    TEXT = "text"
    MARKDOWN = "markdown"


class MessageSource(StrEnum):
    GET = "get"
    POST = "post"


class MessageStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"
