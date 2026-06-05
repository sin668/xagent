from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar


logger = logging.getLogger("app.agent_run")

StateT = TypeVar("StateT")


def log_agent_run_start(
    *,
    agent_type: str,
    request_id: str,
    agent_mode: str,
    trigger_source: str,
    agent_service_run_id: str,
) -> None:
    logger.info(
        "agent_run_start agent_type=%s request_id=%s agent_mode=%s trigger_source=%s agent_service_run_id=%s",
        agent_type,
        request_id,
        agent_mode,
        trigger_source,
        agent_service_run_id,
    )


def log_agent_run_succeeded(
    *,
    agent_type: str,
    request_id: str,
    agent_mode: str,
    agent_service_run_id: str,
    executed_node_count: int,
) -> None:
    logger.info(
        "agent_run_succeeded agent_type=%s request_id=%s agent_mode=%s agent_service_run_id=%s status=succeeded executed_node_count=%s",
        agent_type,
        request_id,
        agent_mode,
        agent_service_run_id,
        executed_node_count,
    )


def log_agent_run_failed(
    *,
    agent_type: str,
    request_id: str,
    agent_mode: str,
    agent_service_run_id: str,
    error_type: str,
    error_message: str,
) -> None:
    logger.info(
        "agent_run_failed agent_type=%s request_id=%s agent_mode=%s agent_service_run_id=%s status=failed error_type=%s error_message=%s",
        agent_type,
        request_id,
        agent_mode,
        agent_service_run_id,
        error_type,
        error_message,
    )


def run_logged_node(*, agent_type: str, node_name: str, func: Callable[[StateT], StateT], state: StateT) -> StateT:
    logger.info("agent_node_start agent_type=%s node=%s", agent_type, node_name)
    try:
        result = func(state)
    except Exception as exc:
        logger.info("agent_node_failed agent_type=%s node=%s error_message=%s", agent_type, node_name, str(exc))
        raise
    logger.info("agent_node_finish agent_type=%s node=%s", agent_type, node_name)
    return result
