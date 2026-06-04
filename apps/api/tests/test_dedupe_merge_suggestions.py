from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.services.staging_leads import StagingLeadService


API_ROOT = Path(__file__).resolve().parents[1]


def _lead(**overrides):
    payload = {
        "id": uuid4(),
        "customer_name": " Auto City Moscow ",
        "city": "Moscow",
        "contacts_json": [{"type": "email", "value": " Sales@Dealer.Example.RU "}],
        "candidate_url": SimpleNamespace(url="https://dealer.example.ru/catalog?utm=1", url_hash="abc123"),
        "source_evidence": "官网公开展示邮箱和库存。",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_dedupe_api_contract_and_response_fields_exist() -> None:
    api_text = (API_ROOT / "app" / "api" / "staging_leads.py").read_text(encoding="utf-8")
    schema_text = (API_ROOT / "app" / "schemas" / "staging_leads.py").read_text(encoding="utf-8")

    assert '@router.get("/{lead_id}/duplicates"' in api_text
    assert '@router.post("/{lead_id}/duplicates/resolve"' in api_text
    assert "duplicate_signals" in schema_text
    assert "DuplicateSignalResponse" in schema_text


def test_dedupe_keys_cover_strong_suspected_and_source_duplicate_rules() -> None:
    lead = _lead()

    keys = StagingLeadService.build_duplicate_keys(lead)

    assert keys["normalized_name"] == "auto city moscow"
    assert keys["contact_hash"]
    assert keys["strong_key"] == f"auto city moscow::{keys['contact_hash']}"
    assert keys["suspected_key"] == "auto city moscow::moscow::dealer.example.ru"
    assert keys["source_url_hash"] == "abc123"


def test_duplicate_signals_mark_strong_duplicates_as_blocking_and_suspected_as_manual_review() -> None:
    signals = StagingLeadService.build_duplicate_signal_summary(
        strong_candidates=[{"target_type": "core_customer", "target_id": "c1", "reason": "同名同邮箱"}],
        suspected_candidates=[{"target_type": "staging_lead", "target_id": "s2", "reason": "同名同城同域名"}],
        source_candidates=[{"target_type": "lead_source", "target_id": "src1", "reason": "URL hash相同"}],
    )

    assert signals["has_strong_duplicate"] is True
    assert signals["blocks_promotion"] is True
    assert signals["requires_manual_review"] is True
    assert signals["strong_duplicates"][0]["reason"] == "同名同邮箱"
    assert signals["suspected_duplicates"][0]["reason"] == "同名同城同域名"
    assert signals["source_duplicates"][0]["reason"] == "URL hash相同"


def test_strong_duplicate_error_blocks_promotion_without_deleting_evidence() -> None:
    signals = StagingLeadService.build_duplicate_signal_summary(
        strong_candidates=[{"target_type": "core_customer", "target_id": "c1", "reason": "同名同联系方式"}],
        suspected_candidates=[],
        source_candidates=[],
    )

    try:
        StagingLeadService.raise_if_strong_duplicate(signals)
    except ValueError as exc:
        assert "强重复线索不得晋级 core" in str(exc)
        assert "同名同联系方式" in str(exc)
    else:
        raise AssertionError("strong duplicate should block promotion")


def test_merge_resolution_payload_preserves_source_evidence_and_dnc_boundary() -> None:
    lead = _lead(source_evidence="公开官网证据A")
    payload = StagingLeadService.build_merge_resolution_payload(
        lead,
        target_customer_id=uuid4(),
        actor="ops-anna",
        source_url="https://dealer.example.ru",
        evidence_note="公开官网证据A",
    )

    assert payload["review_status"] == "duplicate"
    assert payload["queue_status"] == "not_eligible"
    assert payload["lead_source"]["evidence_note"] == "公开官网证据A"
    assert payload["lead_source"]["source_url"] == "https://dealer.example.ru"
    assert payload["review_log"]["action"] == "merge_duplicate_staging_lead"
    assert payload["review_log"]["reviewer"] == "ops-anna"
