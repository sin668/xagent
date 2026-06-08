from __future__ import annotations

import json
from uuid import UUID

import httpx

from app.graphs.deep_enrichment import DeepEnrichmentGraphRunner, DeepEnrichmentGraphState, LLMDeepEnrichmentExtractor
from app.graphs.lead_cleanup import LLMLeadCleanupReviewer, LeadCleanupGraphRunner, LeadCleanupGraphState
from app.graphs.lead_extraction import LLMLeadFieldExtractor, LeadExtractionGraphRunner, LeadExtractionGraphState
from app.graphs.lead_grading import LLMLeadGradingExplainer, LeadGradingGraphRunner, LeadGradingGraphState
from app.graphs.source_discovery import LLMSourceDiscoveryQueryPlanner, SourceDiscoveryGraphRunner, SourceDiscoveryGraphState
from app.services.llm_client import LLMClient
from app.settings import AgentSettings


def build_settings() -> AgentSettings:
    return AgentSettings(
        agents_api_key="agent-secret",
        database_url="sqlite:///./agents.db",
        llm_provider="deepseek",
        llm_api_key="sk-test",
        llm_base_url="https://api.deepseek.com/v1",
        llm_default_model="deepseek-chat",
    )


def build_client(payload: dict | list) -> LLMClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
                "usage": {"total_tokens": 27},
            },
        )

    return LLMClient(settings=build_settings(), http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_source_discovery_default_runner_uses_llm_query_planner_without_core_writes() -> None:
    planner = LLMSourceDiscoveryQueryPlanner(
        llm_client=build_client({"queries": ["Russia used car importer public directory", "Moscow auto dealer export"]})
    )
    runner = SourceDiscoveryGraphRunner(llm_query_planner=planner)

    result = runner.run(
        SourceDiscoveryGraphState(
            discovery_run_id="run-1",
            market="Russia",
            channel_strategy={"keywords": ["used car importer"]},
        )
    )

    assert isinstance(SourceDiscoveryGraphRunner().llm_query_planner, LLMSourceDiscoveryQueryPlanner)
    assert "Russia used car importer public directory" in result.output.audit["llm_query_planner"]["queries"]
    assert result.output.audit["writes_core_tables"] is False


def test_lead_extraction_default_runner_uses_llm_fields_and_still_requires_source_evidence() -> None:
    extractor = LLMLeadFieldExtractor(
        llm_client=build_client(
            {
                "fields": {
                    "company_name": "Siberia Auto Trade",
                    "email": "sales@siberia-auto.example",
                    "city": "Novosibirsk",
                    "website": "https://siberia-auto.example",
                    "vehicle_interest": "Toyota Land Cruiser",
                }
            }
        )
    )
    runner = LeadExtractionGraphRunner(llm_field_extractor=extractor)

    result = runner.run(
        LeadExtractionGraphState(
            extraction_run_id="extract-1",
            source_url="https://siberia-auto.example",
            source_content=(
                "Siberia Auto Trade is located in Novosibirsk. "
                "Email sales@siberia-auto.example for Toyota Land Cruiser sourcing. "
                "Website https://siberia-auto.example"
            ),
        )
    )

    assert isinstance(LeadExtractionGraphRunner().llm_field_extractor, LLMLeadFieldExtractor)
    candidate = result.output.candidates[0]
    assert candidate.company_name.value == "Siberia Auto Trade"
    assert candidate.email.value == "sales@siberia-auto.example"
    assert candidate.city.value == "Novosibirsk"
    assert candidate.phone.value is None
    assert candidate.phone.evidence is None
    assert result.output.audit["llm_field_extractor"]["used"] is True
    assert result.output.audit["writes_core_tables"] is False


def test_lead_grading_default_runner_uses_llm_explainer_but_keeps_hard_rule_grade() -> None:
    extraction_runner = LeadExtractionGraphRunner(
        llm_field_extractor=LLMLeadFieldExtractor(llm_client=build_client({"fields": {"email": "watch@example.com"}}))
    )
    lead = extraction_runner.run(
        LeadExtractionGraphState(
            extraction_run_id="extract-2",
            source_url="https://watch.example",
            source_content="Watch Dealer exports cars. Contact watch@example.com.",
        )
    ).output.candidates[0]
    explainer = LLMLeadGradingExplainer(
        llm_client=build_client({"explanations": {"llm_signal_summary": "公开文本有邮箱，但来源风险需要人工复核。"}})
    )
    runner = LeadGradingGraphRunner(llm_explainer=explainer)

    result = runner.run(
        LeadGradingGraphState(
            grading_run_id="grade-1",
            extracted_lead=lead,
            risk_flags=["high_risk_source"],
        )
    )

    assert isinstance(LeadGradingGraphRunner().llm_explainer, LLMLeadGradingExplainer)
    suggestion = result.output.suggestions[0]
    assert suggestion.recommended_grade == "Watch"
    assert suggestion.status_route == "needs_manual_risk_review"
    assert suggestion.explanations["llm_signal_summary"] == "公开文本有邮箱，但来源风险需要人工复核。"
    assert result.output.audit["writes_core_tables"] is False


def test_deep_enrichment_default_runner_uses_llm_extractor_and_filters_candidates_by_evidence() -> None:
    lead_id = UUID("11111111-1111-1111-1111-111111111111")
    extractor = LLMDeepEnrichmentExtractor(
        llm_client=build_client(
            {
                "field_candidates": [
                    {
                        "field_name": "whatsapp",
                        "candidate_value": "+7 999 111 22 33",
                        "source_type": "ai_public_source",
                        "source_url": "https://dealer.example/contact",
                        "evidence_note": "页面写有 WhatsApp +7 999 111 22 33。",
                        "confidence_score": 0.81,
                    },
                    {
                        "field_name": "telegram",
                        "candidate_value": "@invented",
                        "source_type": "ai_public_source",
                        "source_url": "https://dealer.example/contact",
                        "evidence_note": "页面写有 Telegram @invented。",
                        "confidence_score": 0.7,
                    },
                ]
            }
        )
    )
    runner = DeepEnrichmentGraphRunner(
        llm_extractor=extractor,
        search_tool=StaticSearchTool(
            [
                {
                    "url": "https://dealer.example/contact",
                    "title": "Contact",
                    "text": "Dealer contact page. WhatsApp +7 999 111 22 33 for sourcing.",
                }
            ]
        ),
    )

    result = runner.run(
        DeepEnrichmentGraphState(
            agent_run_id=lead_id,
            staging_lead_id=lead_id,
            lead_snapshot={"customer_name": "Dealer", "city": "Moscow", "country": "Russia"},
            missing_fields=["whatsapp", "telegram"],
        )
    )

    assert isinstance(DeepEnrichmentGraphRunner().llm_extractor, LLMDeepEnrichmentExtractor)
    assert [item.field_name for item in result.output.field_candidates] == ["whatsapp"]
    assert result.output.audit["llm_extractor"]["used"] is True
    assert result.output.audit["writes_core_tables"] is False


def test_lead_cleanup_default_runner_uses_llm_reviewer_without_auto_cleanup() -> None:
    lead_id = UUID("22222222-2222-2222-2222-222222222222")
    reviewer = LLMLeadCleanupReviewer(
        llm_client=build_client(
            {
                "suggestions": [
                    {
                        "staging_lead_id": str(lead_id),
                        "suggestion_type": "needs_manual_review",
                        "target_lead_id": None,
                        "confidence_score": 0.66,
                        "reason": "LLM 发现 Invalid 线索仍有邮箱，建议人工复核是否误杀。",
                        "evidence_json": {"email": "ops@example.com"},
                        "recommended_action": "人工复核后决定是否恢复到 Watch 或保留 Invalid",
                    }
                ]
            }
        )
    )
    runner = LeadCleanupGraphRunner(llm_reviewer=reviewer)

    result = runner.run(
        LeadCleanupGraphState(
            cleanup_run_id=lead_id,
            leads=[
                {
                    "staging_lead_id": str(lead_id),
                    "customer_name": "Ops Dealer",
                    "recommended_grade": "Invalid",
                    "email": "ops@example.com",
                }
            ],
        )
    )

    assert isinstance(LeadCleanupGraphRunner().llm_reviewer, LLMLeadCleanupReviewer)
    assert any(item.reason.startswith("LLM 发现") for item in result.output.suggestions)
    assert result.output.audit["llm_reviewer"]["used"] is True
    assert result.output.audit["writes_core_tables"] is False
    assert result.output.audit["auto_execute_cleanup"] is False


class StaticSearchTool:
    def __init__(self, results: list[dict]) -> None:
        self.results = results

    def search(self, queries: list[str]) -> list[dict]:
        return self.results
