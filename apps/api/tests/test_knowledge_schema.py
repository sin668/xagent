from pathlib import Path

from app.models.enums import KnowledgeItemStatus, KnowledgeReviewStatus
from app.services.knowledge import KnowledgeService


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0018_knowledge_pgvector_schema.py"


def test_knowledge_migration_declares_tables_and_pgvector_embedding() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0018"' in migration
    assert 'down_revision = "20260529_0017"' in migration
    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration
    for table in ["knowledge_collections", "knowledge_items", "knowledge_embeddings"]:
        assert f'"{table}"' in migration
    for field in ["status", "review_status", "version", "source_ref"]:
        assert field in migration
    assert "vector(1536)" in migration
    assert "embedding_status" in migration
    assert "error_message" in migration


def test_knowledge_models_and_router_are_registered() -> None:
    models_init = (API_ROOT / "app" / "models" / "__init__.py").read_text(encoding="utf-8")
    main_py = (API_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert "KnowledgeCollection" in models_init
    assert "KnowledgeItem" in models_init
    assert "KnowledgeEmbedding" in models_init
    assert "KnowledgeItemStatus" in models_init
    assert "KnowledgeReviewStatus" in models_init
    assert "knowledge_router" in main_py


def test_only_active_approved_knowledge_is_rag_eligible() -> None:
    assert (
        KnowledgeService.is_rag_eligible(
            status=KnowledgeItemStatus.ACTIVE,
            review_status=KnowledgeReviewStatus.APPROVED,
        )
        is True
    )
    assert (
        KnowledgeService.is_rag_eligible(
            status=KnowledgeItemStatus.DEPRECATED,
            review_status=KnowledgeReviewStatus.APPROVED,
        )
        is False
    )
    assert (
        KnowledgeService.is_rag_eligible(
            status=KnowledgeItemStatus.ACTIVE,
            review_status=KnowledgeReviewStatus.PENDING,
        )
        is False
    )


def test_embedding_failure_payload_does_not_block_structured_knowledge() -> None:
    payload = KnowledgeService.build_embedding_payload(
        item_id="11111111-1111-1111-1111-111111111111",
        embedding_model="test-embedding",
        embedding=None,
        embedding_dimensions=1536,
        error_message="embedding provider timeout",
    )

    assert payload["embedding_status"] == "failed"
    assert payload["embedding"] is None
    assert payload["error_message"] == "embedding provider timeout"


def test_deprecated_knowledge_filter_is_excluded_from_production_rag() -> None:
    filters = KnowledgeService.production_rag_filters()

    assert filters["status"] == KnowledgeItemStatus.ACTIVE
    assert filters["review_status"] == KnowledgeReviewStatus.APPROVED
    assert filters["exclude_statuses"] == [KnowledgeItemStatus.DEPRECATED]


def test_knowledge_crud_api_contract_exists() -> None:
    api_file = API_ROOT / "app" / "api" / "knowledge.py"

    assert api_file.exists()
    text = api_file.read_text(encoding="utf-8")
    assert '@router.post("/collections"' in text
    assert '@router.get("/collections"' in text
    assert '@router.post("/items"' in text
    assert '@router.get("/items"' in text
    assert '@router.post("/items/{item_id}/embedding"' in text

