from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic

from fastapi import Request

from app.core.errors import AppError


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int
    message: str = "请求过于频繁，请稍后再试"


_buckets: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or "unknown"
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def rate_limit(key: str, rule: RateLimitRule) -> None:
    now = monotonic()
    bucket = _buckets[key]
    cutoff = now - rule.window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= rule.limit:
        raise AppError(429, rule.message, code=429)
    bucket.append(now)


def limit_request(request: Request, scope: str, *parts: object, rule: RateLimitRule) -> None:
    normalized_parts = [str(part).strip().lower() for part in parts if part is not None and str(part).strip()]
    rate_limit(":".join([scope, "ip", client_ip(request)]), rule)
    if normalized_parts:
        rate_limit(":".join([scope, "key", *normalized_parts]), rule)


def limit_key(scope: str, *parts: object, rule: RateLimitRule) -> None:
    normalized_parts = [str(part).strip().lower() for part in parts if part is not None and str(part).strip()]
    key = ":".join([scope, *normalized_parts])
    rate_limit(key, rule)


def reset_rate_limits() -> None:
    _buckets.clear()
