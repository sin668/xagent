import asyncio

import pytest

from app.services.agent_locks import AgentRedisLockManager


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        if nx and key in self.values:
            return None
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex
        return True

    async def get(self, key: str):
        return self.values.get(key)

    async def delete(self, key: str):
        existed = key in self.values
        self.values.pop(key, None)
        self.expirations.pop(key, None)
        return int(existed)


@pytest.mark.asyncio
async def test_agent_redis_lock_acquires_short_term_mutex_and_releases_by_token() -> None:
    redis = FakeRedis()
    manager = AgentRedisLockManager(redis_client=redis, namespace="test-agent", ttl_seconds=45)

    first = await manager.acquire("source_discovery_hourly")
    second = await manager.acquire("source_discovery_hourly")

    assert first.acquired is True
    assert second.acquired is False
    assert redis.expirations["test-agent:source_discovery_hourly"] == 45

    await second.release()
    assert "test-agent:source_discovery_hourly" in redis.values

    await first.release()
    assert "test-agent:source_discovery_hourly" not in redis.values


@pytest.mark.asyncio
async def test_run_with_lock_skips_duplicate_execution_without_audit_side_effect() -> None:
    redis = FakeRedis()
    manager = AgentRedisLockManager(redis_client=redis, namespace="test-agent", ttl_seconds=30)
    calls: list[str] = []

    async def job() -> str:
        calls.append("ran")
        return "ok"

    held = await manager.acquire("retry_failed_tasks")
    result = await manager.run_with_lock("retry_failed_tasks", job)

    assert held.acquired is True
    assert result == {"status": "skipped", "reason": "lock_not_acquired", "job_id": "retry_failed_tasks"}
    assert calls == []

    await held.release()
    result_after_release = await manager.run_with_lock("retry_failed_tasks", job)

    assert result_after_release == "ok"
    assert calls == ["ran"]


@pytest.mark.asyncio
async def test_lock_release_does_not_delete_lock_owned_by_another_token() -> None:
    redis = FakeRedis()
    manager = AgentRedisLockManager(redis_client=redis, namespace="test-agent", ttl_seconds=30)

    lock = await manager.acquire("lead_extraction_interval")
    redis.values["test-agent:lead_extraction_interval"] = "another-token"

    await lock.release()

    assert redis.values["test-agent:lead_extraction_interval"] == "another-token"
