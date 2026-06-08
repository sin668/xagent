from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = API_ROOT / "alembic" / "versions"


def read_migration(filename: str) -> str:
    return (MIGRATION_DIR / filename).read_text(encoding="utf-8")


def test_phase3_migration_chain_is_linear_and_reaches_expected_head() -> None:
    migrations = {
        "20260604_0024": read_migration("20260604_0024_create_lead_enrichment_results.py"),
        "20260604_0025": read_migration("20260604_0025_create_lead_enrichment_field_candidates.py"),
        "20260604_0026": read_migration("20260604_0026_create_lead_cleanup_tables.py"),
        "20260604_0027": read_migration("20260604_0027_create_customer_intents_followups.py"),
    }

    assert 'revision = "20260604_0024"' in migrations["20260604_0024"]
    assert 'down_revision = "20260603_0023"' in migrations["20260604_0024"]
    assert 'revision = "20260604_0025"' in migrations["20260604_0025"]
    assert 'down_revision = "20260604_0024"' in migrations["20260604_0025"]
    assert 'revision = "20260604_0026"' in migrations["20260604_0026"]
    assert 'down_revision = "20260604_0025"' in migrations["20260604_0026"]
    assert 'revision = "20260604_0027"' in migrations["20260604_0027"]
    assert 'down_revision = "20260604_0026"' in migrations["20260604_0027"]


def test_phase3_migrations_create_required_tables_once() -> None:
    required_tables = {
        "20260604_0024_create_lead_enrichment_results.py": ["lead_enrichment_results"],
        "20260604_0025_create_lead_enrichment_field_candidates.py": ["lead_enrichment_field_candidates"],
        "20260604_0026_create_lead_cleanup_tables.py": ["lead_cleanup_runs", "lead_cleanup_suggestions"],
        "20260604_0027_create_customer_intents_followups.py": ["customer_vehicle_intents", "customer_followups"],
    }

    for filename, table_names in required_tables.items():
        migration = read_migration(filename)
        for table_name in table_names:
            assert migration.count(f'"{table_name}"') >= 1, f"{filename} missing {table_name}"


def test_phase3_migrations_use_postgresql_jsonb_and_uuid_contracts() -> None:
    for filename in (
        "20260604_0024_create_lead_enrichment_results.py",
        "20260604_0025_create_lead_enrichment_field_candidates.py",
        "20260604_0026_create_lead_cleanup_tables.py",
        "20260604_0027_create_customer_intents_followups.py",
    ):
        migration = read_migration(filename)
        assert "postgresql.UUID(as_uuid=True)" in migration

    jsonb_migrations = (
        "20260604_0024_create_lead_enrichment_results.py",
        "20260604_0025_create_lead_enrichment_field_candidates.py",
        "20260604_0026_create_lead_cleanup_tables.py",
        "20260604_0027_create_customer_intents_followups.py",
    )
    for filename in jsonb_migrations:
        migration = read_migration(filename)
        assert "postgresql.JSONB" in migration


def test_phase3_migrations_keep_high_risk_actions_out_of_schema() -> None:
    forbidden_tokens = (
        "auto_send",
        "auto_friend",
        "auto_message",
        "social_login",
        "crawler_bypass",
        "anti_bot",
    )

    for path in sorted(MIGRATION_DIR.glob("20260604_00*.py")):
        if path.name < "20260604_0024":
            continue
        migration = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in migration


def test_phase3_contract_does_not_use_memory_database_as_formal_migration_validation() -> None:
    test_files = [
        API_ROOT / "tests" / "test_phase3_model_contract.py",
        API_ROOT / "tests" / "test_lead_enrichment_result_model.py",
        API_ROOT / "tests" / "test_lead_enrichment_field_candidate_model.py",
        API_ROOT / "tests" / "test_lead_cleanup_models.py",
        API_ROOT / "tests" / "test_customer_intents_followups_models.py",
    ]

    for test_file in test_files:
        test_text = test_file.read_text(encoding="utf-8")
        assert "sqlite://" not in test_text.lower()
        assert "sqlite+aiosqlite" not in test_text.lower()
        assert "create_engine(\"sqlite" not in test_text.lower()
        assert "postgresql.dialect" in test_text
