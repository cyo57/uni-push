from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx

from app.core.crypto import decrypt_secret
from app.core.enums import ChannelType, MessageType
from app.core.sanitization import sanitize_for_storage, sanitize_text
from app.models.channel import Channel


@dataclass
class AdapterSendResult:
    success: bool
    retryable: bool
    status_code: int | None
    response_body: str | None
    error: str | None = None


def build_adapter_payload(
    channel_type: ChannelType,
    title: str,
    content: str,
    message_type: MessageType,
) -> dict:
    if channel_type == ChannelType.WECOM_BOT:
        if message_type == MessageType.TEXT:
            return {"msgtype": "text", "text": {"content": f"{title}\n{content}"}}
        return {"msgtype": "markdown", "markdown": {"content": f"## {title}\n{content}"}}

    if channel_type == ChannelType.DINGTALK_BOT:
        if message_type == MessageType.TEXT:
            return {"msgtype": "text", "text": {"content": f"{title}\n{content}"}}
        return {"msgtype": "markdown", "markdown": {"title": title, "text": content}}

    if channel_type == ChannelType.FEISHU_BOT:
        if message_type == MessageType.MARKDOWN:
            return {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": title,
                            "content": [[{"tag": "text", "text": content}]],
                        }
                    }
                },
            }
        return {"msg_type": "text", "content": {"text": f"{title}\n{content}"}}

    return {
        "title": title,
        "content": content,
        "type": message_type.value,
    }


def build_channel_request(channel: Channel, payload: dict) -> tuple[str, dict, dict]:
    url = channel.webhook_url
    headers = {"Content-Type": "application/json"}
    secret = decrypt_secret(channel.secret)
    if channel.type == ChannelType.DINGTALK_BOT and secret:
        timestamp = str(int(time.time() * 1000))
        secret_enc = secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{secret}".encode()
        sign = quote_plus(
            base64.b64encode(hmac.new(secret_enc, string_to_sign, hashlib.sha256).digest()).decode(
                "utf-8"
            )
        )
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}timestamp={timestamp}&sign={sign}"
    if channel.type == ChannelType.FEISHU_BOT and secret:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret}".encode()
        sign = base64.b64encode(hmac.new(string_to_sign, digestmod=hashlib.sha256).digest()).decode(
            "utf-8"
        )
        payload = {"timestamp": timestamp, "sign": sign, **payload}
    return url, headers, payload


def _response_text(response: httpx.Response) -> str:
    try:
        data = response.json()
        return json.dumps(sanitize_for_storage(data), ensure_ascii=False)
    except Exception:
        return sanitize_text(response.text) or ""


def _parse_channel_success(channel_type: ChannelType, response: httpx.Response) -> tuple[bool, str]:
    body = _response_text(response)
    if response.status_code < 200 or response.status_code >= 300:
        return False, body

    try:
        data = response.json()
    except Exception:
        return True, body

    if channel_type == ChannelType.WECOM_BOT:
        return data.get("errcode") == 0, body
    if channel_type == ChannelType.DINGTALK_BOT:
        return data.get("errcode") == 0, body
    if channel_type == ChannelType.FEISHU_BOT:
        return (
            data.get("StatusCode") == 0 or data.get("code") == 0 or data.get("errcode") == 0
        ), body
    return True, body


async def send_via_channel(
    client: httpx.AsyncClient,
    channel: Channel,
    payload: dict,
) -> AdapterSendResult:
    try:
        url, headers, body = build_channel_request(channel, payload)
    except Exception as exc:
        return AdapterSendResult(
            success=False,
            retryable=False,
            status_code=None,
            response_body=None,
            error=sanitize_text(str(exc)) or "Failed to prepare channel request",
        )
    try:
        response = await client.post(url, headers=headers, json=body)
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        return AdapterSendResult(
            success=False,
            retryable=True,
            status_code=None,
            response_body=None,
            error=sanitize_text(str(exc)),
        )

    success, response_body = _parse_channel_success(channel.type, response)
    retryable = response.status_code >= 500 or response.status_code == 429
    return AdapterSendResult(
        success=success,
        retryable=retryable,
        status_code=response.status_code,
        response_body=response_body,
        error=None if success else sanitize_text("Channel rejected request"),
    )
