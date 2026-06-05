from sqlalchemy import select
from sqlalchemy.orm import Session

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
    CustomerVehicleIntentStatus,
    LeadCleanupSuggestionReviewStatus,
    LeadCleanupSuggestionType,
    LeadEnrichmentFieldReviewStatus,
    LeadEnrichmentResultStatus,
    RiskEventSeverity,
    RiskEventStatus,
)


class Phase3CleanupMetricsService:
    DUPLICATE_TYPES = {
        LeadCleanupSuggestionType.STRONG_DUPLICATE,
        LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0

    def list_cleanup_suggestions(self) -> list[LeadCleanupSuggestion]:
        return list(self.session.scalars(select(LeadCleanupSuggestion)).all())

    def cleanup_metrics(self) -> dict[str, int | float | bool]:
        suggestions = self.list_cleanup_suggestions()
        created_count = len(suggestions)
        approved_count = sum(
            1
            for item in suggestions
            if LeadCleanupSuggestionReviewStatus(item.review_status)
            in {
                LeadCleanupSuggestionReviewStatus.APPROVED,
                LeadCleanupSuggestionReviewStatus.EXECUTED,
            }
        )
        executed = [
            item
            for item in suggestions
            if LeadCleanupSuggestionReviewStatus(item.review_status) == LeadCleanupSuggestionReviewStatus.EXECUTED
        ]
        executed_count = len(executed)
        rejected_count = sum(
            1
            for item in suggestions
            if LeadCleanupSuggestionReviewStatus(item.review_status) == LeadCleanupSuggestionReviewStatus.REJECTED
        )
        pending_count = sum(
            1
            for item in suggestions
            if LeadCleanupSuggestionReviewStatus(item.review_status) == LeadCleanupSuggestionReviewStatus.PENDING
        )
        duplicate_merge_count = sum(1 for item in executed if LeadCleanupSuggestionType(item.suggestion_type) in self.DUPLICATE_TYPES)
        watch_restore_count = sum(
            1
            for item in executed
            if LeadCleanupSuggestionType(item.suggestion_type) == LeadCleanupSuggestionType.RESTORE_FROM_WATCH
        )
        invalid_confirm_count = sum(
            1
            for item in executed
            if LeadCleanupSuggestionType(item.suggestion_type) == LeadCleanupSuggestionType.CONFIRM_INVALID
        )

        return {
            "created_count": created_count,
            "approved_count": approved_count,
            "executed_count": executed_count,
            "rejected_count": rejected_count,
            "pending_count": pending_count,
            "duplicate_merge_count": duplicate_merge_count,
            "watch_restore_count": watch_restore_count,
            "invalid_confirm_count": invalid_confirm_count,
            "adoption_rate": self.rate(approved_count, created_count),
            "execution_rate": self.rate(executed_count, created_count),
            "duplicate_merge_rate": self.rate(duplicate_merge_count, created_count),
            "watch_restore_rate": self.rate(watch_restore_count, created_count),
            "invalid_confirm_rate": self.rate(invalid_confirm_count, created_count),
            "auto_suggestion_not_equal_executed": created_count != executed_count,
        }


class Phase3MetricsService:
    ACTIVE_RISK_STATUSES = {RiskEventStatus.OPEN, RiskEventStatus.INVESTIGATING}
    RISK_VIOLATION_SEVERITIES = {RiskEventSeverity.HIGH, RiskEventSeverity.CRITICAL}

    def __init__(self, session: Session) -> None:
        self.session = session
        self.cleanup_service = Phase3CleanupMetricsService(session)

    @staticmethod
    def rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0

    def list_model(self, model):
        return list(self.session.scalars(select(model)).all())

    def customer_acceptance_metrics(self) -> dict[str, int | float]:
        customers = self.list_model(Customer)
        followups = self.list_model(CustomerFollowup)
        followed_customer_ids = {item.customer_id for item in followups}
        accepted_first_followup_count = sum(
            1
            for customer in customers
            if customer.id in followed_customer_ids and (customer.owner or customer.owner_team)
        )
        promoted_customer_count = len(customers)

        return {
            "promoted_customer_count": promoted_customer_count,
            "accepted_first_followup_count": accepted_first_followup_count,
            "effective_customer_acceptance_rate": self.rate(accepted_first_followup_count, promoted_customer_count),
        }

    def enrichment_metrics(self) -> dict[str, int | float]:
        staging_leads = self.list_model(StagingLead)
        customers = self.list_model(Customer)
        enrichment_results = self.list_model(LeadEnrichmentResult)
        field_candidates = self.list_model(LeadEnrichmentFieldCandidate)
        contacts = self.list_model(ContactMethod)
        vehicle_intents = self.list_model(CustomerVehicleIntent)

        succeeded_enrichment_count = sum(
            1 for item in enrichment_results if LeadEnrichmentResultStatus(item.status) == LeadEnrichmentResultStatus.SUCCEEDED
        )
        accepted_field_count = sum(
            1 for item in field_candidates if LeadEnrichmentFieldReviewStatus(item.review_status) == LeadEnrichmentFieldReviewStatus.ACCEPTED
        )
        customer_ids_with_contact = {item.customer_id for item in contacts if item.value}
        customer_ids_with_active_intent = {
            item.customer_id
            for item in vehicle_intents
            if CustomerVehicleIntentStatus(item.status) == CustomerVehicleIntentStatus.ACTIVE
        }
        promoted_customer_count = len(customers)

        return {
            "staging_lead_count": len(staging_leads),
            "promoted_customer_count": promoted_customer_count,
            "enrichment_result_count": len(enrichment_results),
            "succeeded_enrichment_count": succeeded_enrichment_count,
            "field_candidate_count": len(field_candidates),
            "accepted_field_count": accepted_field_count,
            "contact_complete_customer_count": len(customer_ids_with_contact),
            "vehicle_intent_customer_count": len(customer_ids_with_active_intent),
            "enrichment_success_rate": self.rate(succeeded_enrichment_count, len(enrichment_results)),
            "field_adoption_rate": self.rate(accepted_field_count, len(field_candidates)),
            "promotion_rate": self.rate(promoted_customer_count, len(staging_leads)),
            "contact_completeness_rate": self.rate(len(customer_ids_with_contact), promoted_customer_count),
            "vehicle_intent_rate": self.rate(len(customer_ids_with_active_intent), promoted_customer_count),
        }

    def risk_metrics(self) -> dict[str, int | bool]:
        risk_events = self.list_model(RiskEvent)
        risk_violation_count = sum(
            1
            for item in risk_events
            if RiskEventSeverity(item.severity) in self.RISK_VIOLATION_SEVERITIES
            and RiskEventStatus(item.resolution_status) in self.ACTIVE_RISK_STATUSES
        )

        return {
            "risk_event_count": len(risk_events),
            "risk_violation_count": risk_violation_count,
            "risk_violation_target_zero": risk_violation_count == 0,
        }

    def metrics(self) -> dict[str, object]:
        return {
            "customer_acceptance": self.customer_acceptance_metrics(),
            "enrichment": self.enrichment_metrics(),
            "cleanup": self.cleanup_service.cleanup_metrics(),
            "risk": self.risk_metrics(),
            "guardrails": {
                "auto_outreach_allowed": False,
                "auto_friend_request_allowed": False,
                "login_batch_collection_allowed": False,
                "risk_violation_target": 0,
            },
        }
