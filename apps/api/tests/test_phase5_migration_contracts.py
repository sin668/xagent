import asyncio
from pathlib import Path

from sqlalchemy import text

from app.db.session import async_engine
from app.migration_contracts.phase5 import PHASE5_MIGRATION_CONTRACTS, PHASE5_ROLLBACK_STRATEGY


API_ROOT = Path(__file__).resolve().parents[1]


def test_phase5_migration_contract_manifest_covers_expected_revisions() -> None:
    revisions = [contract["revision"] for contract in PHASE5_MIGRATION_CONTRACTS]

    assert revisions == [
        "20260605_0029",
        "20260605_0030",
        "20260605_0031",
        "20260605_0032",
        "20260605_0033",
    ]
    assert "downgrade" in PHASE5_ROLLBACK_STRATEGY.lower()
    assert "20260605_0033" in PHASE5_ROLLBACK_STRATEGY
    assert "20260605_0028" in PHASE5_ROLLBACK_STRATEGY


def test_phase5_migration_files_declare_downgrade_or_equivalent_rollback_strategy() -> None:
    for contract in PHASE5_MIGRATION_CONTRACTS:
        migration_path = API_ROOT / "alembic" / "versions" / contract["filename"]
        assert migration_path.exists()
        migration = migration_path.read_text(encoding="utf-8")

        assert f'revision = "{contract["revision"]}"' in migration
        assert f'down_revision = "{contract["down_revision"]}"' in migration
        assert "def upgrade()" in migration
        assert "def downgrade()" in migration

        for table_name in contract.get("tables", {}):
            assert f'"{table_name}"' in migration

        for enum_name in contract.get("enums", {}):
            assert enum_name in migration


def test_phase5_real_postgresql_database_matches_migration_contract() -> None:
    async def inspect_contracts() -> None:
        async with async_engine.connect() as conn:
            current_revision = (
                await conn.execute(text("select version_num from alembic_version"))
            ).scalar_one()
            assert current_revision == PHASE5_MIGRATION_CONTRACTS[-1]["revision"]

            for contract in PHASE5_MIGRATION_CONTRACTS:
                for table_name, expected_columns in contract.get("tables", {}).items():
                    columns = (
                        await conn.execute(
                            text(
                                """
                                select column_name
                                from information_schema.columns
                                where table_schema = 'public' and table_name = :table_name
                                """
                            ),
                            {"table_name": table_name},
                        )
                    ).scalars().all()
                    for column_name in expected_columns:
                        assert column_name in columns

                for enum_name, expected_values in contract.get("enums", {}).items():
                    values = (
                        await conn.execute(
                            text(
                                """
                                select enumlabel
                                from pg_enum
                                join pg_type on pg_type.oid = pg_enum.enumtypid
                                where pg_type.typname = :enum_name
                                order by enumsortorder
                                """
                            ),
                            {"enum_name": enum_name},
                        )
                    ).scalars().all()
                    for enum_value in expected_values:
                        assert enum_value in values

    asyncio.run(inspect_contracts())
