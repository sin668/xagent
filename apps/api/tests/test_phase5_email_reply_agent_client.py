from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models import AgentTaskRun, EmailReplyDraft
from app.models.enums import AgentTaskRunStatus, AgentTaskType, EmailReplyDraftStatus
from app.services.email_reply_agent import EmailReplyAgentService


class SuccessfulEmailReplyRuntime:
    class Settings:
        agents_base_url = "http://agents.local:8010"

    settings = Settings()

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run_email_reply_response(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "schema_version": "phase4.agent.run.v1",
            "agent_service_run_id": "44444444-4444-4444-4444-444444444444",
            "request_id": str(kwargs["request_id"]),
            "status": "succeeded",
            "agent_type": "email_reply",
            "agent_mode": kwargs["agent_mode"],
            "output": {
                "schema_version": "email-reply-v1",
                "detected_language": "ru",
                "reply_language": "ru",
                "language_confidence": 0.91,
                "suggested_subject": "Vehicle procurement follow-up",
                "suggested_body": "Hello, thanks for your message.",
                "knowledge_hits": [{"knowledge_item_id": "k-1", "similarity_score": 0.88}],
                "risk_flags": [],
                "auto_send_allowed": False,
                "manual_review_required": True,
                "manual_review_reason": "需要人工确认。",
                "next_action": "send_after_review",
                "audit": {
                    "prompt_version": "v3",
                    "model": "deepseek-chat",
                    "route_decision": "manual_review",
                },
            },
            "audit": {
                "writes_core_tables": False,
                "executed_nodes": ["load_context", "retrieve_knowledge", "draft_reply"],
                "risk_flags": [],
            },
            "error": None,
        }


class FailingEmailReplyRuntime:
    class Settings:
        agents_base_url = "http://agents.local:8010"

    settings = Settings()

    def run_email_reply_response(self, **kwargs):
        raise RuntimeError("apps/agents unavailable")


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False

    def add(self, item: object) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flushed = True


def make_draft() -> EmailReplyDraft:
    return EmailReplyDraft(
        id=uuid4(),
        thread_id=uuid4(),
        message_id=uuid4(),
        customer_id=uuid4(),
        ai_suggested_body="",
        knowledge_hits_json=[],
        auto_send_decision_json={},
        status=EmailReplyDraftStatus.DRAFTED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_email_reply_agent_service_saves_external_summary_and_updates_draft() -> None:
    draft = make_draft()
    runtime = SuccessfulEmailReplyRuntime()
    session = RecordingSession()

    task_run = EmailReplyAgentService.run_email_reply_agent(
        draft,
        runtime=runtime,
        session=session,
        context={"customer": {"name": "OOO Test"}},
        prompt={"task_type": "EMAIL_REPLY_DRAFT", "version": "v3"},
        options={"tone": "concise"},
        now=datetime(2026, 6, 5, 8, 0, tzinfo=UTC),
    )

    assert isinstance(task_run, AgentTaskRun)
    assert task_run.task_type == AgentTaskType.EMAIL_REPLY
    assert task_run.status == AgentTaskRunStatus.SUCCEEDED
    assert task_run.output_summary_json["external_agent_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert task_run.output_summary_json["external_agent_status"] == "succeeded"
    assert task_run.output_summary_json["external_agent_type"] == "email_reply"
    assert task_run.output_summary_json["knowledge_hit_count"] == 1
    assert task_run.output_summary_json["auto_send_allowed"] is False
    assert task_run.output_summary_json["manual_review_required"] is True
    assert task_run.output_summary_json["writes_core_tables"] is False
    assert draft.agent_task_run_id == task_run.id
    assert draft.agent_service_run_id == UUID("44444444-4444-4444-4444-444444444444")
    assert draft.ai_suggested_subject == "Vehicle procurement follow-up"
    assert draft.ai_suggested_body == "Hello, thanks for your message."
    assert draft.knowledge_hits_json == [{"knowledge_item_id": "k-1", "similarity_score": 0.88}]
    assert draft.auto_send_allowed is False
    assert draft.manual_review_required is True
    assert draft.manual_review_reason == "需要人工确认。"
    assert draft.status == EmailReplyDraftStatus.PENDING_REVIEW
    assert runtime.calls[0]["thread_id"] == draft.thread_id
    assert runtime.calls[0]["message_id"] == draft.message_id
    assert runtime.calls[0]["customer_id"] == draft.customer_id
    assert runtime.calls[0]["draft_id"] == draft.id
    assert session.added == [task_run, draft]
    assert session.flushed is True


def test_email_reply_agent_service_records_degraded_failure_without_raising() -> None:
    draft = make_draft()
    session = RecordingSession()

    task_run = EmailReplyAgentService.run_email_reply_agent(
        draft,
        runtime=FailingEmailReplyRuntime(),
        session=session,
        context={},
        prompt={},
        now=datetime(2026, 6, 5, 8, 0, tzinfo=UTC),
    )

    assert task_run.task_type == AgentTaskType.EMAIL_REPLY
    assert task_run.status == AgentTaskRunStatus.FAILED
    assert "apps/agents unavailable" in (task_run.error_message or "")
    assert task_run.output_summary_json["error"]["type"] == "external_agent_unavailable"
    assert task_run.output_summary_json["writes_core_tables"] is False
    assert draft.agent_task_run_id == task_run.id
    assert draft.status == EmailReplyDraftStatus.FAILED
    assert draft.manual_review_required is True
    assert "apps/agents unavailable" in (draft.manual_review_reason or "")
    assert session.added == [task_run, draft]
    assert session.flushed is True


def test_email_reply_agent_service_rejects_wrong_email_reply_schema() -> None:
    class WrongSchemaRuntime(SuccessfulEmailReplyRuntime):
        def run_email_reply_response(self, **kwargs):
            response = super().run_email_reply_response(**kwargs)
            response["output"]["schema_version"] = "wrong"
            return response

    draft = make_draft()

    task_run = EmailReplyAgentService.run_email_reply_agent(
        draft,
        runtime=WrongSchemaRuntime(),
        context={},
        prompt={},
    )

    assert task_run.status == AgentTaskRunStatus.FAILED
    assert task_run.output_summary_json["external_agent_run_id"] == "44444444-4444-4444-4444-444444444444"
    assert task_run.output_summary_json["error"]["type"] == "schema_validation_error"
    assert draft.status == EmailReplyDraftStatus.FAILED
