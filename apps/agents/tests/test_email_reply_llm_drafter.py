import httpx

from app.graphs.email_reply import LLMEmailReplyDrafter
from app.schemas.email_reply import EmailReplyKnowledgeHit
from app.services.llm_client import LLMClient
from app.settings import AgentSettings


def test_email_reply_llm_drafter_uses_llm_client_and_preserves_audit_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "schema_version": "email-reply-v1",
                              "reply_language": "ru",
                              "detected_language": "ru",
                              "suggested_subject": "Toyota sourcing",
                              "suggested_body": "Здравствуйте, можем отправить базовую информацию.",
                              "knowledge_hits": [],
                              "risk_flags": [],
                              "auto_send_allowed": false,
                              "manual_review_required": true,
                              "next_action": "hold_for_manual_review",
                              "audit": {"writes_core_tables": false}
                            }
                            """,
                        }
                    }
                ],
                "usage": {"total_tokens": 33},
            },
        )

    settings = AgentSettings(
        agents_api_key="agent-secret",
        database_url="sqlite:///./agents.db",
        llm_api_key="sk-test",
        llm_base_url="https://api.deepseek.com/v1",
        llm_email_reply_model="deepseek-email",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        drafter = LLMEmailReplyDrafter(llm_client=LLMClient(settings=settings, http_client=http_client))
        draft = drafter.draft(
            context={
                "customer": {"name": "Moscow Auto Dealer"},
                "inbound_message": {"language": "ru", "body_text": "Нужна Toyota."},
            },
            knowledge_hits=[
                EmailReplyKnowledgeHit(
                    knowledge_item_id="k1",
                    title="Fixed FAQ",
                    version="v1",
                    similarity_score=0.91,
                    evidence_note="Approved FAQ.",
                )
            ],
            prompt={"version": "email-reply-v1"},
            options={"language": "ru"},
        )

    assert draft["schema_version"] == "email-reply-v1"
    assert draft["suggested_subject"] == "Toyota sourcing"
    assert draft["audit"]["writes_core_tables"] is False
    assert draft["audit"]["llm_provider"] == "deepseek"
    assert draft["audit"]["llm_model"] == "deepseek-email"
    assert draft["audit"]["token_usage"] == {"total_tokens": 33}


def test_email_reply_llm_drafter_falls_back_to_manual_review_when_llm_is_not_configured() -> None:
    settings = AgentSettings(
        agents_api_key="agent-secret",
        database_url="sqlite:///./agents.db",
        llm_api_key="",
        llm_base_url="https://api.deepseek.com/v1",
    )
    drafter = LLMEmailReplyDrafter(llm_client=LLMClient(settings=settings))

    draft = drafter.draft(context={}, knowledge_hits=[], prompt={}, options={"language": "ru"})

    assert draft["suggested_subject"] == "Unknown"
    assert draft["suggested_body"] == "Unknown"
    assert draft["auto_send_allowed"] is False
    assert draft["manual_review_required"] is True
    assert draft["next_action"] == "hold_for_manual_review"
    assert draft["audit"]["llm_error"]["type"] == "configuration_error"
    assert draft["audit"]["writes_core_tables"] is False
