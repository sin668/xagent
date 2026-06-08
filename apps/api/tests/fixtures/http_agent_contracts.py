from copy import deepcopy


REQUEST_ID = "11111111-1111-1111-1111-111111111111"
AGENT_TASK_RUN_ID = "22222222-2222-2222-2222-222222222222"
AGENT_SERVICE_RUN_ID = "44444444-4444-4444-4444-444444444444"


SUCCESS_RESPONSE = {
    "schema_version": "phase4.agent.run.v1",
    "agent_service_run_id": AGENT_SERVICE_RUN_ID,
    "request_id": REQUEST_ID,
    "status": "succeeded",
    "agent_type": "deep_enrichment",
    "agent_mode": "active",
    "output": {
        "schema_version": "phase3.agent.deep_enrichment.v1",
        "field_candidates": [],
        "missing_fields": [],
        "recommended_next_action": "manual_review",
        "audit": {"writes_core_tables": False},
    },
    "audit": {
        "writes_core_tables": False,
        "executed_nodes": ["load_lead", "validate_evidence"],
        "failed_node": None,
        "risk_flags": [],
        "source_urls": [],
    },
    "error": None,
}


def success_response(**overrides):
    payload = deepcopy(SUCCESS_RESPONSE)
    payload.update(overrides)
    return payload
