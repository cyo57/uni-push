from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx

from app.core.enums import ChannelType, MessageType
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

    if message_type == MessageType.TEXT:
        return {"msgtype": "text", "text": {"content": f"{title}\n{content}"}}
    return {"msgtype": "markdown", "markdown": {"title": title, "text": content}}


def build_channel_request(channel: Channel, payload: dict) -> tuple[str, dict, dict]:
    url = channel.webhook_url
    headers = {"Content-Type": "application/json"}
    if channel.type == ChannelType.DINGTALK_BOT and channel.secret:
        timestamp = str(int(time.time() * 1000))
        secret_enc = channel.secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{channel.secret}".encode()
        sign = quote_plus(
            base64.b64encode(hmac.new(secret_enc, string_to_sign, hashlib.sha256).digest()).decode(
                "utf-8"
            )
        )
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}timestamp={timestamp}&sign={sign}"
    return url, headers, payload


def _response_text(response: httpx.Response) -> str:
    try:
        data = response.json()
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return response.text


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
    return True, body


async def send_via_channel(
    client: httpx.AsyncClient,
    channel: Channel,
    payload: dict,
) -> AdapterSendResult:
    url, headers, body = build_channel_request(channel, payload)
    try:
        response = await client.post(url, headers=headers, json=body)
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        return AdapterSendResult(
            success=False,
            retryable=True,
            status_code=None,
            response_body=None,
            error=str(exc),
        )

    success, response_body = _parse_channel_success(channel.type, response)
    retryable = response.status_code >= 500 or response.status_code == 429
    return AdapterSendResult(
        success=success,
        retryable=retryable,
        status_code=response.status_code,
        response_body=response_body,
        error=None if success else "Channel rejected request",
    )
