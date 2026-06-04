from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable
from threading import Lock
from time import perf_counter
from typing import Any


logger = logging.getLogger("uvicorn.error")


class AgentThreadRunner:
    _lock = Lock()
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm-agent")
    _futures: set[Future] = set()

    @classmethod
    def submit(cls, *, name: str, target: Callable[[], Any]) -> Future:
        def run_agent() -> Any:
            started_at = perf_counter()
            logger.info(
                "Agent 线程池任务开始：name=%s active=%s tracked=%s",
                name,
                cls.active_count(),
                cls.tracked_count(),
            )
            try:
                return target()
            finally:
                logger.info(
                    "Agent 线程池任务结束：name=%s duration_ms=%.2f active=%s tracked=%s",
                    name,
                    (perf_counter() - started_at) * 1000,
                    cls.active_count(),
                    cls.tracked_count(),
                )

        future = cls._executor.submit(run_agent)

        def cleanup(done_future: Future) -> None:
            with cls._lock:
                cls._futures.discard(done_future)
                active_count = sum(1 for future in cls._futures if not future.done())
                tracked_count = len(cls._futures)
            logger.info(
                "Agent 线程池任务回收：name=%s active=%s tracked=%s cancelled=%s exception=%s",
                name,
                active_count,
                tracked_count,
                done_future.cancelled(),
                None if done_future.cancelled() else done_future.exception(),
            )

        with cls._lock:
            cls._futures.add(future)
            active_count = sum(1 for future in cls._futures if not future.done())
            tracked_count = len(cls._futures)
        logger.info(
            "Agent 线程池任务提交：name=%s active=%s tracked=%s",
            name,
            active_count,
            tracked_count,
        )
        future.add_done_callback(cleanup)
        return future

    @classmethod
    def start(cls, *, name: str, target: Callable[[], Any]) -> Future:
        def run_with_log() -> None:
            try:
                target()
            except Exception:
                logger.exception("Agent 后台线程执行异常：%s", name)

        return cls.submit(name=name, target=run_with_log)

    @classmethod
    def active_count(cls) -> int:
        with cls._lock:
            return sum(1 for future in cls._futures if not future.done())

    @classmethod
    def tracked_count(cls) -> int:
        with cls._lock:
            return len(cls._futures)

    @classmethod
    def shutdown(cls, *, wait: bool = True) -> None:
        cls._executor.shutdown(wait=wait, cancel_futures=False)
        with cls._lock:
            cls._futures.clear()
