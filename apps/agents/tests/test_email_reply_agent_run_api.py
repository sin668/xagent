from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.agent_runs import get_db_session
from app.db.base import Base
from app.main import app
from app.schemas.email_reply import EmailReplyAgentOutput, EmailReplyKnowledgeHit
from app.settings import get_settings


INTERNAL_API_KEY = "test-email-reply-agent-key"


class FakeEmailReplyGraphResult:
    def __init__(self) -> None:
        self.executed_nodes = [
            "load_context",
            "retrieve_knowledge",
            "draft_reply",
            "schema_validation",
            "auto_send_check",
            "route_decision",
        ]
        self.output = EmailReplyAgentOutput(
            schema_version="email-reply-v1",
            reply_language="ru",
            detected_language="ru",
            suggested_subject="Toyota sourcing",
            suggested_body="Здравствуйте, можем отправить базовую информацию.",
            knowledge_hits=[
                EmailReplyKnowledgeHit(
                    knowledge_item_id=str(uuid4()),
                    title="Fixed FAQ",
                    version="v1",
                    similarity_score=0.94,
                    evidence_note="Approved fixed FAQ wording.",
                )
            ],
            risk_flags=[],
            auto_send_allowed=False,
            manual_review_required=True,
            next_action="hold_for_manual_review",
            audit={
                "writes_core_tables": False,
                "route_decision": "hold_for_manual_review",
                "route_reasons": ["test_default_manual_review"],
            },
        )


class FakeEmailReplyGraphRunner:
    calls = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    def run(self, state):
        self.calls.append(state)
        return FakeEmailReplyGraphResult()


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTS_API_KEY", INTERNAL_API_KEY)
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{tmp_path / 'agents-test.db'}")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def override_db_session():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_db_session
    monkeypatch.setattr("app.api.agent_runs.EmailReplyGraphRunner", FakeEmailReplyGraphRunner)
    FakeEmailReplyGraphRunner.calls = []
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def email_reply_payload() -> dict:
    return {
        "request_id": str(uuid4()),
        "trigger_source": "manual_api",
        "agent_mode": "dry_run",
        "input": {
            "thread_id": str(uuid4()),
            "message_id": str(uuid4()),
            "customer_id": str(uuid4()),
            "draft_id": str(uuid4()),
            "context": {},
            "prompt": {"version": "email-reply-v1"},
            "options": {"language": "ru", "dry_run": True},
        },
        "options": {"dry_run": True, "max_retries": 1},
    }


def test_health_is_public_without_internal_api_key(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "vehicle-leads-agents"


def test_email_reply_agent_run_requires_internal_api_key(client: TestClient) -> None:
    response = client.post("/agent-runs/email-reply", json=email_reply_payload())

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing agents API key"


def test_email_reply_agent_run_creates_run_and_get_returns_result(client: TestClient) -> None:
    payload = email_reply_payload()
    response = client.post(
        "/agent-runs/email-reply",
        headers={"X-Agents-Api-Key": INTERNAL_API_KEY},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    run_id = UUID(body["agent_service_run_id"])
    assert body["status"] == "succeeded"
    assert body["agent_type"] == "email_reply"
    assert body["audit"]["writes_core_tables"] is False
    assert body["audit"]["executed_nodes"] == [
        "load_context",
        "retrieve_knowledge",
        "draft_reply",
        "schema_validation",
        "auto_send_check",
        "route_decision",
    ]
    assert body["output"]["schema_version"] == "email-reply-v1"
    assert FakeEmailReplyGraphRunner.calls[0].thread_id == UUID(payload["input"]["thread_id"])

    detail = client.get(f"/agent-runs/{run_id}", headers={"X-Agents-Api-Key": INTERNAL_API_KEY})

    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["agent_service_run_id"] == str(run_id)
    assert detail_body["status"] == "succeeded"
    assert detail_body["output"]["suggested_subject"] == "Toyota sourcing"


def test_get_agent_run_returns_404_for_missing_run(client: TestClient) -> None:
    response = client.get(f"/agent-runs/{uuid4()}", headers={"X-Agents-Api-Key": INTERNAL_API_KEY})

    assert response.status_code == 404
