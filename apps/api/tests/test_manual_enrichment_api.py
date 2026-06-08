from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.candidate_url import CandidateUrl
from app.models.enums import (
    ChannelRiskLevel,
    CustomerGrade,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
)
from app.models.staging_lead import StagingLead
from app.schemas.lead_enrichment import ManualEnrichmentCreate
from app.services.lead_enrichment import LeadEnrichmentService


API_ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def build_lead(*, risk_level: ChannelRiskLevel = ChannelRiskLevel.LOW) -> StagingLead:
    lead = StagingLead(
        id=uuid4(),
        candidate_url_id=uuid4(),
        customer_name="Ru Auto City",
        country="Russia",
        city="Moscow",
        contacts_json=[],
        source_evidence="公开来源展示车商名称。",
        recommended_grade=CustomerGrade.B,
        review_status="pending_review",
        queue_status="pending_review",
        missing_fields=["contacts_json", "vehicle_intents"],
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


def manual_request(**overrides: object) -> ManualEnrichmentCreate:
    payload = {
        "operator": "ops-a",
        "note": "人工从公开联系页补录。",
        "fields": [
            {
                "field_name": "contacts_json",
                "candidate_value": [{"type": "email", "value": "sales@example.com"}],
                "source_type": LeadEnrichmentFieldSourceType.MANUAL_PUBLIC_INFO,
                "source_url": "https://example.com/contact",
                "evidence_note": "公开联系页展示 sales@example.com。",
                "confidence_score": 0.9,
            },
            {
                "field_name": "vehicle_intents",
                "candidate_value": [{"brand": "Toyota", "model": "Camry"}],
                "source_type": LeadEnrichmentFieldSourceType.MANUAL_BUSINESS_NOTE,
                "source_url": None,
                "evidence_note": "销售线下沟通记录，客户关注 Toyota Camry。",
                "confidence_score": 0.7,
            },
        ],
    }
    payload.update(overrides)
    return ManualEnrichmentCreate(**payload)


def test_manual_enrichment_schema_requires_operator_and_fields() -> None:
    try:
        ManualEnrichmentCreate(operator="", fields=[])
    except ValidationError as exc:
        assert "operator" in str(exc)
        assert "fields" in str(exc)
    else:
        raise AssertionError("manual enrichment should require operator and at least one field")


def test_manual_enrichment_route_is_registered_without_auto_promotion_or_outreach() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/staging-leads/{lead_id}/manual-enrichment" in paths
    assert "post" in paths["/staging-leads/{lead_id}/manual-enrichment"]

    api_text = (API_ROOT / "app" / "api" / "lead_enrichment.py").read_text(encoding="utf-8")
    assert "manual-enrichment" in api_text
    assert "promote" not in api_text.lower()
    assert "auto_send" not in api_text
    assert "outreach" not in api_text.lower()


def test_build_manual_enrichment_result_records_operator_time_note_and_staging_only() -> None:
    lead = build_lead()
    request = manual_request()

    result, candidates = LeadEnrichmentService.build_manual_enrichment_payloads(
        lead,
        request=request,
        now=datetime(2026, 6, 4, 13, tzinfo=UTC),
    )

    assert result["staging_lead_id"] == lead.id
    assert result["enrichment_type"] == LeadEnrichmentType.MANUAL_SUPPLEMENT
    assert result["triggered_by"] == "ops-a"
    assert result["status"] == LeadEnrichmentResultStatus.SUCCEEDED
    assert result["input_snapshot_json"]["operator"] == "ops-a"
    assert result["input_snapshot_json"]["note"] == "人工从公开联系页补录。"
    assert result["output_json"]["manual_field_count"] == 2
    assert result["recommended_action"] == "manual_review"
    assert result["agent_task_run_id"] is None
    assert result["created_at"] == datetime(2026, 6, 4, 13, tzinfo=UTC)
    assert "customer_id" not in result

    assert len(candidates) == 2
    assert candidates[0]["field_name"] == "contacts_json"
    assert candidates[0]["source_type"] == LeadEnrichmentFieldSourceType.MANUAL_PUBLIC_INFO
    assert candidates[0]["review_status"] == LeadEnrichmentFieldReviewStatus.NEEDS_REVIEW
    assert candidates[0]["evidence_note"] == "公开联系页展示 sales@example.com。"
    assert candidates[1]["field_name"] == "vehicle_intents"
    assert candidates[1]["source_type"] == LeadEnrichmentFieldSourceType.MANUAL_BUSINESS_NOTE


def test_unknown_source_type_cannot_create_critical_promotion_candidate() -> None:
    lead = build_lead()
    request = manual_request(
        fields=[
            {
                "field_name": "contacts_json",
                "candidate_value": [{"type": "email", "value": "unknown@example.com"}],
                "source_type": LeadEnrichmentFieldSourceType.UNKNOWN,
                "source_url": None,
                "evidence_note": "来源无法确认。",
            }
        ]
    )

    try:
        LeadEnrichmentService.build_manual_enrichment_payloads(
            lead,
            request=request,
            now=datetime(2026, 6, 4, 13, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "unknown" in str(exc)
        assert "晋级关键证据" in str(exc)
    else:
        raise AssertionError("unknown source cannot create critical promotion candidate")


def test_manual_enrichment_blocks_forbidden_source_lead() -> None:
    lead = build_lead(risk_level=ChannelRiskLevel.FORBIDDEN)
    request = manual_request()

    try:
        LeadEnrichmentService.validate_manual_enrichment_allowed(lead, request=request)
    except ValueError as exc:
        assert "Forbidden" in str(exc)
    else:
        raise AssertionError("manual enrichment should not bypass Forbidden guard")
