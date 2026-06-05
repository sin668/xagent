from uuid import uuid4

from app.graphs.email_reply import EmailReplyGraphRunner, EmailReplyGraphState


class FakeRouteApiClient:
    def __init__(self, decision: dict) -> None:
        self.decision = decision
        self.auto_send_check_calls = []

    def load_context(self, envelope):
        return {
            "customer": {
                "name": "Moscow Auto Dealer",
                "is_whitelisted": True,
                "grade": "A",
                "status": "ready_for_sales",
                "do_not_contact": False,
            },
            "inbound_message": {
                "language": "ru",
                "body_text": "Нужна базовая информация по Toyota.",
                "risk_flags": [],
                "sensitive_topics": [],
            },
            "audit_summary": {"included_sections": ["customer", "inbound_message"]},
        }

    def retrieve_knowledge(self, **kwargs):
        return {
            "items": [
                {
                    "knowledge_item_id": str(uuid4()),
                    "title": "Fixed FAQ",
                    "version": "v1",
                    "similarity_score": 0.94,
                    "evidence_note": "Approved fixed FAQ wording.",
                }
            ],
            "total": 1,
            "rejection_reason": None,
        }

    def auto_send_check(self, *, envelope, output, context, knowledge_hits, options, dry_run):
        self.auto_send_check_calls.append(
            {
                "envelope": envelope,
                "output": output,
                "context": context,
                "knowledge_hits": knowledge_hits,
                "options": options,
                "dry_run": dry_run,
            }
        )
        return self.decision


class SafeAutoSendDrafter:
    def draft(self, *, context, knowledge_hits, prompt, options):
        return {
            "schema_version": "email-reply-v1",
            "reply_language": "ru",
            "detected_language": "ru",
            "suggested_subject": "Toyota sourcing",
            "suggested_body": "Здравствуйте, можем отправить базовую информацию по процессу.",
            "knowledge_hits": [item.model_dump(mode="json") for item in knowledge_hits],
            "risk_flags": [],
            "auto_send_allowed": True,
            "manual_review_required": False,
            "next_action": "auto_send_candidate",
            "audit": {"writes_core_tables": False},
        }


def run_with_decision(decision: dict):
    api_client = FakeRouteApiClient(decision=decision)
    runner = EmailReplyGraphRunner(api_client=api_client, llm_drafter=SafeAutoSendDrafter())
    result = runner.run(
        EmailReplyGraphState(
            request_id=uuid4(),
            thread_id=uuid4(),
            message_id=uuid4(),
            customer_id=uuid4(),
            draft_id=uuid4(),
            options={
                "language": "ru",
                "auto_send_candidate": True,
                "dry_run": True,
                "business_scene": "fixed_faq",
                "scene_risk_level": "low",
            },
        )
    )
    return api_client, result


def test_email_reply_agent_routes_auto_send_decision_from_apps_api_without_sending() -> None:
    api_client, result = run_with_decision(
        {
            "route": "auto_send",
            "auto_send_allowed": True,
            "manual_review_required": False,
            "manual_review_reason": None,
            "reasons": ["apps_api_allowed_auto_send"],
            "dry_run": True,
            "send_triggered": False,
        }
    )

    assert result.executed_nodes == [
        "load_context",
        "retrieve_knowledge",
        "draft_reply",
        "schema_validation",
        "auto_send_check",
        "route_decision",
    ]
    assert len(api_client.auto_send_check_calls) == 1
    assert api_client.auto_send_check_calls[0]["dry_run"] is True
    assert result.output.auto_send_allowed is True
    assert result.output.manual_review_required is False
    assert result.output.next_action == "auto_send_candidate"
    assert result.output.audit["route_decision"] == "auto_send"
    assert result.output.audit["send_triggered"] is False


def test_email_reply_agent_routes_hold_for_manual_review_with_reasons() -> None:
    _, result = run_with_decision(
        {
            "route": "hold_for_manual_review",
            "auto_send_allowed": False,
            "manual_review_required": True,
            "manual_review_reason": "未满足自动发送准入条件，进入人工确认。",
            "reasons": ["not_first_touch"],
            "dry_run": True,
            "send_triggered": False,
        }
    )

    assert result.output.auto_send_allowed is False
    assert result.output.manual_review_required is True
    assert result.output.next_action == "hold_for_manual_review"
    assert result.output.audit["route_decision"] == "hold_for_manual_review"
    assert result.output.audit["route_reasons"] == ["not_first_touch"]


def test_email_reply_agent_routes_block_with_structured_reasons() -> None:
    _, result = run_with_decision(
        {
            "route": "block",
            "auto_send_allowed": False,
            "manual_review_required": True,
            "manual_review_reason": "命中硬拦截规则，禁止自动发送。",
            "reasons": ["customer_do_not_contact"],
            "block_reasons": [
                {"code": "customer_do_not_contact", "message": "客户已标记勿扰或 DNC。", "severity": "critical"}
            ],
            "dry_run": True,
            "send_triggered": False,
        }
    )

    assert result.output.auto_send_allowed is False
    assert result.output.manual_review_required is True
    assert result.output.next_action == "block"
    assert result.output.audit["route_decision"] == "block"
    assert result.output.audit["block_reasons"][0]["code"] == "customer_do_not_contact"
