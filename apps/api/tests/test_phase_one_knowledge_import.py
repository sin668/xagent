from pathlib import Path

from app.models.enums import KnowledgeItemStatus, KnowledgeReviewStatus
from app.services.knowledge_import import KnowledgeImportService


API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]


def test_phase_one_import_specs_cover_required_collections() -> None:
    specs = KnowledgeImportService.phase_one_import_specs(REPO_ROOT)
    collection_names = {spec.collection_name for spec in specs}

    assert {
        "channel_sop",
        "faq",
        "script_template",
        "keyword_library",
        "vehicle_knowledge",
        "compliance_rules",
        "failed_cases",
    }.issubset(collection_names)


def test_each_import_spec_has_required_knowledge_fields_and_source_ref() -> None:
    specs = KnowledgeImportService.phase_one_import_specs(REPO_ROOT)

    assert specs
    for spec in specs:
        assert spec.title
        assert spec.body
        assert spec.language
        assert spec.country == "Russia"
        assert spec.source_ref
        assert spec.status == KnowledgeItemStatus.DRAFT
        assert spec.review_status == KnowledgeReviewStatus.PENDING
        assert spec.rag_eligible is False


def test_script_template_import_preserves_forbidden_promises_and_opt_out_path() -> None:
    specs = KnowledgeImportService.phase_one_import_specs(REPO_ROOT)
    script_items = [spec for spec in specs if spec.collection_name == "script_template"]

    assert script_items
    body = "\n".join(item.body for item in script_items)
    assert "禁止承诺点" in body
    assert "拒绝联系" in body


def test_phase_one_import_payload_is_idempotent_by_collection_title_source() -> None:
    specs = KnowledgeImportService.phase_one_import_specs(REPO_ROOT)
    keys = [KnowledgeImportService.import_spec_key(spec) for spec in specs]

    assert len(keys) == len(set(keys))
    assert all("::" in key for key in keys)


def test_phase_one_import_api_contract_exists() -> None:
    api_file = API_ROOT / "app" / "api" / "knowledge.py"

    text = api_file.read_text(encoding="utf-8")
    assert '@router.post("/import/phase-one"' in text

