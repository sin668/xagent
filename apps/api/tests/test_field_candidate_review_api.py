from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import (
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
)
from app.models.lead_enrichment_field_candidate import LeadEnrichmentFieldCandidate
from app.models.lead_enrichment_result import LeadEnrichmentResult
from app.schemas.lead_enrichment_field_candidate import (
    LeadEnrichmentFieldCandidateAccept,
    LeadEnrichmentFieldCandidateReject,
    LeadEnrichmentFieldCandidateUpdate,
)
from app.services.lead_enrichment import LeadEnrichmentService


API_ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def build_result() -> LeadEnrichmentResult:
    return LeadEnrichmentResult(
        id=uuid4(),
        staging_lead_id=uuid4(),
        enrichment_type=LeadEnrichmentType.AI_DEEP_RESEARCH,
        triggered_by="ops-a",
        status=LeadEnrichmentResultStatus.SUCCEEDED,
        input_snapshot_json={"customer_name": "Unknown"},
        output_json={"customer_name": "Ru Auto City"},
        evidence_links=["https://example.com/dealer"],
        confidence_score=0.82,
        missing_fields=[],
        recommended_action="manual_review",
        created_at=datetime(2026, 6, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 6, 4, 10, tzinfo=UTC),
    )


def build_candidate(
    *,
    field_name: str = "customer_name",
    source_url: str | None = "https://example.com/dealer",
    evidence_note: str = "公开官网页脚展示经销商名称。",
    review_status: LeadEnrichmentFieldReviewStatus = LeadEnrichmentFieldReviewStatus.PENDING,
) -> LeadEnrichmentFieldCandidate:
    result = build_result()
    return LeadEnrichmentFieldCandidate(
        id=uuid4(),
        enrichment_result_id=result.id,
        staging_lead_id=result.staging_lead_id,
        field_name=field_name,
        candidate_value="Ru Auto City",
        source_type=LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE,
        source_url=source_url,
        evidence_note=evidence_note,
        confidence_score=0.78,
        review_status=review_status,
        created_at=datetime(2026, 6, 4, 10, 1, tzinfo=UTC),
        updated_at=datetime(2026, 6, 4, 10, 1, tzinfo=UTC),
    )


def test_field_candidate_review_routes_are_registered_without_auto_promotion_or_outreach() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/lead-enrichment-field-candidates/{candidate_id}/accept" in paths
    assert "patch" in paths["/lead-enrichment-field-candidates/{candidate_id}/accept"]
    assert "/lead-enrichment-field-candidates/{candidate_id}/reject" in paths
    assert "patch" in paths["/lead-enrichment-field-candidates/{candidate_id}/reject"]
    assert "/lead-enrichment-field-candidates/{candidate_id}" in paths
    assert "patch" in paths["/lead-enrichment-field-candidates/{candidate_id}"]

    api_text = (API_ROOT / "app" / "api" / "lead_enrichment.py").read_text(encoding="utf-8")
    assert "promote" not in api_text.lower()
    assert "auto_send" not in api_text
    assert "outreach" not in api_text.lower()


def test_accept_field_candidate_records_actor_time_and_keeps_staging_layer() -> None:
    candidate = build_candidate()
    request = LeadEnrichmentFieldCandidateAccept(accepted_by="reviewer-a")

    accepted = LeadEnrichmentService.accept_field_candidate(candidate, request=request, now=datetime(2026, 6, 4, 11, tzinfo=UTC))

    assert accepted.review_status == LeadEnrichmentFieldReviewStatus.ACCEPTED
    assert accepted.accepted_by == "reviewer-a"
    assert accepted.accepted_at == datetime(2026, 6, 4, 11, tzinfo=UTC)
    assert accepted.rejected_reason is None
    assert accepted.updated_at == datetime(2026, 6, 4, 11, tzinfo=UTC)
    assert not hasattr(accepted, "customer_id")


def test_accept_field_candidate_can_update_value_before_accepting() -> None:
    candidate = build_candidate(field_name="contacts_json")
    request = LeadEnrichmentFieldCandidateAccept(
        accepted_by="reviewer-a",
        candidate_value=[{"type": "email", "value": "sales@example.com"}],
        source_type=LeadEnrichmentFieldSourceType.MANUAL_PUBLIC_INFO,
        source_url="https://example.com/contact",
        evidence_note="公开联系页展示 sales@example.com。",
        confidence_score=0.91,
    )

    accepted = LeadEnrichmentService.accept_field_candidate(candidate, request=request, now=datetime(2026, 6, 4, 11, tzinfo=UTC))

    assert accepted.candidate_value == [{"type": "email", "value": "sales@example.com"}]
    assert accepted.source_type == LeadEnrichmentFieldSourceType.MANUAL_PUBLIC_INFO
    assert accepted.source_url == "https://example.com/contact"
    assert accepted.evidence_note == "公开联系页展示 sales@example.com。"
    assert accepted.confidence_score == 0.91
    assert accepted.review_status == LeadEnrichmentFieldReviewStatus.ACCEPTED


def test_reject_field_candidate_records_reason_without_acceptance_audit() -> None:
    candidate = build_candidate()
    request = LeadEnrichmentFieldCandidateReject(rejected_reason="来源页面未能证明该名称属于车商。")

    rejected = LeadEnrichmentService.reject_field_candidate(candidate, request=request, now=datetime(2026, 6, 4, 11, tzinfo=UTC))

    assert rejected.review_status == LeadEnrichmentFieldReviewStatus.REJECTED
    assert rejected.rejected_reason == "来源页面未能证明该名称属于车商。"
    assert rejected.accepted_by is None
    assert rejected.accepted_at is None
    assert rejected.updated_at == datetime(2026, 6, 4, 11, tzinfo=UTC)


def test_update_field_candidate_marks_manual_needs_review_without_accepting() -> None:
    candidate = build_candidate(field_name="city")
    request = LeadEnrichmentFieldCandidateUpdate(
        candidate_value="Moscow",
        evidence_note="人工复核公开页面地址后修正城市。",
        review_status=LeadEnrichmentFieldReviewStatus.NEEDS_REVIEW,
    )

    updated = LeadEnrichmentService.update_field_candidate(candidate, request=request, now=datetime(2026, 6, 4, 11, tzinfo=UTC))

    assert updated.candidate_value == "Moscow"
    assert updated.evidence_note == "人工复核公开页面地址后修正城市。"
    assert updated.review_status == LeadEnrichmentFieldReviewStatus.NEEDS_REVIEW
    assert updated.accepted_by is None
    assert updated.accepted_at is None


def test_update_field_candidate_cannot_bypass_acceptance_endpoint() -> None:
    candidate = build_candidate(field_name="contacts_json", source_url=None, evidence_note="   ")
    request = LeadEnrichmentFieldCandidateUpdate(
        review_status=LeadEnrichmentFieldReviewStatus.ACCEPTED,
        accepted_by="reviewer-a",
    )

    try:
        LeadEnrichmentService.update_field_candidate(candidate, request=request, now=datetime(2026, 6, 4, 11, tzinfo=UTC))
    except ValueError as exc:
        assert "采纳" in str(exc)
        assert "/accept" in str(exc)
    else:
        raise AssertionError("generic update should not bypass acceptance endpoint")


def test_critical_field_without_evidence_cannot_be_accepted() -> None:
    candidate = build_candidate(field_name="contacts_json", source_url=None, evidence_note="   ")
    request = LeadEnrichmentFieldCandidateAccept(accepted_by="reviewer-a")

    try:
        LeadEnrichmentService.accept_field_candidate(candidate, request=request, now=datetime(2026, 6, 4, 11, tzinfo=UTC))
    except ValueError as exc:
        assert "关键字段" in str(exc)
        assert "来源证据" in str(exc)
    else:
        raise AssertionError("critical field without evidence should be rejected")
