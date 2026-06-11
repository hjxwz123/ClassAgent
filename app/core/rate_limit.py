from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic, time
from uuid import uuid4

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger("app.rate_limit")


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int
    message: str = "请求过于频繁，请稍后再试"


# 进程内回退桶：仅在 Redis 不可用时使用（注意：单进程、不跨 worker/副本共享）。
_buckets: dict[str, deque[float]] = defaultdict(deque)

# Redis 探测结果缓存：None=未探测；False=不可用(用内存)；其余为 redis 客户端实例。
_redis_state: object | None = None


def _get_redis():
    """返回可用的 Redis 客户端；不可用时返回 None（首次探测后缓存结果）。"""
    global _redis_state
    if _redis_state is None:
        try:
            import redis  # 局部导入，避免在无 redis 环境下产生额外开销

            client = redis.Redis.from_url(
                get_settings().redis_url,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            client.ping()
            _redis_state = client
        except Exception:  # 连接失败/未安装：退回进程内内存限流
            logger.warning("限流 Redis 不可用，退回进程内内存限流（不跨 worker，重启清零）")
            _redis_state = False
    return _redis_state or None


def client_ip(request: Request) -> str:
    """解析客户端真实 IP。

    默认不信任 X-Forwarded-For（可被任意伪造，每次伪造一个新 IP 即可绕过 IP 维度限流）。
    仅当部署在反向代理之后并显式设置 rate_limit_trusted_proxy_count>0 时，
    才从 XFF 链尾部跳过相应数量的可信代理跳数，取出真实客户端 IP。
    """
    peer = request.client.host if request.client else "unknown"
    hops = get_settings().rate_limit_trusted_proxy_count
    if hops > 0:
        forwarded = request.headers.get("x-forwarded-for", "")
        chain = [part.strip() for part in forwarded.split(",") if part.strip()]
        if chain:
            index = len(chain) - hops - 1
            if index < 0:
                index = 0
            return chain[index] or peer
    return peer


def _rate_limit_memory(key: str, rule: RateLimitRule) -> None:
    now = monotonic()
    bucket = _buckets[key]
    cutoff = now - rule.window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= rule.limit:
        raise AppError(429, rule.message, code=429)
    bucket.append(now)


def _rate_limit_redis(client, key: str, rule: RateLimitRule) -> None:
    """基于 Redis 有序集合的滑动窗口限流，跨进程/副本共享计数。"""
    now = time()
    redis_key = f"ratelimit:{key}"
    member = f"{now:.6f}:{uuid4().hex}"
    try:
        pipe = client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - rule.window_seconds)
        pipe.zadd(redis_key, {member: now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, rule.window_seconds + 1)
        results = pipe.execute()
        count = int(results[2])
    except Exception:
        # Redis 临时故障：本次退回内存，不因限流组件抖动而阻断业务请求
        _rate_limit_memory(key, rule)
        return
    if count > rule.limit:
        # 被拒绝的请求不应占用窗口名额，移除刚写入的成员后再拒绝
        try:
            client.zrem(redis_key, member)
        except Exception:
            pass
        raise AppError(429, rule.message, code=429)


def rate_limit(key: str, rule: RateLimitRule) -> None:
    client = _get_redis()
    if client is not None:
        _rate_limit_redis(client, key, rule)
    else:
        _rate_limit_memory(key, rule)


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
    """清空所有限流计数（主要供测试使用）。"""
    _buckets.clear()
    client = _get_redis()
    if client is not None:
        try:
            for redis_key in client.scan_iter(match="ratelimit:*", count=500):
                client.delete(redis_key)
        except Exception:
            pass
