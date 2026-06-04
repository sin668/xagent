from pathlib import Path

from app.models.enums import RiskEventSeverity, RiskEventStatus
from app.services.audit_risk import AuditRiskLogService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0013_audit_risk_logs.py"


def test_audit_risk_migration_declares_required_tables_and_ai_audit_extensions() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0013"' in migration
    assert 'down_revision = "20260529_0012"' in migration
    assert 'op.add_column("ai_audit_logs"' in migration
    assert "source_urls" in migration
    assert "output_json" in migration
    for table in ["agent_run_logs", "review_logs", "risk_events"]:
        assert f'"{table}"' in migration
    for field in ["task_id", "agent_name", "action", "input_ref", "output_ref", "result", "error_message"]:
        assert field in migration
    for field in ["channel", "risk_level", "event_type", "severity", "resolution_status", "block_reason"]:
        assert field in migration


def test_audit_risk_models_are_registered_for_alembic_metadata() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")

    assert "AgentRunLog" in models_init
    assert "ReviewLog" in models_init
    assert "RiskEvent" in models_init
    assert "RiskEventSeverity" in models_init
    assert "RiskEventStatus" in models_init


def test_ai_audit_payload_keeps_llm_required_fields() -> None:
    payload = AuditRiskLogService.build_ai_audit_payload(
        prompt_version="lead-extraction-v1",
        model_name="test-model",
        output_json={"recommended_grade": "B"},
        source_urls=["https://example.com/dealer"],
    )

    assert payload["prompt_version"] == "lead-extraction-v1"
    assert payload["model_name"] == "test-model"
    assert payload["output_json"] == {"recommended_grade": "B"}
    assert payload["source_urls"] == ["https://example.com/dealer"]


def test_risk_event_defaults_and_block_reason_are_preserved() -> None:
    event = AuditRiskLogService.build_risk_event_payload(
        channel="VK",
        risk_level="High",
        event_type="rule_block",
        block_reason="High 风险渠道不得进入触达队列",
    )

    assert event["channel"] == "VK"
    assert event["risk_level"] == "High"
    assert event["event_type"] == "rule_block"
    assert event["severity"] == RiskEventSeverity.HIGH
    assert event["resolution_status"] == RiskEventStatus.OPEN
    assert "不得进入触达队列" in event["block_reason"]


def test_private_payload_keys_are_removed_from_audit_logs() -> None:
    sanitized = AuditRiskLogService.sanitize_audit_payload(
        {
            "customer_name": "Dealer",
            "private_chat": "unrelated personal note",
            "password": "secret",
            "token": "abc",
            "source_url": "https://example.com",
        }
    )

    assert sanitized == {"customer_name": "Dealer", "source_url": "https://example.com"}
