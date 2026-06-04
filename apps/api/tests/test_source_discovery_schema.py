import copy

import pytest

from app.services.source_discovery_schema import SourceDiscoverySchemaService, SourceDiscoveryValidationError


def valid_output() -> dict:
    return {
        "task_type": "SOURCE_DISCOVERY",
        "country": "Russia",
        "city": "Moscow",
        "channel_strategy": "official_website_public_directory_search_engine",
        "candidates": [
            {
                "source_url": "https://example.com/dealers",
                "platform": "official_website",
                "channel_name": "dealer_directory",
                "country": "Russia",
                "city": "Moscow",
                "risk_level": "Low",
                "discovery_method": "keyword_search",
                "discovery_query": "автосалон импорт авто Москва",
                "discovery_reason": "公开页面展示车辆经销商目录。",
                "evidence_note": "公开页面包含 dealer、auto sales 和 contact 相关信息。",
                "evidence_links": ["https://example.com/dealers"],
                "confidence_score": 0.72,
                "recommended_review_status": "auto_approved",
                "approved_for_extraction": True,
            }
        ],
        "blocked_candidates": [
            {
                "source_url": "https://blocked.example.com",
                "risk_level": "Forbidden",
                "blocked_reason": "需要登录或违反渠道规则。",
            }
        ],
    }


def test_valid_source_discovery_output_passes_and_preserves_values() -> None:
    output = valid_output()

    result = SourceDiscoverySchemaService.validate_output(output)

    assert result.valid is True
    assert result.error is None
    assert result.normalized_output == output
    assert result.candidates[0]["source_url"] == "https://example.com/dealers"
    assert result.candidates[0]["approved_for_extraction"] is True
    assert result.blocked_candidates[0]["approved_for_extraction"] is False
    assert result.blocked_candidates[0]["blocked_reason"] == "需要登录或违反渠道规则。"


def test_unknown_null_and_empty_array_are_preserved_without_fabrication() -> None:
    output = valid_output()
    output["city"] = None
    output["candidates"][0]["city"] = None
    output["candidates"][0]["discovery_query"] = "Unknown"
    output["candidates"][0]["evidence_links"] = []
    output["blocked_candidates"] = []

    result = SourceDiscoverySchemaService.validate_output(output)

    assert result.normalized_output["city"] is None
    assert result.candidates[0]["city"] is None
    assert result.candidates[0]["discovery_query"] == "Unknown"
    assert result.candidates[0]["evidence_links"] == []
    assert result.blocked_candidates == []


@pytest.mark.parametrize(
    ("field_name", "expected_message"),
    [
        ("source_url", "source_url"),
        ("platform", "platform"),
        ("risk_level", "risk_level"),
        ("discovery_reason", "discovery_reason"),
        ("evidence_note", "evidence_note"),
    ],
)
def test_candidate_missing_required_fields_fails(field_name: str, expected_message: str) -> None:
    output = valid_output()
    output["candidates"][0].pop(field_name)

    with pytest.raises(SourceDiscoveryValidationError) as exc_info:
        SourceDiscoverySchemaService.validate_output(output)

    assert expected_message in str(exc_info.value)
    assert exc_info.value.error_type == "schema_validation_error"


def test_invalid_candidate_risk_level_fails() -> None:
    output = valid_output()
    output["candidates"][0]["risk_level"] = "Critical"

    with pytest.raises(SourceDiscoveryValidationError) as exc_info:
        SourceDiscoverySchemaService.validate_output(output)

    assert "risk_level" in str(exc_info.value)
    assert "Critical" in str(exc_info.value)


def test_forbidden_candidate_must_not_enter_candidates() -> None:
    output = valid_output()
    output["candidates"][0]["risk_level"] = "Forbidden"

    with pytest.raises(SourceDiscoveryValidationError) as exc_info:
        SourceDiscoverySchemaService.validate_output(output)

    assert "Forbidden" in str(exc_info.value)
    assert "blocked_candidates" in str(exc_info.value)


def test_top_level_required_fields_are_validated() -> None:
    output = valid_output()
    output.pop("channel_strategy")

    with pytest.raises(SourceDiscoveryValidationError) as exc_info:
        SourceDiscoverySchemaService.validate_output(output)

    assert "channel_strategy" in str(exc_info.value)


def test_blocked_candidates_are_never_auto_extractable() -> None:
    output = valid_output()
    output["blocked_candidates"][0]["approved_for_extraction"] = True

    result = SourceDiscoverySchemaService.validate_output(output)

    assert result.blocked_candidates[0]["approved_for_extraction"] is False
    assert "approved_for_extraction" not in result.normalized_output["blocked_candidates"][0]


def test_validation_does_not_mutate_input() -> None:
    output = valid_output()
    original = copy.deepcopy(output)

    SourceDiscoverySchemaService.validate_output(output)

    assert output == original
