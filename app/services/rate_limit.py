from __future__ import annotations

from redis.asyncio import Redis

RATE_LIMIT_LUA = """
local current = tonumber(redis.call("GET", KEYS[1]) or "0")
local limit = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
if current >= limit then
  return {0, current, redis.call("TTL", KEYS[1])}
end
current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], ttl)
end
return {1, current, redis.call("TTL", KEYS[1])}
"""


async def allow_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    ttl_seconds: int = 60,
) -> tuple[bool, int, int]:
    allowed, current, ttl = await redis.eval(RATE_LIMIT_LUA, 1, key, limit, ttl_seconds)
    return bool(allowed), int(current), int(ttl)
