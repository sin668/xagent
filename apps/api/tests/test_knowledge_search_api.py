from pathlib import Path
from types import SimpleNamespace

from app.models.enums import KnowledgeItemStatus, KnowledgeReviewStatus
from app.services.knowledge_search import KnowledgeSearchService


API_ROOT = Path(__file__).resolve().parents[1]


def fake_item(
    *,
    title,
    body,
    collection_name="channel_sop",
    language="zh",
    country="Russia",
    channels=None,
    status=KnowledgeItemStatus.ACTIVE,
    review_status=KnowledgeReviewStatus.APPROVED,
):
    return SimpleNamespace(
        title=title,
        body=body,
        language=language,
        country=country,
        applicable_channels=channels or [],
        status=status,
        review_status=review_status,
        collection=SimpleNamespace(name=collection_name),
        source_ref="test-source.md",
    )


def test_search_only_returns_active_approved_and_excludes_deprecated() -> None:
    items = [
        fake_item(title="Approved SOP", body="公开页面读取规则"),
        fake_item(title="Draft SOP", body="公开页面读取规则", review_status=KnowledgeReviewStatus.PENDING),
        fake_item(title="Deprecated SOP", body="公开页面读取规则", status=KnowledgeItemStatus.DEPRECATED),
    ]

    results = KnowledgeSearchService.keyword_fallback_search(
        items,
        collection="channel_sop",
        query="公开页面",
    )

    assert [result.item.title for result in results] == ["Approved SOP"]


def test_search_filters_faq_and_script_template_by_language() -> None:
    items = [
        fake_item(title="FAQ RU", body="цена логистика", collection_name="faq", language="ru"),
        fake_item(title="FAQ ZH", body="价格 物流", collection_name="faq", language="zh"),
        fake_item(title="Script RU", body="отказаться от связи", collection_name="script_template", language="ru"),
    ]

    results = KnowledgeSearchService.keyword_fallback_search(
        items,
        collection="faq",
        language="ru",
        query="логистика",
    )

    assert [result.item.title for result in results] == ["FAQ RU"]


def test_search_filters_by_country_and_channel() -> None:
    items = [
        fake_item(title="Russia Maps", body="Yandex map SOP", channels=["maps"], country="Russia"),
        fake_item(title="Russia Social", body="VK manual SOP", channels=["social_manual"], country="Russia"),
        fake_item(title="Kazakhstan Maps", body="map SOP", channels=["maps"], country="Kazakhstan"),
    ]

    results = KnowledgeSearchService.keyword_fallback_search(
        items,
        country="Russia",
        channel="maps",
        query="SOP",
    )

    assert [result.item.title for result in results] == ["Russia Maps"]


def test_pgvector_unavailable_uses_keyword_fallback_with_explicit_note() -> None:
    decision = KnowledgeSearchService.resolve_search_mode(
        query_embedding=None,
        allow_keyword_fallback=True,
    )

    assert decision["search_mode"] == "keyword_fallback"
    assert "pgvector" in decision["fallback_reason"]


def test_knowledge_search_api_contract_exists() -> None:
    api_file = API_ROOT / "app" / "api" / "knowledge.py"

    text = api_file.read_text(encoding="utf-8")
    assert '@router.post("/search"' in text

