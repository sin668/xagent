from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import uuid4

from redis.asyncio import from_url

from app.settings import settings


@dataclass(frozen=True)
class AgentRedisLock:
    redis_client: object
    key: str
    token: str
    acquired: bool

    async def release(self) -> bool:
        if not self.acquired:
            return False
        current_token = await self.redis_client.get(self.key)
        if isinstance(current_token, bytes):
            current_token = current_token.decode("utf-8")
        if current_token != self.token:
            return False
        await self.redis_client.delete(self.key)
        return True


class AgentRedisLockManager:
    """Short-term Redis mutex for scheduler jobs; not an audit source."""

    def __init__(
        self,
        *,
        redis_client: object | None = None,
        redis_url: str | None = None,
        namespace: str = "agent-scheduler-lock",
        ttl_seconds: int = 300,
    ) -> None:
        if redis_client is None:
            resolved_url = redis_url or settings.redis_url
            if not resolved_url:
                raise ValueError("Redis URL 未配置，无法创建 Agent 调度锁。")
            redis_client = from_url(resolved_url)
        self.redis_client = redis_client
        self.namespace = namespace
        self.ttl_seconds = ttl_seconds

    def build_key(self, job_id: str) -> str:
        return f"{self.namespace}:{job_id}"

    async def acquire(self, job_id: str) -> AgentRedisLock:
        key = self.build_key(job_id)
        token = uuid4().hex
        acquired = await self.redis_client.set(key, token, nx=True, ex=self.ttl_seconds)
        return AgentRedisLock(
            redis_client=self.redis_client,
            key=key,
            token=token,
            acquired=bool(acquired),
        )

    async def run_with_lock(self, job_id: str, callback: Callable[[], Awaitable[object]]) -> object:
        lock = await self.acquire(job_id)
        if not lock.acquired:
            return {"status": "skipped", "reason": "lock_not_acquired", "job_id": job_id}
        try:
            return await callback()
        finally:
            await lock.release()
