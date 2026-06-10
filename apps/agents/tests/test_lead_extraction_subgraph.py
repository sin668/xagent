import pytest
from pydantic import ValidationError

from app.graphs.lead_extraction import (
    LEAD_EXTRACTION_NODE_SEQUENCE,
    LLMLeadFieldExtractor,
    LeadExtractionGraphRunner,
    LeadExtractionGraphState,
)
from app.schemas.lead_extraction import LeadExtractionAgentOutput


PUBLIC_SOURCE_TEXT = """
Auto City Dubai exports used Toyota Land Cruiser and Lexus LX vehicles to overseas buyers.
Contact: sales@autocity.example, +971 50 123 4567.
Located in Dubai, United Arab Emirates. Website: https://autocity.example.
The company says it can arrange export documentation and shipping.
"""


class StubLeadFieldExtractor(LLMLeadFieldExtractor):
    def __init__(self, output):
        self.output = output
        self.last_audit = {"used": True, "provider": "stub", "model": "stub"}

    def extract(self, *, source_url: str, source_content: str):
        return self.output


def test_lead_extraction_graph_declares_required_node_sequence() -> None:
    assert LEAD_EXTRACTION_NODE_SEQUENCE == (
        "load_source_content",
        "extract_candidate_fields",
        "map_field_evidence",
        "validate_required_evidence",
        "output_shadow_staging_lead",
    )


def test_lead_extraction_graph_outputs_structured_candidate_with_evidence_without_core_writes() -> None:
    runner = LeadExtractionGraphRunner()
    state = LeadExtractionGraphState(
        extraction_run_id="22222222-2222-2222-2222-222222222222",
        source_url="https://autocity.example",
        source_content=PUBLIC_SOURCE_TEXT,
        agent_mode="shadow",
    )

    result = runner.run(state)

    assert result.output.schema_version == "phase4.agent.lead_extraction.v1"
    assert result.output.extraction_run_id == "22222222-2222-2222-2222-222222222222"
    assert result.output.agent_mode == "shadow"
    assert result.executed_nodes == list(LEAD_EXTRACTION_NODE_SEQUENCE)
    assert len(result.output.candidates) == 1

    candidate = result.output.candidates[0]
    assert candidate.company_name.value == "Auto City Dubai"
    assert candidate.company_name.evidence.reference == "source_content"
    assert "Auto City Dubai exports" in candidate.company_name.evidence.quote
    assert candidate.email.value == "sales@autocity.example"
    assert candidate.phone.value == "+971 50 123 4567"
    assert candidate.country.value == "United Arab Emirates"
    assert candidate.city.value == "Dubai"
    assert candidate.vehicle_interest.value == "Toyota Land Cruiser, Lexus LX"
    assert candidate.export_intent.value == "arrange export documentation and shipping"
    assert candidate.website.value == "https://autocity.example"
    assert candidate.audit_status == "shadow_only"

    assert result.output.audit["writes_core_tables"] is False
    assert result.output.audit["output_table"] == "shadow_staging_lead_candidates"
    assert "staging_leads" not in result.output.audit.get("written_tables", [])


def test_lead_extraction_graph_keeps_missing_reason_for_absent_key_fields() -> None:
    runner = LeadExtractionGraphRunner()
    state = LeadExtractionGraphState(
        extraction_run_id="22222222-2222-2222-2222-222222222222",
        source_url="https://minimal.example",
        source_content="Minimal Motors sells used vehicles. Website: https://minimal.example.",
        agent_mode="shadow",
    )

    result = runner.run(state)
    candidate = result.output.candidates[0]

    assert candidate.company_name.value == "Minimal Motors"
    assert candidate.email.value is None
    assert candidate.email.missing_reason == "源文本未提供 email。"
    assert candidate.phone.value is None
    assert candidate.phone.missing_reason == "源文本未提供 phone。"
    assert candidate.export_intent.value is None
    assert candidate.export_intent.missing_reason == "源文本未提供 export_intent。"
    assert result.output.validation_errors == []


def test_lead_extraction_graph_accepts_active_mode_and_rejects_empty_content() -> None:
    runner = LeadExtractionGraphRunner()

    active_result = runner.run(
        LeadExtractionGraphState(
            extraction_run_id="22222222-2222-2222-2222-222222222222",
            source_url="https://autocity.example",
            source_content=PUBLIC_SOURCE_TEXT,
            agent_mode="active",
        )
    )
    assert active_result.output.agent_mode == "active"

    with pytest.raises(ValueError, match="Lead Extraction 需要输入公开来源文本或来源内容"):
        runner.run(
            LeadExtractionGraphState(
                extraction_run_id="22222222-2222-2222-2222-222222222222",
                source_url="https://autocity.example",
                source_content="",
                agent_mode="shadow",
            )
        )


def test_lead_extraction_output_schema_rejects_field_without_evidence_or_missing_reason() -> None:
    with pytest.raises(ValidationError) as exc_info:
        LeadExtractionAgentOutput.model_validate(
            {
                "schema_version": "phase4.agent.lead_extraction.v1",
                "extraction_run_id": "22222222-2222-2222-2222-222222222222",
                "agent_mode": "shadow",
                "candidates": [
                    {
                        "source_url": "https://invalid.example",
                        "company_name": {"field_name": "company_name", "value": "Invalid Motors"},
                        "email": {"field_name": "email", "value": None, "missing_reason": "源文本未提供 email。"},
                        "phone": {"field_name": "phone", "value": None, "missing_reason": "源文本未提供 phone。"},
                        "country": {"field_name": "country", "value": None, "missing_reason": "源文本未提供 country。"},
                        "city": {"field_name": "city", "value": None, "missing_reason": "源文本未提供 city。"},
                        "vehicle_interest": {
                            "field_name": "vehicle_interest",
                            "value": None,
                            "missing_reason": "源文本未提供 vehicle_interest。",
                        },
                        "export_intent": {
                            "field_name": "export_intent",
                            "value": None,
                            "missing_reason": "源文本未提供 export_intent。",
                        },
                        "website": {"field_name": "website", "value": None, "missing_reason": "源文本未提供 website。"},
                    }
                ],
                "audit": {"writes_core_tables": False},
            }
        )

    assert "字段 company_name 必须包含证据引用或缺失原因" in str(exc_info.value)


def test_lead_extraction_graph_collects_all_public_contact_methods_from_one_source() -> None:
    source_text = """
    Avtogermes sells new and used cars in Moscow, Russia. Website: https://www.avtogermes.ru/.
    Contact sales: info@avtogermes.ru, sale@avtogermes.ru.
    Phones: +7 495 777 7777 and +7 495 223 3333.
    """
    runner = LeadExtractionGraphRunner(llm_field_extractor=StubLeadFieldExtractor({}))

    result = runner.run(
        LeadExtractionGraphState(
            extraction_run_id="22222222-2222-2222-2222-222222222222",
            source_url="https://www.avtogermes.ru/",
            source_content=source_text,
            agent_mode="active",
        )
    )

    candidate = result.output.candidates[0]
    assert candidate.email.value == "info@avtogermes.ru"
    assert candidate.phone.value == "+7 495 777 7777"
    assert [contact.value for contact in candidate.contacts] == [
        "info@avtogermes.ru",
        "sale@avtogermes.ru",
        "+7 495 777 7777",
        "+7 495 223 3333",
    ]
    assert [contact.contact_type for contact in candidate.contacts] == ["email", "email", "phone", "phone"]


def test_lead_extraction_graph_accepts_llm_leads_array_and_outputs_multiple_candidates() -> None:
    source_text = """
    Alpha Motors exports Toyota Land Cruiser from Dubai. Email alpha@example.com. Phone +971 50 111 1111.
    Beta Cars exports Lexus LX from Dubai. Email beta@example.com. Phone +971 50 222 2222.
    """
    runner = LeadExtractionGraphRunner(
        llm_field_extractor=StubLeadFieldExtractor(
            {
                "leads": [
                    {
                        "fields": {
                            "company_name": "Alpha Motors",
                            "email": "alpha@example.com",
                            "phone": "+971 50 111 1111",
                            "country": "United Arab Emirates",
                            "city": "Dubai",
                            "vehicle_interest": "Toyota Land Cruiser",
                            "export_intent": "exports Toyota Land Cruiser",
                            "website": "https://alpha.example",
                        },
                        "contacts": [
                            {"type": "email", "value": "alpha@example.com"},
                            {"type": "phone", "value": "+971 50 111 1111"},
                        ],
                    },
                    {
                        "fields": {
                            "company_name": "Beta Cars",
                            "email": "beta@example.com",
                            "phone": "+971 50 222 2222",
                            "country": "United Arab Emirates",
                            "city": "Dubai",
                            "vehicle_interest": "Lexus LX",
                            "export_intent": "exports Lexus LX",
                            "website": "https://beta.example",
                        },
                        "contacts": [
                            {"type": "email", "value": "beta@example.com"},
                            {"type": "phone", "value": "+971 50 222 2222"},
                        ],
                    },
                ]
            }
        )
    )

    result = runner.run(
        LeadExtractionGraphState(
            extraction_run_id="22222222-2222-2222-2222-222222222222",
            source_url="https://market.example/dealers",
            source_content=source_text,
            agent_mode="active",
        )
    )

    assert [candidate.company_name.value for candidate in result.output.candidates] == ["Alpha Motors", "Beta Cars"]
    assert [candidate.email.value for candidate in result.output.candidates] == ["alpha@example.com", "beta@example.com"]
    assert result.output.audit["candidate_count"] == 2
