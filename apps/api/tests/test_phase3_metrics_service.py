from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import phase3_dashboard
from app.main import app
from app.models import (
    ContactMethod,
    Customer,
    CustomerFollowup,
    CustomerVehicleIntent,
    LeadCleanupSuggestion,
    LeadEnrichmentFieldCandidate,
    LeadEnrichmentResult,
    RiskEvent,
    StagingLead,
)
from app.models.enums import (
    ChannelRiskLevel,
    ContactMethodType,
    CustomerFollowupTeam,
    CustomerFollowupType,
    CustomerGrade,
    CustomerStatus,
    CustomerType,
    CustomerVehicleIntentSourceType,
    CustomerVehicleIntentStatus,
    LeadCleanupSuggestionReviewStatus,
    LeadCleanupSuggestionType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentFieldSourceType,
    LeadEnrichmentResultStatus,
    LeadEnrichmentType,
    RiskEventSeverity,
    RiskEventStatus,
    StagingQueueStatus,
    StagingReviewStatus,
)
from app.services.phase3_metrics import Phase3MetricsService


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeMetricsSession:
    def __init__(self, rows_by_model):
        self.rows_by_model = rows_by_model

    def scalars(self, statement):
        model = statement.column_descriptions[0]["entity"]
        return FakeScalarResult(self.rows_by_model.get(model, []))


class FakeAsyncSession:
    def __init__(self, sync_session):
        self.sync_session = sync_session

    async def run_sync(self, fn):
        return fn(self.sync_session)


def customer(customer_id, *, owner="ops-a", status=CustomerStatus.CUSTOMER_SERVICE_FOLLOWING, grade=CustomerGrade.B):
    return Customer(
        id=customer_id,
        name=f"客户-{customer_id}",
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        grade=grade,
        status=status,
        owner=owner,
        owner_team="customer_service" if owner else None,
    )


def staging_lead():
    return StagingLead(
        id=uuid4(),
        candidate_url_id=uuid4(),
        customer_name="AutoCity",
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        contacts_json=[{"type": "email", "value": "sales@example.ru"}],
        source_evidence="官网公开来源",
        recommended_grade=CustomerGrade.B,
        review_status=StagingReviewStatus.APPROVED,
        queue_status=StagingQueueStatus.ELIGIBLE,
    )


def enrichment_result(status):
    return LeadEnrichmentResult(
        id=uuid4(),
        staging_lead_id=uuid4(),
        enrichment_type=LeadEnrichmentType.MANUAL_SUPPLEMENT,
        triggered_by="ops-a",
        status=status,
        input_snapshot_json={},
        evidence_links=[],
        missing_fields=[],
    )


def field_candidate(status):
    return LeadEnrichmentFieldCandidate(
        id=uuid4(),
        enrichment_result_id=uuid4(),
        staging_lead_id=uuid4(),
        field_name="邮箱",
        candidate_value="sales@example.ru",
        source_type=LeadEnrichmentFieldSourceType.MANUAL_PUBLIC_INFO,
        evidence_note="官网联系页公开邮箱",
        review_status=status,
    )


def contact(customer_id):
    return ContactMethod(
        id=uuid4(),
        customer_id=customer_id,
        method_type=ContactMethodType.EMAIL,
        value="sales@example.ru",
        evidence_note="官网联系页公开邮箱",
    )


def vehicle_intent(customer_id, status=CustomerVehicleIntentStatus.ACTIVE):
    return CustomerVehicleIntent(
        id=uuid4(),
        customer_id=customer_id,
        brand="Toyota",
        model="Camry",
        source_type=CustomerVehicleIntentSourceType.MANUAL_CUSTOMER_REPLY,
        status=status,
        created_by="ops-a",
    )


def followup(customer_id):
    return CustomerFollowup(
        id=uuid4(),
        customer_id=customer_id,
        owner_id="ops-a",
        team=CustomerFollowupTeam.CUSTOMER_SERVICE,
        followup_type=CustomerFollowupType.INTERNAL_NOTE,
        content="人工完成首次跟进。",
        created_by="ops-a",
        created_at=datetime(2026, 6, 4, tzinfo=UTC),
    )


def cleanup_suggestion(suggestion_type, status):
    return LeadCleanupSuggestion(
        id=uuid4(),
        cleanup_run_id=uuid4(),
        staging_lead_id=uuid4(),
        suggestion_type=suggestion_type,
        confidence_score=0.9,
        reason="清洗建议",
        evidence_json={"evidence_note": "公开证据"},
        recommended_action="人工确认",
        review_status=status,
    )


def risk_event(severity=RiskEventSeverity.HIGH, status=RiskEventStatus.OPEN):
    return RiskEvent(
        id=uuid4(),
        channel="website",
        risk_level=ChannelRiskLevel.HIGH,
        event_type="policy_violation",
        severity=severity,
        resolution_status=status,
        result="blocked",
    )


def build_session_with_metrics_data():
    customer_a = uuid4()
    customer_b = uuid4()
    customer_c = uuid4()
    return FakeMetricsSession(
        {
            StagingLead: [staging_lead(), staging_lead(), staging_lead(), staging_lead()],
            Customer: [
                customer(customer_a, owner="ops-a"),
                customer(customer_b, owner="sales-a", status=CustomerStatus.SALES_FOLLOWING, grade=CustomerGrade.C),
                customer(customer_c, owner=None, status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE),
            ],
            LeadEnrichmentResult: [
                enrichment_result(LeadEnrichmentResultStatus.SUCCEEDED),
                enrichment_result(LeadEnrichmentResultStatus.SUCCEEDED),
                enrichment_result(LeadEnrichmentResultStatus.FAILED),
            ],
            LeadEnrichmentFieldCandidate: [
                field_candidate(LeadEnrichmentFieldReviewStatus.ACCEPTED),
                field_candidate(LeadEnrichmentFieldReviewStatus.ACCEPTED),
                field_candidate(LeadEnrichmentFieldReviewStatus.REJECTED),
                field_candidate(LeadEnrichmentFieldReviewStatus.PENDING),
            ],
            ContactMethod: [contact(customer_a), contact(customer_b)],
            CustomerVehicleIntent: [vehicle_intent(customer_b), vehicle_intent(customer_c, CustomerVehicleIntentStatus.ARCHIVED)],
            CustomerFollowup: [followup(customer_a), followup(customer_b)],
            LeadCleanupSuggestion: [
                cleanup_suggestion(LeadCleanupSuggestionType.STRONG_DUPLICATE, LeadCleanupSuggestionReviewStatus.EXECUTED),
                cleanup_suggestion(LeadCleanupSuggestionType.POSSIBLE_DUPLICATE, LeadCleanupSuggestionReviewStatus.EXECUTED),
                cleanup_suggestion(LeadCleanupSuggestionType.RESTORE_FROM_WATCH, LeadCleanupSuggestionReviewStatus.EXECUTED),
                cleanup_suggestion(LeadCleanupSuggestionType.CONFIRM_INVALID, LeadCleanupSuggestionReviewStatus.APPROVED),
                cleanup_suggestion(LeadCleanupSuggestionType.NEEDS_MANUAL_REVIEW, LeadCleanupSuggestionReviewStatus.PENDING),
            ],
            RiskEvent: [risk_event(), risk_event(RiskEventSeverity.LOW, RiskEventStatus.RESOLVED)],
        },
    )


def test_phase3_metrics_service_calculates_frozen_business_rates() -> None:
    metrics = Phase3MetricsService(build_session_with_metrics_data()).metrics()

    assert metrics["customer_acceptance"]["promoted_customer_count"] == 3
    assert metrics["customer_acceptance"]["accepted_first_followup_count"] == 2
    assert metrics["customer_acceptance"]["effective_customer_acceptance_rate"] == 2 / 3
    assert metrics["enrichment"]["enrichment_success_rate"] == 2 / 3
    assert metrics["enrichment"]["field_adoption_rate"] == 2 / 4
    assert metrics["enrichment"]["promotion_rate"] == 3 / 4
    assert metrics["enrichment"]["contact_completeness_rate"] == 2 / 3
    assert metrics["enrichment"]["vehicle_intent_rate"] == 1 / 3
    assert metrics["cleanup"]["adoption_rate"] == 4 / 5
    assert metrics["cleanup"]["duplicate_merge_rate"] == 2 / 5
    assert metrics["cleanup"]["watch_restore_rate"] == 1 / 5
    assert metrics["risk"]["risk_violation_count"] == 1
    assert metrics["risk"]["risk_violation_target_zero"] is False


def test_phase3_metrics_service_returns_zero_rates_without_data() -> None:
    metrics = Phase3MetricsService(FakeMetricsSession({})).metrics()

    assert metrics["customer_acceptance"]["effective_customer_acceptance_rate"] == 0
    assert metrics["enrichment"]["enrichment_success_rate"] == 0
    assert metrics["enrichment"]["field_adoption_rate"] == 0
    assert metrics["enrichment"]["promotion_rate"] == 0
    assert metrics["enrichment"]["contact_completeness_rate"] == 0
    assert metrics["enrichment"]["vehicle_intent_rate"] == 0
    assert metrics["cleanup"]["adoption_rate"] == 0
    assert metrics["risk"]["risk_violation_count"] == 0
    assert metrics["risk"]["risk_violation_target_zero"] is True


def test_phase3_dashboard_metrics_api_returns_contract_payload() -> None:
    async def override_session():
        yield FakeAsyncSession(build_session_with_metrics_data())

    app.dependency_overrides[phase3_dashboard.get_async_session] = override_session
    try:
        response = TestClient(app).get("/phase3-dashboard/metrics")
    finally:
        app.dependency_overrides.pop(phase3_dashboard.get_async_session, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_acceptance"]["effective_customer_acceptance_rate"] == 2 / 3
    assert payload["enrichment"]["contact_completeness_rate"] == 2 / 3
    assert payload["cleanup"]["watch_restore_rate"] == 1 / 5
    assert payload["risk"]["risk_violation_target_zero"] is False
    assert payload["guardrails"]["auto_outreach_allowed"] is False
    assert payload["guardrails"]["auto_friend_request_allowed"] is False
    assert payload["guardrails"]["login_batch_collection_allowed"] is False
