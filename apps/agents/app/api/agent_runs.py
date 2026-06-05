from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.graphs.deep_enrichment import DeepEnrichmentGraphRunner, DeepEnrichmentGraphState
from app.graphs.lead_cleanup import LeadCleanupGraphRunner, LeadCleanupGraphState
from app.graphs.lead_extraction_grading import LeadExtractionGradingGraphRunner, LeadExtractionGradingGraphState
from app.graphs.source_discovery import SourceDiscoveryGraphRunner, SourceDiscoveryGraphState
from app.schemas.agent_run import AgentRunAudit, AgentRunError, AgentRunRequest, AgentRunResponse
from app.security import require_internal_api_key
from app.services.agent_logging import log_agent_run_failed, log_agent_run_start, log_agent_run_succeeded
from app.services.agent_service_runs import AgentServiceRunService


router = APIRouter(
    prefix="/agent-runs",
    dependencies=[Depends(require_internal_api_key)],
)


@router.post("/deep-enrichment", response_model=AgentRunResponse)
def run_deep_enrichment(
    request: AgentRunRequest,
    session: Session = Depends(get_db_session),
) -> AgentRunResponse:
    service = AgentServiceRunService(session)
    input_payload = dict(request.input)
    run = service.create_run(
        request_id=request.request_id,
        agent_type="deep_enrichment",
        agent_mode=request.agent_mode,
        trigger_source=request.trigger_source,
        input_json=input_payload,
        max_retries=request.options.max_retries,
    )
    service.mark_running(run.id)
    log_agent_run_start(
        agent_type="deep_enrichment",
        request_id=str(request.request_id),
        agent_mode=request.agent_mode,
        trigger_source=request.trigger_source,
        agent_service_run_id=str(run.id),
    )

    try:
        graph_result = DeepEnrichmentGraphRunner().run(
            DeepEnrichmentGraphState(
                agent_run_id=input_payload.get("agent_run_id") or request.request_id,
                staging_lead_id=input_payload["staging_lead_id"],
                lead_snapshot=input_payload.get("lead_snapshot") or {},
                missing_fields=list(input_payload.get("missing_fields") or []),
                requested_actions=list(input_payload.get("requested_actions") or []),
            )
        )
    except Exception as exc:
        error_type = _classify_deep_enrichment_error(exc)
        failed = service.mark_failed(run.id, error_type=error_type, error_message=str(exc))
        log_agent_run_failed(
            agent_type="deep_enrichment",
            request_id=str(request.request_id),
            agent_mode=failed.agent_mode,
            agent_service_run_id=str(failed.id),
            error_type=error_type,
            error_message=str(exc),
        )
        return AgentRunResponse(
            agent_service_run_id=failed.id,
            request_id=failed.request_id,
            status="failed",
            agent_type="deep_enrichment",
            agent_mode=failed.agent_mode,
            output=None,
            audit=AgentRunAudit(writes_core_tables=False, executed_nodes=[]),
            error=AgentRunError(error_type=error_type, message=str(exc), retryable=False),
        )

    output = graph_result.output.model_dump(mode="json")
    audit = _response_audit(output.get("audit") or {}, executed_nodes=graph_result.executed_nodes)
    succeeded = service.mark_succeeded(
        run.id,
        output_json=output,
        output_summary_json=_deep_enrichment_output_summary(output, audit),
    )
    succeeded.audit_json = audit
    session.add(succeeded)
    session.commit()
    session.refresh(succeeded)
    log_agent_run_succeeded(
        agent_type="deep_enrichment",
        request_id=str(succeeded.request_id),
        agent_mode=succeeded.agent_mode,
        agent_service_run_id=str(succeeded.id),
        executed_node_count=len(graph_result.executed_nodes),
    )

    return AgentRunResponse(
        agent_service_run_id=succeeded.id,
        request_id=succeeded.request_id,
        status="succeeded",
        agent_type="deep_enrichment",
        agent_mode=succeeded.agent_mode,
        output=output,
        audit=AgentRunAudit(**audit),
        error=None,
    )


@router.post("/lead-cleanup", response_model=AgentRunResponse)
def run_lead_cleanup(
    request: AgentRunRequest,
    session: Session = Depends(get_db_session),
) -> AgentRunResponse:
    service = AgentServiceRunService(session)
    input_payload = dict(request.input)
    run = service.create_run(
        request_id=request.request_id,
        agent_type="lead_cleanup",
        agent_mode=request.agent_mode,
        trigger_source=request.trigger_source,
        input_json=input_payload,
        max_retries=request.options.max_retries,
    )
    service.mark_running(run.id)
    log_agent_run_start(
        agent_type="lead_cleanup",
        request_id=str(request.request_id),
        agent_mode=request.agent_mode,
        trigger_source=request.trigger_source,
        agent_service_run_id=str(run.id),
    )

    try:
        graph_result = LeadCleanupGraphRunner().run(
            LeadCleanupGraphState(
                cleanup_run_id=input_payload.get("cleanup_run_id") or request.request_id,
                leads=list(input_payload.get("leads") or []),
                requested_actions=list(input_payload.get("requested_actions") or []),
            )
        )
    except Exception as exc:
        error_type = _classify_lead_cleanup_error(exc)
        failed = service.mark_failed(run.id, error_type=error_type, error_message=str(exc))
        log_agent_run_failed(
            agent_type="lead_cleanup",
            request_id=str(request.request_id),
            agent_mode=failed.agent_mode,
            agent_service_run_id=str(failed.id),
            error_type=error_type,
            error_message=str(exc),
        )
        return _failed_response(
            failed,
            agent_type="lead_cleanup",
            error_type=error_type,
            error_message=str(exc),
        )

    output = graph_result.output.model_dump(mode="json")
    audit = _response_audit(output.get("audit") or {}, executed_nodes=graph_result.executed_nodes)
    succeeded = service.mark_succeeded(
        run.id,
        output_json=output,
        output_summary_json=_lead_cleanup_output_summary(output, audit),
    )
    succeeded.audit_json = audit
    session.add(succeeded)
    session.commit()
    session.refresh(succeeded)
    log_agent_run_succeeded(
        agent_type="lead_cleanup",
        request_id=str(succeeded.request_id),
        agent_mode=succeeded.agent_mode,
        agent_service_run_id=str(succeeded.id),
        executed_node_count=len(graph_result.executed_nodes),
    )

    return AgentRunResponse(
        agent_service_run_id=succeeded.id,
        request_id=succeeded.request_id,
        status="succeeded",
        agent_type="lead_cleanup",
        agent_mode=succeeded.agent_mode,
        output=output,
        audit=AgentRunAudit(**audit),
        error=None,
    )


@router.post("/source-discovery", response_model=AgentRunResponse)
def run_source_discovery(
    request: AgentRunRequest,
    session: Session = Depends(get_db_session),
) -> AgentRunResponse:
    service = AgentServiceRunService(session)
    input_payload = dict(request.input)
    run = service.create_run(
        request_id=request.request_id,
        agent_type="source_discovery",
        agent_mode=request.agent_mode,
        trigger_source=request.trigger_source,
        input_json=input_payload,
        max_retries=request.options.max_retries,
    )
    service.mark_running(run.id)
    log_agent_run_start(
        agent_type="source_discovery",
        request_id=str(request.request_id),
        agent_mode=request.agent_mode,
        trigger_source=request.trigger_source,
        agent_service_run_id=str(run.id),
    )

    try:
        graph_result = SourceDiscoveryGraphRunner().run(
            SourceDiscoveryGraphState(
                discovery_run_id=input_payload.get("discovery_run_id") or request.request_id,
                market=str(input_payload.get("market") or "Unknown"),
                channel_strategy=dict(input_payload.get("channel_strategy") or {}),
                agent_mode=request.agent_mode,
                seed_urls=list(input_payload.get("seed_urls") or []),
                requested_actions=list(input_payload.get("requested_actions") or []),
                search_results=list(input_payload.get("search_results") or []),
            )
        )
    except Exception as exc:
        error_type = _classify_source_discovery_error(exc)
        failed = service.mark_failed(run.id, error_type=error_type, error_message=str(exc))
        log_agent_run_failed(
            agent_type="source_discovery",
            request_id=str(request.request_id),
            agent_mode=failed.agent_mode,
            agent_service_run_id=str(failed.id),
            error_type=error_type,
            error_message=str(exc),
        )
        return _failed_response(
            failed,
            agent_type="source_discovery",
            error_type=error_type,
            error_message=str(exc),
        )

    output = graph_result.output.model_dump(mode="json")
    audit = _response_audit(output.get("audit") or {}, executed_nodes=graph_result.executed_nodes)
    persisted_audit = _source_discovery_persisted_audit(output.get("audit") or {}, executed_nodes=graph_result.executed_nodes)
    succeeded = service.mark_succeeded(
        run.id,
        output_json=output,
        output_summary_json=_source_discovery_output_summary(output, audit),
    )
    succeeded.audit_json = persisted_audit
    session.add(succeeded)
    session.commit()
    session.refresh(succeeded)
    log_agent_run_succeeded(
        agent_type="source_discovery",
        request_id=str(succeeded.request_id),
        agent_mode=succeeded.agent_mode,
        agent_service_run_id=str(succeeded.id),
        executed_node_count=len(graph_result.executed_nodes),
    )

    return AgentRunResponse(
        agent_service_run_id=succeeded.id,
        request_id=succeeded.request_id,
        status="succeeded",
        agent_type="source_discovery",
        agent_mode=succeeded.agent_mode,
        output=output,
        audit=AgentRunAudit(**audit),
        error=None,
    )


@router.post("/lead-extraction-grading", response_model=AgentRunResponse)
def run_lead_extraction_grading(
    request: AgentRunRequest,
    session: Session = Depends(get_db_session),
) -> AgentRunResponse:
    service = AgentServiceRunService(session)
    input_payload = dict(request.input)
    run = service.create_run(
        request_id=request.request_id,
        agent_type="lead_extraction_grading",
        agent_mode=request.agent_mode,
        trigger_source=request.trigger_source,
        input_json=input_payload,
        max_retries=request.options.max_retries,
    )
    service.mark_running(run.id)
    log_agent_run_start(
        agent_type="lead_extraction_grading",
        request_id=str(request.request_id),
        agent_mode=request.agent_mode,
        trigger_source=request.trigger_source,
        agent_service_run_id=str(run.id),
    )

    try:
        graph_result = LeadExtractionGradingGraphRunner().run(
            LeadExtractionGradingGraphState(
                combined_run_id=input_payload.get("combined_run_id") or request.request_id,
                extraction_run_id=input_payload.get("extraction_run_id") or request.request_id,
                grading_run_id=input_payload.get("grading_run_id") or request.request_id,
                source_url=str(input_payload.get("source_url") or ""),
                source_content=str(input_payload.get("source_content") or ""),
                agent_mode=request.agent_mode,
                risk_flags=list(input_payload.get("risk_flags") or []),
                existing_grade=input_payload.get("existing_grade"),
                expected_contacts=dict(input_payload.get("expected_contacts") or {}),
            )
        )
    except Exception as exc:
        error_type = _classify_lead_extraction_grading_error(exc)
        failed = service.mark_failed(run.id, error_type=error_type, error_message=str(exc))
        log_agent_run_failed(
            agent_type="lead_extraction_grading",
            request_id=str(request.request_id),
            agent_mode=failed.agent_mode,
            agent_service_run_id=str(failed.id),
            error_type=error_type,
            error_message=str(exc),
        )
        return _failed_response(
            failed,
            agent_type="lead_extraction_grading",
            error_type=error_type,
            error_message=str(exc),
        )

    output = graph_result.output.model_dump(mode="json")
    audit = _response_audit(output.get("audit") or {}, executed_nodes=graph_result.executed_nodes)
    succeeded = service.mark_succeeded(
        run.id,
        output_json=output,
        output_summary_json=_lead_extraction_grading_output_summary(output, audit),
    )
    succeeded.audit_json = {**audit, "validation_summary": (output.get("audit") or {}).get("validation_summary")}
    session.add(succeeded)
    session.commit()
    session.refresh(succeeded)
    log_agent_run_succeeded(
        agent_type="lead_extraction_grading",
        request_id=str(succeeded.request_id),
        agent_mode=succeeded.agent_mode,
        agent_service_run_id=str(succeeded.id),
        executed_node_count=len(graph_result.executed_nodes),
    )

    return AgentRunResponse(
        agent_service_run_id=succeeded.id,
        request_id=succeeded.request_id,
        status="succeeded",
        agent_type="lead_extraction_grading",
        agent_mode=succeeded.agent_mode,
        output=output,
        audit=AgentRunAudit(**audit),
        error=None,
    )


def _classify_deep_enrichment_error(exc: Exception) -> str:
    message = str(exc)
    if "不允许自动私信" in message or "反爬规避" in message:
        return "risk_blocked"
    return "schema_validation_error"


def _classify_lead_cleanup_error(exc: Exception) -> str:
    message = str(exc)
    if "不允许自动执行" in message or "删除线索" in message or "自动恢复 Invalid" in message:
        return "risk_blocked"
    return "schema_validation_error"


def _classify_source_discovery_error(exc: Exception) -> str:
    message = str(exc)
    if "只允许 shadow_run" in message or "登录采集" in message or "私有数据采集" in message or "lead_source_candidates" in message:
        return "risk_blocked"
    return "schema_validation_error"


def _classify_lead_extraction_grading_error(exc: Exception) -> str:
    message = str(exc)
    if "只允许 shadow_run" in message or "Forbidden" in message or "勿扰" in message:
        return "risk_blocked"
    if "证据" in message or "联系方式" in message:
        return "evidence_validation_error"
    return "schema_validation_error"


def _failed_response(
    run,
    *,
    agent_type: str,
    error_type: str,
    error_message: str,
) -> AgentRunResponse:
    return AgentRunResponse(
        agent_service_run_id=run.id,
        request_id=run.request_id,
        status="failed",
        agent_type=agent_type,
        agent_mode=run.agent_mode,
        output=None,
        audit=AgentRunAudit(writes_core_tables=False, executed_nodes=[]),
        error=AgentRunError(error_type=error_type, message=error_message, retryable=False),
    )


def _response_audit(graph_audit: dict[str, Any], *, executed_nodes: list[str]) -> dict[str, Any]:
    return {
        "writes_core_tables": False,
        "executed_nodes": executed_nodes,
        "failed_node": graph_audit.get("failed_node"),
        "risk_flags": list(graph_audit.get("risk_flags") or []),
        "source_urls": list(graph_audit.get("source_urls") or []),
    }


def _source_discovery_persisted_audit(graph_audit: dict[str, Any], *, executed_nodes: list[str]) -> dict[str, Any]:
    node_summaries = graph_audit.get("node_summaries") if isinstance(graph_audit.get("node_summaries"), dict) else {}
    return {
        "writes_core_tables": False,
        "executed_nodes": [
            {
                "node": node_name,
                "status": "succeeded",
                "summary": dict(node_summaries.get(node_name) or {}),
            }
            for node_name in executed_nodes
        ],
        "failed_node": graph_audit.get("failed_node"),
        "risk_flags": list(graph_audit.get("risk_flags") or []),
        "source_urls": list(graph_audit.get("source_urls") or []),
    }


def _deep_enrichment_output_summary(output: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "field_candidate_count": len(output.get("field_candidates") or []),
        "risk_flags": list(audit.get("risk_flags") or []),
    }


def _lead_cleanup_output_summary(output: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "suggestion_count": len(output.get("suggestions") or []),
        "blocked_item_count": len(output.get("blocked_items") or []),
        "risk_flags": list(audit.get("risk_flags") or []),
    }


def _source_discovery_output_summary(output: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_count": len(output.get("candidates") or []),
        "blocked_item_count": len(output.get("blocked_items") or []),
        "risk_flags": list(audit.get("risk_flags") or []),
    }


def _lead_extraction_grading_output_summary(output: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    extraction = output.get("extraction") or {}
    grading = output.get("grading") or {}
    hard_rule_summary = output.get("hard_rule_summary") or {}
    return {
        "extracted_candidate_count": len(extraction.get("candidates") or []),
        "grading_suggestion_count": len(grading.get("suggestions") or []),
        "hard_rules_applied": bool(hard_rule_summary.get("hard_rules_applied")),
        "risk_flags": list(audit.get("risk_flags") or []),
    }
