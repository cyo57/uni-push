from __future__ import annotations

import base64
import hashlib
import hmac
from secrets import token_bytes

from app.core.config import get_settings

ENVELOPE_PREFIX = "enc:v1:"
_NONCE_SIZE = 16
_MAC_SIZE = 32


def _master_key() -> bytes:
    settings = get_settings()
    return hashlib.sha256(settings.effective_data_encryption_key.encode("utf-8")).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        counter_bytes = counter.to_bytes(4, "big")
        blocks.append(hmac.new(key, b"stream:" + nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def is_encrypted_secret(value: str | None) -> bool:
    return bool(value and value.startswith(ENVELOPE_PREFIX))


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    if is_encrypted_secret(value):
        return value

    key = _master_key()
    plaintext = value.encode("utf-8")
    nonce = token_bytes(_NONCE_SIZE)
    stream = _keystream(key, nonce, len(plaintext))
    ciphertext = bytes(left ^ right for left, right in zip(plaintext, stream, strict=True))
    mac = hmac.new(key, b"mac:" + nonce + ciphertext, hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(nonce + mac + ciphertext).decode("ascii")
    return f"{ENVELOPE_PREFIX}{token}"


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    if not is_encrypted_secret(value):
        return value

    key = _master_key()
    raw = base64.urlsafe_b64decode(value[len(ENVELOPE_PREFIX) :].encode("ascii"))
    nonce = raw[:_NONCE_SIZE]
    mac = raw[_NONCE_SIZE : _NONCE_SIZE + _MAC_SIZE]
    ciphertext = raw[_NONCE_SIZE + _MAC_SIZE :]
    expected_mac = hmac.new(key, b"mac:" + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("Encrypted secret integrity check failed")

    stream = _keystream(key, nonce, len(ciphertext))
    plaintext = bytes(left ^ right for left, right in zip(ciphertext, stream, strict=True))
    return plaintext.decode("utf-8")


def mask_secret(value: str | None) -> str | None:
    plaintext = decrypt_secret(value)
    if not plaintext:
        return None
    if len(plaintext) <= 4:
        return "*" * len(plaintext)
    return f"{plaintext[:2]}***{plaintext[-2:]}"
