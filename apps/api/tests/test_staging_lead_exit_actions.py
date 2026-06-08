from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.enums import CustomerGrade, StagingQueueStatus, StagingReviewStatus
from app.schemas.staging_leads import (
    StagingLeadAbandonRequest,
    StagingLeadExitActionResponse,
    StagingLeadGradeUpdateRequest,
    StagingLeadMarkInvalidRequest,
    StagingLeadMarkWatchRequest,
)
from app.services.staging_lead_actions import StagingLeadActionService


API_ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def build_lead(*, grade: CustomerGrade = CustomerGrade.B, queue_status: StagingQueueStatus = StagingQueueStatus.ELIGIBLE):
    return SimpleNamespace(
        id=uuid4(),
        recommended_grade=grade,
        recommended_reason="原始 AI 分级。",
        review_status=StagingReviewStatus.PENDING_REVIEW,
        queue_status=queue_status,
        requires_compliance_review=grade == CustomerGrade.C,
        updated_at=datetime(2026, 6, 4, 13, 10),
    )


def test_exit_action_routes_are_registered_without_delete_or_outreach() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    for path in (
        "/staging-leads/{lead_id}/mark-watch",
        "/staging-leads/{lead_id}/mark-invalid",
        "/staging-leads/{lead_id}/abandon",
        "/staging-leads/{lead_id}/grade",
    ):
        assert path in paths
        assert "patch" in paths[path]
        assert "delete" not in paths[path]

    api_text = (API_ROOT / "app" / "api" / "staging_leads.py").read_text(encoding="utf-8")
    assert "mark-watch" in api_text
    assert "mark-invalid" in api_text
    assert "abandon" in api_text
    assert "auto_send" not in api_text
    assert "outreach" not in api_text.lower()


def test_exit_action_requests_require_actor_and_reason() -> None:
    for request_cls in (StagingLeadMarkWatchRequest, StagingLeadMarkInvalidRequest, StagingLeadAbandonRequest):
        try:
            request_cls(actor="", reason="")
        except ValidationError as exc:
            assert "actor" in str(exc)
            assert "reason" in str(exc)
        else:
            raise AssertionError(f"{request_cls.__name__} should require actor and reason")


def test_mark_watch_sets_not_eligible_and_writes_review_log_payload() -> None:
    lead = build_lead(grade=CustomerGrade.B)
    request = StagingLeadMarkWatchRequest(actor="ops-a", reason="两轮补全仍缺关键联系方式。")

    result = StagingLeadActionService.apply_mark_watch(lead, request=request, now=datetime(2026, 6, 4, 14))

    assert lead.recommended_grade == CustomerGrade.WATCH
    assert lead.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    assert lead.review_status == StagingReviewStatus.REJECTED
    assert lead.recommended_reason == "两轮补全仍缺关键联系方式。"
    assert lead.requires_compliance_review is False
    assert result["review_log"].action == "mark_watch"
    assert result["review_log"].reviewer == "ops-a"
    assert result["review_log"].result == "watch"
    assert result["review_log"].error_message == "两轮补全仍缺关键联系方式。"


def test_mark_invalid_and_abandon_never_enter_touch_queue() -> None:
    invalid_lead = build_lead(grade=CustomerGrade.C)
    invalid_request = StagingLeadMarkInvalidRequest(actor="ops-a", reason="确认不是车辆销售主体。")
    invalid_result = StagingLeadActionService.apply_mark_invalid(
        invalid_lead,
        request=invalid_request,
        now=datetime(2026, 6, 4, 14),
    )

    abandoned_lead = build_lead(grade=CustomerGrade.B)
    abandon_request = StagingLeadAbandonRequest(actor="ops-b", reason="公开来源失效，无法补全。")
    abandon_result = StagingLeadActionService.apply_abandon(
        abandoned_lead,
        request=abandon_request,
        now=datetime(2026, 6, 4, 14),
    )

    assert invalid_lead.recommended_grade == CustomerGrade.INVALID
    assert invalid_lead.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    assert invalid_lead.review_status == StagingReviewStatus.REJECTED
    assert invalid_lead.requires_compliance_review is False
    assert invalid_result["review_log"].action == "mark_invalid"
    assert invalid_result["review_log"].result == "invalid"

    assert abandoned_lead.recommended_grade == CustomerGrade.INVALID
    assert abandoned_lead.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    assert abandoned_lead.review_status == StagingReviewStatus.REJECTED
    assert abandon_result["review_log"].action == "abandon_staging_lead"
    assert abandon_result["review_log"].result == "abandoned"


def test_grade_update_keeps_watch_invalid_out_of_touch_queue_and_sets_c_compliance_flag() -> None:
    lead = build_lead(grade=CustomerGrade.B)

    c_result = StagingLeadActionService.apply_grade_update(
        lead,
        request=StagingLeadGradeUpdateRequest(actor="ops-a", recommended_grade=CustomerGrade.C, reason="人工确认销售机会。"),
        now=datetime(2026, 6, 4, 14),
    )
    assert lead.recommended_grade == CustomerGrade.C
    assert lead.queue_status == StagingQueueStatus.ELIGIBLE
    assert lead.requires_compliance_review is True
    assert c_result["review_log"].action == "update_staging_grade"

    watch_result = StagingLeadActionService.apply_grade_update(
        lead,
        request=StagingLeadGradeUpdateRequest(actor="ops-a", recommended_grade=CustomerGrade.WATCH, reason="补全不足，转观察。"),
        now=datetime(2026, 6, 4, 14, 5),
    )
    assert lead.recommended_grade == CustomerGrade.WATCH
    assert lead.queue_status == StagingQueueStatus.NOT_ELIGIBLE
    assert lead.review_status == StagingReviewStatus.REJECTED
    assert lead.requires_compliance_review is False
    assert watch_result["review_log"].result == "Watch"


def test_do_not_contact_lead_cannot_be_made_eligible_by_grade_update() -> None:
    lead = build_lead(grade=CustomerGrade.WATCH, queue_status=StagingQueueStatus.BLOCKED)
    request = StagingLeadGradeUpdateRequest(actor="ops-a", recommended_grade=CustomerGrade.B, reason="尝试恢复。")

    try:
        StagingLeadActionService.apply_grade_update(
            lead,
            request=request,
            has_do_not_contact_match=True,
            now=datetime(2026, 6, 4, 14),
        )
    except ValueError as exc:
        assert "勿扰" in str(exc)
    else:
        raise AssertionError("DNC matched lead should not be made eligible by grade update")


def test_exit_action_response_exposes_audit_reference() -> None:
    response = StagingLeadExitActionResponse(
        staging_lead_id=uuid4(),
        action="mark_watch",
        recommended_grade=CustomerGrade.WATCH,
        review_status=StagingReviewStatus.REJECTED,
        queue_status=StagingQueueStatus.NOT_ELIGIBLE,
        reason="补全失败。",
        review_log_id=uuid4(),
    )

    assert response.recommended_grade == CustomerGrade.WATCH
    assert response.review_log_id is not None
