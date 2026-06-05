from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ContactMethod, Customer, ReviewLog, StagingLead
from app.models.enums import CustomerGrade, StagingQueueStatus, StagingReviewStatus
from app.schemas.staging_leads import (
    StagingLeadAbandonRequest,
    StagingLeadGradeUpdateRequest,
    StagingLeadMarkInvalidRequest,
    StagingLeadMarkWatchRequest,
)
from app.services.staging_leads import StagingLeadService


class StagingLeadActionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_staging_lead(self, lead_id: UUID) -> StagingLead | None:
        return self.session.get(StagingLead, lead_id)

    @staticmethod
    def _now() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def _review_log(
        lead,
        *,
        action: str,
        actor: str,
        result: str,
        reason: str,
    ) -> ReviewLog:
        return ReviewLog(
            task_id=str(lead.id),
            agent_name="manual-review",
            action=action,
            reviewer=actor,
            input_ref=f"staging:{lead.id}",
            output_ref=None,
            result=result,
            error_message=reason,
        )

    @classmethod
    def _set_exit_state(
        cls,
        lead,
        *,
        grade: CustomerGrade,
        reason: str,
        now: datetime | None,
    ) -> None:
        lead.recommended_grade = grade
        lead.recommended_reason = reason
        lead.review_status = StagingReviewStatus.REJECTED
        lead.queue_status = StagingQueueStatus.NOT_ELIGIBLE
        lead.requires_compliance_review = False
        lead.updated_at = now or cls._now()

    @classmethod
    def apply_mark_watch(
        cls,
        lead,
        *,
        request: StagingLeadMarkWatchRequest,
        now: datetime | None = None,
    ) -> dict:
        cls._set_exit_state(lead, grade=CustomerGrade.WATCH, reason=request.reason, now=now)
        review_log = cls._review_log(
            lead,
            action="mark_watch",
            actor=request.actor,
            result="watch",
            reason=request.reason,
        )
        return {"lead": lead, "review_log": review_log, "action": "mark_watch", "reason": request.reason}

    @classmethod
    def apply_mark_invalid(
        cls,
        lead,
        *,
        request: StagingLeadMarkInvalidRequest,
        now: datetime | None = None,
    ) -> dict:
        cls._set_exit_state(lead, grade=CustomerGrade.INVALID, reason=request.reason, now=now)
        review_log = cls._review_log(
            lead,
            action="mark_invalid",
            actor=request.actor,
            result="invalid",
            reason=request.reason,
        )
        return {"lead": lead, "review_log": review_log, "action": "mark_invalid", "reason": request.reason}

    @classmethod
    def apply_abandon(
        cls,
        lead,
        *,
        request: StagingLeadAbandonRequest,
        now: datetime | None = None,
    ) -> dict:
        cls._set_exit_state(lead, grade=CustomerGrade.INVALID, reason=request.reason, now=now)
        review_log = cls._review_log(
            lead,
            action="abandon_staging_lead",
            actor=request.actor,
            result="abandoned",
            reason=request.reason,
        )
        return {"lead": lead, "review_log": review_log, "action": "abandon_staging_lead", "reason": request.reason}

    @classmethod
    def apply_grade_update(
        cls,
        lead,
        *,
        request: StagingLeadGradeUpdateRequest,
        has_do_not_contact_match: bool = False,
        now: datetime | None = None,
    ) -> dict:
        if has_do_not_contact_match:
            raise ValueError("命中勿扰客户，等级调整不得绕过勿扰状态。")

        timestamp = now or cls._now()
        grade = CustomerGrade(request.recommended_grade)
        lead.recommended_grade = grade
        lead.recommended_reason = request.reason
        lead.requires_compliance_review = grade == CustomerGrade.C
        if grade in {CustomerGrade.WATCH, CustomerGrade.INVALID}:
            lead.review_status = StagingReviewStatus.REJECTED
            lead.queue_status = StagingQueueStatus.NOT_ELIGIBLE
            lead.requires_compliance_review = False
        else:
            lead.review_status = StagingReviewStatus.PENDING_REVIEW
            lead.queue_status = StagingQueueStatus.ELIGIBLE
        lead.updated_at = timestamp
        review_log = cls._review_log(
            lead,
            action="update_staging_grade",
            actor=request.actor,
            result=grade.value,
            reason=request.reason,
        )
        return {"lead": lead, "review_log": review_log, "action": "update_staging_grade", "reason": request.reason}

    def has_do_not_contact_match(self, lead: StagingLead) -> bool:
        contact_values = {
            str(item.get("value", "")).strip().lower()
            for item in (lead.contacts_json or [])
            if isinstance(item, dict) and str(item.get("value", "")).strip()
        }
        normalized_name = (lead.customer_name or "").strip().lower()
        if normalized_name and normalized_name != "unknown":
            if self.session.scalar(
                select(Customer.id)
                .where(Customer.do_not_contact.is_(True), func.lower(Customer.name) == normalized_name)
                .limit(1)
            ):
                return True
        if not contact_values:
            return False
        return bool(
            self.session.scalar(
                select(ContactMethod.id)
                .join(Customer, ContactMethod.customer_id == Customer.id)
                .where(Customer.do_not_contact.is_(True), func.lower(ContactMethod.value).in_(contact_values))
                .limit(1)
            )
        )

    @staticmethod
    def _persist_result(session: Session, result: dict) -> dict:
        session.add(result["review_log"])
        session.flush()
        return result

    def mark_watch(self, lead: StagingLead, *, request: StagingLeadMarkWatchRequest) -> dict:
        return self._persist_result(self.session, self.apply_mark_watch(lead, request=request))

    def mark_invalid(self, lead: StagingLead, *, request: StagingLeadMarkInvalidRequest) -> dict:
        return self._persist_result(self.session, self.apply_mark_invalid(lead, request=request))

    def abandon(self, lead: StagingLead, *, request: StagingLeadAbandonRequest) -> dict:
        return self._persist_result(self.session, self.apply_abandon(lead, request=request))

    def update_grade(self, lead: StagingLead, *, request: StagingLeadGradeUpdateRequest) -> dict:
        return self._persist_result(
            self.session,
            self.apply_grade_update(
                lead,
                request=request,
                has_do_not_contact_match=self.has_do_not_contact_match(lead),
            ),
        )
