from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.lead_enrichment_field_candidate import LeadEnrichmentFieldCandidate
from app.models.lead_enrichment_result import LeadEnrichmentResult
from app.models.enums import (
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
)
from app.services.lead_enrichment import LeadEnrichmentService


client = TestClient(app)


def build_result(index: int = 0) -> LeadEnrichmentResult:
    return LeadEnrichmentResult(
        id=uuid4(),
        staging_lead_id=uuid4(),
        enrichment_type=LeadEnrichmentType.AI_DEEP_RESEARCH,
        triggered_by="ops-a",
        status=LeadEnrichmentResultStatus.SUCCEEDED,
        input_snapshot_json={"customer_name": "Unknown", "contacts_json": []},
        output_json={"city": None, "contacts": []},
        evidence_links=["https://example.com/public"],
        confidence_score=0.8,
        missing_fields=["purchase_frequency"],
        recommended_action="manual_review",
        created_at=datetime(2026, 6, 4, 9, index, tzinfo=UTC),
        updated_at=datetime(2026, 6, 4, 9, index, tzinfo=UTC),
    )


def build_candidate(result: LeadEnrichmentResult) -> LeadEnrichmentFieldCandidate:
    return LeadEnrichmentFieldCandidate(
        id=uuid4(),
        enrichment_result_id=result.id,
        staging_lead_id=result.staging_lead_id,
        field_name="contacts_json",
        candidate_value=[],
        source_type=LeadEnrichmentFieldSourceType.AI_PUBLIC_SOURCE,
        source_url="https://example.com/public",
        evidence_note="公开页面没有展示联系方式，保留空数组。",
        confidence_score=0.66,
        review_status=LeadEnrichmentFieldReviewStatus.NEEDS_REVIEW,
        created_at=datetime(2026, 6, 4, 9, 10, tzinfo=UTC),
        updated_at=datetime(2026, 6, 4, 9, 10, tzinfo=UTC),
    )


def test_serialize_enrichment_result_with_field_candidates_preserves_unknown_null_and_empty_list() -> None:
    result = build_result()
    candidate = build_candidate(result)

    payload = LeadEnrichmentService.serialize_result_with_candidates(result, [candidate])

    assert payload["id"] == result.id
    assert payload["input_snapshot_json"]["customer_name"] == "Unknown"
    assert payload["input_snapshot_json"]["contacts_json"] == []
    assert payload["output_json"]["city"] is None
    assert payload["output_json"]["contacts"] == []
    assert payload["field_candidates"][0]["candidate_value"] == []
    assert payload["field_candidates"][0]["source_type"] == "ai_public_source"
    assert payload["field_candidates"][0]["source_url"] == "https://example.com/public"
    assert payload["field_candidates"][0]["evidence_note"] == "公开页面没有展示联系方式，保留空数组。"
    assert payload["field_candidates"][0]["confidence_score"] == 0.66
    assert payload["field_candidates"][0]["review_status"] == "needs_review"


def test_group_field_candidates_by_result_id() -> None:
    first = build_result(1)
    second = build_result(2)
    candidate = build_candidate(second)

    grouped = LeadEnrichmentService.group_field_candidates_by_result_id([candidate])
    first_payload = LeadEnrichmentService.serialize_result_with_candidates(first, grouped.get(first.id, []))
    second_payload = LeadEnrichmentService.serialize_result_with_candidates(second, grouped.get(second.id, []))

    assert first_payload["field_candidates"] == []
    assert len(second_payload["field_candidates"]) == 1
    assert second_payload["field_candidates"][0]["enrichment_result_id"] == second.id


def test_enrichment_results_response_schema_accepts_nested_candidates() -> None:
    from app.schemas.lead_enrichment import LeadEnrichmentResultsResponse

    result = build_result()
    candidate = build_candidate(result)
    payload = LeadEnrichmentResultsResponse(
        staging_lead_id=result.staging_lead_id,
        items=[LeadEnrichmentService.serialize_result_with_candidates(result, [candidate])],
    )

    assert payload.items[0].field_candidates[0].field_name == "contacts_json"
    assert payload.items[0].field_candidates[0].candidate_value == []
    assert payload.items[0].field_candidates[0].review_status == LeadEnrichmentFieldReviewStatus.NEEDS_REVIEW


def test_lead_enrichment_query_route_is_registered_as_read_only_without_auto_promotion() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/staging-leads/{lead_id}/enrichment-results" in paths
    assert "get" in paths["/staging-leads/{lead_id}/enrichment-results"]
    assert "post" not in paths["/staging-leads/{lead_id}/enrichment-results"]
    assert "patch" not in paths["/staging-leads/{lead_id}/enrichment-results"]
    assert all("promote" not in path.lower() for path in paths if "lead-enrichment" in path)
    assert all("outreach" not in path.lower() for path in paths if "lead-enrichment" in path)
