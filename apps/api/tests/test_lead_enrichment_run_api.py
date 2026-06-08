from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.candidate_url import CandidateUrl
from app.models.enums import ChannelRiskLevel, CustomerGrade, LeadEnrichmentResultStatus, LeadEnrichmentType
from app.models.staging_lead import StagingLead
from app.schemas.lead_enrichment import LeadEnrichmentRunCreate
from app.services.lead_enrichment import LeadEnrichmentQuota, LeadEnrichmentService


API_ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def build_lead(*, grade: CustomerGrade = CustomerGrade.B, risk_level: ChannelRiskLevel = ChannelRiskLevel.LOW) -> StagingLead:
    lead = StagingLead(
        id=uuid4(),
        candidate_url_id=uuid4(),
        customer_name="Ru Auto City",
        country="Russia",
        city="Moscow",
        contacts_json=[{"type": "email", "value": "sales@example.com"}],
        source_evidence="公开官网包含车辆销售和联系方式。",
        recommended_grade=grade,
        review_status="pending_review",
        queue_status="pending_review",
        missing_fields=["purchase_frequency"],
        requires_compliance_review=False,
    )
    lead.candidate_url = CandidateUrl(
        id=lead.candidate_url_id,
        task_id=uuid4(),
        url="https://example.com/dealer",
        url_hash="hash",
        source_platform="official_website",
        source_risk_level=risk_level,
        source_usage_type="automatic_collection",
        discovery_reason="公开官网。",
        queue_eligible=True,
        requires_secondary_verification=False,
        status="new",
    )
    return lead


def test_lead_enrichment_run_create_requires_manual_actor() -> None:
    try:
        LeadEnrichmentRunCreate(triggered_by="", manual_keywords=["toyota"])
    except ValidationError as exc:
        assert "triggered_by" in str(exc)
    else:
        raise AssertionError("manual trigger actor is required")


def test_validate_trigger_blocks_watch_invalid_forbidden_and_dnc() -> None:
    quota = LeadEnrichmentQuota(daily_limit=2, used_today=0)

    for grade in (CustomerGrade.WATCH, CustomerGrade.INVALID):
        try:
            LeadEnrichmentService.validate_trigger_allowed(
                build_lead(grade=grade),
                quota=quota,
                has_do_not_contact_match=False,
            )
        except ValueError as exc:
            assert "不得深挖" in str(exc)
        else:
            raise AssertionError(f"{grade} should be blocked")

    try:
        LeadEnrichmentService.validate_trigger_allowed(
            build_lead(risk_level=ChannelRiskLevel.FORBIDDEN),
            quota=quota,
            has_do_not_contact_match=False,
        )
    except ValueError as exc:
        assert "Forbidden" in str(exc)
    else:
        raise AssertionError("Forbidden source should be blocked")

    try:
        LeadEnrichmentService.validate_trigger_allowed(
            build_lead(),
            quota=quota,
            has_do_not_contact_match=True,
        )
    except ValueError as exc:
        assert "勿扰" in str(exc)
    else:
        raise AssertionError("DNC matched lead should be blocked")


def test_validate_trigger_blocks_daily_quota() -> None:
    try:
        LeadEnrichmentService.validate_trigger_allowed(
            build_lead(),
            quota=LeadEnrichmentQuota(daily_limit=2, used_today=2),
            has_do_not_contact_match=False,
        )
    except ValueError as exc:
        assert "每日深挖配额" in str(exc)
    else:
        raise AssertionError("quota exhausted lead should be blocked")


def test_build_pending_enrichment_run_payload_keeps_staging_layer_and_audit() -> None:
    lead = build_lead()
    request = LeadEnrichmentRunCreate(
        triggered_by="ops-a",
        manual_keywords=["автосалон", "Toyota"],
        allowed_channel_scope=["official_website", "public_directory"],
        note="人工触发深挖。",
    )
    payload = LeadEnrichmentService.build_pending_run_payload(lead, request=request, now=datetime(2026, 6, 4, tzinfo=UTC))

    assert payload["staging_lead_id"] == lead.id
    assert payload["enrichment_type"] == LeadEnrichmentType.AI_DEEP_RESEARCH
    assert payload["triggered_by"] == "ops-a"
    assert payload["status"] == LeadEnrichmentResultStatus.PENDING
    assert payload["agent_task_run_id"] is None
    assert payload["input_snapshot_json"]["manual_keywords"] == ["автосалон", "Toyota"]
    assert payload["input_snapshot_json"]["customer_name"] == "Ru Auto City"
    assert payload["output_json"] is None
    assert payload["recommended_action"] == "run_deep_enrichment_agent"
    assert "customer_id" not in payload


def test_lead_enrichment_api_route_is_registered_without_bulk_auto_trigger() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/staging-leads/{lead_id}/enrichment-runs" in paths
    assert "post" in paths["/staging-leads/{lead_id}/enrichment-runs"]
    assert all("bulk-enrichment" not in path for path in paths)

    api_text = (API_ROOT / "app" / "api" / "lead_enrichment.py").read_text(encoding="utf-8")
    assert '@router.post("/{lead_id:uuid}/enrichment-runs"' in api_text
    assert "@router.delete" not in api_text
    assert "auto_send" not in api_text
