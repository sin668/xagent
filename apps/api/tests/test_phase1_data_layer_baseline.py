from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "20260529_0009_phase1_data_layer_baseline.py"
DOC_PATH = REPO_ROOT / "docs" / "database" / "phase-1-data-layers.md"


def test_phase1_data_layer_migration_declares_pgvector_and_layers() -> None:
    assert MIGRATION_PATH.exists()
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260529_0009"' in migration
    assert 'down_revision = "20260528_0008"' in migration
    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration
    assert "pgvector extension is required" in migration
    assert "phase1_data_layers" in migration
    assert "phase1_data_layer_table_map" in migration

    for layer in ["raw", "staging", "core", "audit", "knowledge"]:
        assert f'"{layer}"' in migration


def test_phase1_data_layer_migration_does_not_drop_existing_core_tables() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    protected_core_tables = [
        "customers",
        "contact_methods",
        "lead_sources",
        "outreach_records",
        "compliance_reviews",
    ]

    for table_name in protected_core_tables:
        assert f'op.drop_table("{table_name}")' not in migration
        assert f"op.drop_table('{table_name}')" not in migration


def test_phase1_data_layer_document_covers_layers_and_pgvector_runbook() -> None:
    assert DOC_PATH.exists()
    document = DOC_PATH.read_text(encoding="utf-8")

    for heading in [
        "raw",
        "staging",
        "core",
        "audit",
        "knowledge",
        "pgvector",
        "安装指引",
    ]:
        assert heading in document

    assert "不使用内存 SQLite" in document
    assert "不自动社交私信" in document
