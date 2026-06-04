from urllib.parse import urlparse

import pytest
from redis.asyncio import from_url
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.settings import settings


EXPECTED_TABLES = {
    "customers",
    "lead_sources",
    "contact_methods",
    "outreach_records",
    "inventory_items",
    "channel_risk_rules",
    "ai_audit_logs",
    "compliance_reviews",
    "sync_logs",
    "script_templates",
    "phase1_data_layers",
    "phase1_data_layer_table_map",
    "collection_tasks",
    "candidate_urls",
    "page_snapshots",
    "staging_leads",
    "agent_run_logs",
    "review_logs",
    "risk_events",
    "channel_plans",
    "llm_prompt_templates",
    "agent_task_runs",
    "lead_source_candidates",
}

EXPECTED_ALEMBIC_HEAD = "20260602_0022"


@pytest.mark.asyncio
async def test_real_postgres_has_mvp_data_foundation_tables() -> None:
    parsed = urlparse(settings.database_url)
    assert parsed.scheme == "postgresql+asyncpg"
    assert parsed.hostname not in {None, "localhost"}

    async with AsyncSessionLocal() as session:
        table_rows = await session.execute(
            text(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public'
                """
            )
        )
        existing_tables = {row[0] for row in table_rows}

        revision = await session.scalar(text("select version_num from alembic_version"))

    assert EXPECTED_TABLES <= existing_tables
    assert revision == EXPECTED_ALEMBIC_HEAD


@pytest.mark.asyncio
async def test_real_redis_ping_succeeds() -> None:
    parsed = urlparse(settings.redis_url or "")
    assert parsed.scheme == "redis"
    assert parsed.hostname not in {None, "localhost"}

    redis = from_url(settings.redis_url)
    try:
        assert await redis.ping() is True
    finally:
        await redis.aclose()
