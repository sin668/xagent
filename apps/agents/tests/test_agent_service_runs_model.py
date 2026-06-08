from pathlib import Path
import re
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.db.base import Base
from app.models.agent_service_run import AgentServiceRun
from app.schemas.agent_service_run import AgentServiceRunRead


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_agent_service_runs_model_declares_expected_columns() -> None:
    columns = AgentServiceRun.__table__.columns

    expected_columns = {
        "id",
        "request_id",
        "agent_type",
        "agent_mode",
        "status",
        "trigger_source",
        "input_json",
        "output_json",
        "output_summary_json",
        "audit_json",
        "retry_count",
        "max_retries",
        "next_retry_at",
        "error_type",
        "error_message",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    }

    assert AgentServiceRun.__tablename__ == "agent_service_runs"
    assert set(columns.keys()) == expected_columns
    assert Base.metadata.tables["agent_service_runs"] is AgentServiceRun.__table__


def test_agent_service_runs_schema_matches_model_core_fields() -> None:
    model_column_names = set(AgentServiceRun.__table__.columns.keys())
    schema_field_names = set(AgentServiceRunRead.model_fields.keys())

    assert model_column_names == schema_field_names

    run = AgentServiceRunRead(
        id="11111111-1111-1111-1111-111111111111",
        request_id="22222222-2222-2222-2222-222222222222",
        agent_type="deep_enrichment",
        agent_mode="active",
        status="pending",
        trigger_source="manual_api",
        input_json={"staging_lead_id": "33333333-3333-3333-3333-333333333333"},
        retry_count=0,
        max_retries=2,
    )

    assert isinstance(run.id, UUID)
    assert run.agent_type == "deep_enrichment"
    assert run.agent_mode == "active"
    assert run.status == "pending"
    assert run.input_json["staging_lead_id"] == "33333333-3333-3333-3333-333333333333"
    assert run.output_json is None
    assert run.audit_json == {}


def test_agent_service_runs_postgresql_ddl_contains_only_agent_table() -> None:
    ddl = str(CreateTable(AgentServiceRun.__table__).compile(dialect=postgresql.dialect()))

    assert "CREATE TABLE agent_service_runs" in ddl
    assert "agent_type" in ddl
    assert "agent_mode" in ddl
    assert "trigger_source" in ddl
    assert "JSONB" in ddl
    assert "customers" not in ddl
    assert "lead_sources" not in ddl
    assert "contact_methods" not in ddl
    assert "staging_leads" not in ddl


def test_agent_service_runs_migration_creates_only_agent_service_runs_table() -> None:
    migration_paths = list((PROJECT_ROOT / "alembic" / "versions").glob("*agent_service_runs*.py"))

    assert len(migration_paths) == 1
    migration_text = migration_paths[0].read_text(encoding="utf-8")
    assert re.search(r'op\.create_table\(\s*"agent_service_runs"', migration_text)
    assert '"agent_service_node_runs"' not in migration_text
    for forbidden_table in ("customers", "lead_sources", "contact_methods", "staging_leads"):
        assert forbidden_table not in migration_text
    assert "sa.Uuid" in migration_text
    assert "sa.JSON" in migration_text
    assert "postgresql.JSONB" not in migration_text
