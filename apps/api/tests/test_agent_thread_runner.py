from threading import Event

from app.services.agent_thread_runner import AgentThreadRunner


def test_agent_thread_runner_removes_finished_threads_from_active_set() -> None:
    completed = Event()

    future = AgentThreadRunner.start(name="test-agent-thread", target=completed.set)
    future.result(timeout=1)

    assert completed.is_set()
    assert AgentThreadRunner.active_count() == 0
    assert AgentThreadRunner.tracked_count() == 0
