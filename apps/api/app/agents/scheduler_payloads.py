from __future__ import annotations

from typing import Any


def build_external_source_discovery_input(
    *,
    request_id: str,
    market: str = "Russia",
    channel_strategy: dict[str, Any] | None = None,
    seed_urls: list[str] | None = None,
    search_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "discovery_run_id": request_id,
        "trigger_source": "scheduler_external_source_discovery",
        "market": market,
        "channel_strategy": channel_strategy
        or {
            "keywords": ["автодилер", "автосалон", "used cars", "import cars"],
            "target_segments": ["used car dealers", "vehicle import/export dealers"],
            "risk_policy": "仅允许公开来源发现；不得登录、私信、绕过反爬或由外部 Agent 直接写入业务表。",
        },
        "seed_urls": seed_urls or [],
        "requested_actions": [],
        "search_results": search_results or [],
    }


def build_external_lead_extraction_grading_input(
    *,
    request_id: str,
    source_url: str,
    source_content: str,
    source_candidate_id: str | None = None,
    candidate_url_id: str | None = None,
    risk_flags: list[str] | None = None,
    existing_grade: str | None = None,
    expected_contacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "combined_run_id": request_id,
        "extraction_run_id": request_id,
        "grading_run_id": request_id,
        "trigger_source": "scheduler_external_lead_extraction_grading",
        "source_candidate_id": source_candidate_id,
        "candidate_url_id": candidate_url_id,
        "source_url": source_url,
        "source_content": source_content,
        "risk_flags": risk_flags or [],
        "existing_grade": existing_grade,
        "expected_contacts": expected_contacts or {},
    }


def build_external_lead_extraction_grading_batch_input(
    *,
    request_id: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    first = sources[0] if sources else {}
    return {
        "combined_run_id": request_id,
        "extraction_run_id": request_id,
        "grading_run_id": request_id,
        "trigger_source": "scheduler_external_lead_extraction_grading",
        "source_candidate_id": first.get("source_candidate_id"),
        "candidate_url_id": first.get("candidate_url_id"),
        "source_url": first.get("source_url") or "",
        "source_content": first.get("source_content") or "",
        "risk_flags": first.get("risk_flags") or [],
        "existing_grade": first.get("existing_grade"),
        "expected_contacts": first.get("expected_contacts") or {},
        "sources": sources,
    }


def build_external_deep_enrichment_batch_input(
    *,
    request_id: str,
    leads: list[dict[str, Any]],
) -> dict[str, Any]:
    first = leads[0] if leads else {}
    return {
        "agent_run_id": request_id,
        "trigger_source": "scheduler_external_deep_enrichment",
        "staging_lead_id": first.get("staging_lead_id"),
        "lead_snapshot": first.get("lead_snapshot") or {},
        "missing_fields": first.get("missing_fields") or [],
        "requested_actions": [],
        "leads": leads,
    }


def build_external_lead_cleanup_input(
    *,
    request_id: str,
    leads: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "cleanup_run_id": request_id,
        "trigger_source": "scheduler_external_lead_cleanup",
        "leads": leads,
        "requested_actions": [],
    }
