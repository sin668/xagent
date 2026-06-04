from pathlib import Path

from app.models.enums import ChannelRiskLevel, CustomerGrade, CustomerType
from app.services.llm_lead_extraction import LLMLeadExtractionService


API_ROOT = Path(__file__).resolve().parents[1]


def sample_output(**overrides):
    payload = {
        "schema_version": "poc-ai-output-v1",
        "task_type": "lead_extraction",
        "source": {
            "source_url": "https://dealer.example/contact",
            "source_platform": "official_website",
            "channel_risk_level": "Medium",
            "search_keyword": "автосалон Москва",
            "collected_at": "2026-05-29T10:00:00+08:00",
            "operator": "codex-test",
        },
        "risk_blocked": False,
        "risk_block_reason": None,
        "lead": {
            "customer_name": "Example Auto",
            "country": "Russia",
            "city": "Moscow",
            "customer_type": "local_dealer_secondary_dealer",
            "business_scope": "Used cars and imported SUVs",
            "sells_used_or_imported_cars": "yes",
            "import_used_relevance": "high",
            "activity_signal": "Public website shows inventory and contact details",
            "scale_signal": "Multiple vehicle listings",
            "contacts": {
                "emails": ["sales@dealer.example"],
                "phones": ["+7 900 000 00 00"],
                "whatsapp": [],
                "telegram": [],
                "wechat": [],
                "website_forms": ["https://dealer.example/contact"],
            },
            "official_website": "https://dealer.example",
            "source_evidence": [
                {
                    "claim": "dealer_identity",
                    "evidence_text": "Used cars and imported SUVs",
                    "source_url": "https://dealer.example/contact",
                }
            ],
            "missing_fields": [],
        },
        "recommended_next_action": "send_to_grading",
        "touch_queue_allowed": False,
        "audit": {
            "model": "test-model",
            "prompt_version": "lead-extraction-v1",
            "input_saved": True,
            "output_saved": True,
            "executed_at": "2026-05-29T10:01:00+08:00",
        },
    }
    payload.update(overrides)
    return payload


def test_missing_fields_are_normalized_without_fabrication() -> None:
    output = sample_output()
    output["lead"]["customer_name"] = None
    output["lead"]["contacts"] = {}
    output["lead"]["source_evidence"] = [
        {"claim": "dealer_identity", "evidence_text": "Used cars", "source_url": "https://dealer.example/contact"}
    ]

    normalized = LLMLeadExtractionService.normalize_extraction_output(output)

    assert normalized["lead"]["customer_name"] == "Unknown"
    assert normalized["lead"]["contacts"]["emails"] == []
    assert normalized["lead"]["contacts"]["phones"] == []
    assert normalized["lead"]["missing_fields"] == []


def test_fabricated_contact_not_present_in_source_text_is_rejected() -> None:
    output = sample_output()
    public_text = "Example Auto sells used cars. Email sales@dealer.example"

    try:
        LLMLeadExtractionService.validate_extraction_output(
            output,
            public_text=public_text,
            expected_source_url="https://dealer.example/contact",
            channel_risk_level=ChannelRiskLevel.MEDIUM,
        )
    except ValueError as exc:
        assert "联系方式不在公开文本中" in str(exc)
    else:
        raise AssertionError("Fabricated phone should be rejected")


def test_high_or_forbidden_risk_is_blocked_before_staging() -> None:
    output = sample_output(risk_blocked=True, risk_block_reason="High risk policy review only")

    try:
        LLMLeadExtractionService.validate_extraction_output(
            output,
            public_text="sales@dealer.example +7 900 000 00 00",
            expected_source_url="https://dealer.example/contact",
            channel_risk_level=ChannelRiskLevel.HIGH,
        )
    except ValueError as exc:
        assert "High/Forbidden 来源不得写入 staging" in str(exc)
    else:
        raise AssertionError("High risk output should be blocked before staging")


def test_valid_output_maps_to_safe_staging_payload() -> None:
    output = sample_output()
    public_text = "Example Auto. Used cars and imported SUVs. sales@dealer.example +7 900 000 00 00 https://dealer.example/contact"

    staging_payload = LLMLeadExtractionService.build_staging_payload(
        output,
        public_text=public_text,
        expected_source_url="https://dealer.example/contact",
        channel_risk_level=ChannelRiskLevel.MEDIUM,
    )

    assert staging_payload["customer_name"] == "Example Auto"
    assert staging_payload["recommended_grade"] == CustomerGrade.WATCH
    assert staging_payload["recommended_reason"] == "等待 LLM 分级校验；本任务仅完成公开文本抽取。"
    assert any(
        item["method_type"] == "email"
        and item["value"] == "sales@dealer.example"
        and item["source_url"] == "https://dealer.example/contact"
        for item in staging_payload["contacts_json"]
    )
    assert "dealer_identity" in staging_payload["source_evidence"]


def test_customer_type_aliases_are_normalized_to_supported_enums() -> None:
    cases = {
        "未知": CustomerType.UNKNOWN.value,
        "individual": CustomerType.PERSONAL_BUYER.value,
        "dealership directory": CustomerType.DEALERSHIP_DIRECTORY.value,
        "marketplace": CustomerType.MARKETPLACE.value,
        "dealer": CustomerType.LOCAL_DEALER_SECONDARY_DEALER.value,
    }
    public_text = "Example Auto. Used cars and imported SUVs. sales@dealer.example +7 900 000 00 00 https://dealer.example/contact"

    for raw_value, expected in cases.items():
        output = sample_output()
        output["lead"]["customer_type"] = raw_value
        staging_payload = LLMLeadExtractionService.build_staging_payload(
            output,
            public_text=public_text,
            expected_source_url="https://dealer.example/contact",
            channel_risk_level=ChannelRiskLevel.MEDIUM,
        )

        assert staging_payload["customer_type"] == expected


def test_unknown_customer_type_with_contact_falls_back_to_unknown_instead_of_blocking() -> None:
    output = sample_output()
    output["lead"]["customer_type"] = "fleet leasing broker"
    public_text = "Example Auto. Used cars and imported SUVs. sales@dealer.example +7 900 000 00 00 https://dealer.example/contact"

    staging_payload = LLMLeadExtractionService.build_staging_payload(
        output,
        public_text=public_text,
        expected_source_url="https://dealer.example/contact",
        channel_risk_level=ChannelRiskLevel.MEDIUM,
    )

    assert staging_payload["customer_type"] == CustomerType.UNKNOWN.value


def test_staging_payload_truncates_string_fields_to_database_limits() -> None:
    output = sample_output()
    output["lead"]["customer_name"] = "Example Auto " + ("X" * 400)
    output["lead"]["country"] = "Russia " + ("Y" * 120)
    output["lead"]["city"] = "Moscow " + ("Z" * 160)
    output["lead"]["activity_signal"] = "Active dealer signal " + ("A" * 140)
    output["lead"]["import_used_relevance"] = "high relevance " + ("B" * 160)
    public_text = "Example Auto. Used cars and imported SUVs. sales@dealer.example +7 900 000 00 00 https://dealer.example/contact"

    staging_payload = LLMLeadExtractionService.build_staging_payload(
        output,
        public_text=public_text,
        expected_source_url="https://dealer.example/contact",
        channel_risk_level=ChannelRiskLevel.MEDIUM,
    )

    assert len(staging_payload["customer_name"]) <= 255
    assert len(staging_payload["country"]) <= 80
    assert len(staging_payload["city"]) <= 120
    assert len(staging_payload["activity_level"]) <= 80
    assert len(staging_payload["import_used_car_relevance"]) <= 120


def test_unknown_name_without_any_contact_is_rejected_before_staging() -> None:
    output = sample_output()
    output["lead"]["customer_name"] = "Unknown"
    output["lead"]["contacts"] = {
        "emails": [],
        "phones": [],
        "whatsapp": [],
        "telegram": [],
        "wechat": [],
        "website_forms": [],
    }
    public_text = "Public auto dealer directory without a concrete dealer contact."

    try:
        LLMLeadExtractionService.validate_extraction_output(
            output,
            public_text=public_text,
            expected_source_url="https://dealer.example/contact",
            channel_risk_level=ChannelRiskLevel.MEDIUM,
        )
    except ValueError as exc:
        assert "缺少客户名称和联系方式" in str(exc)
    else:
        raise AssertionError("Unknown lead without contacts should not be written to staging")


def test_equivalent_source_url_normalization_is_accepted_and_canonicalized() -> None:
    output = sample_output()
    output["source"]["source_url"] = "HTTPS://DEALER.EXAMPLE/contact/"
    output["lead"]["source_evidence"][0]["source_url"] = "https://dealer.example/contact/"
    public_text = "Example Auto. Used cars and imported SUVs. sales@dealer.example +7 900 000 00 00 https://dealer.example/contact"

    normalized = LLMLeadExtractionService.validate_extraction_output(
        output,
        public_text=public_text,
        expected_source_url="https://dealer.example/contact",
        channel_risk_level=ChannelRiskLevel.MEDIUM,
    )

    assert normalized["source"]["source_url"] == "https://dealer.example/contact"
    assert normalized["lead"]["source_evidence"][0]["source_url"] == "https://dealer.example/contact"


def test_llm_lead_extraction_api_contract_is_registered() -> None:
    main_py = (API_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    api_file = API_ROOT / "app" / "api" / "llm_lead_extraction.py"

    assert api_file.exists()
    assert "llm_lead_extraction_router" in main_py
    assert '@router.post("/run"' in api_file.read_text(encoding="utf-8")
