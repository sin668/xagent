from pathlib import Path

from sqlalchemy import insert, select
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.models import AgentTaskRun, LeadSourceCandidate, LLMPromptTemplate
from app.models.enums import (
    AgentTaskRunStatus,
    AgentTaskType,
    ChannelRiskLevel,
    LeadSourceCandidateExtractionStatus,
    LeadSourceCandidateReviewStatus,
    LLMPromptTaskType,
    LLMPromptTemplateStatus,
    SourcePlatform,
)
from app.services.lead_source_candidate_rules import LeadSourceCandidateRules


API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = API_ROOT / "alembic" / "versions"


def test_phase2_models_are_loaded_into_base_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())

    assert "llm_prompt_templates" in table_names
    assert "agent_task_runs" in table_names
    assert "lead_source_candidates" in table_names


def test_phase2_metadata_contract_keeps_candidates_separate_from_core_lead_sources() -> None:
    candidate_columns = set(Base.metadata.tables["lead_source_candidates"].columns.keys())
    lead_source_columns = set(Base.metadata.tables["lead_sources"].columns.keys())

    assert "customer_id" not in candidate_columns
    assert "customer_id" in lead_source_columns
    assert Base.metadata.tables["lead_sources"].columns["customer_id"].nullable is False


def test_phase2_migration_chain_is_linear_and_reaches_expected_head() -> None:
    migration_0020 = (MIGRATION_DIR / "20260602_0020_create_llm_prompt_templates.py").read_text(encoding="utf-8")
    migration_0021 = (MIGRATION_DIR / "20260602_0021_create_agent_task_runs.py").read_text(encoding="utf-8")
    migration_0022 = (MIGRATION_DIR / "20260602_0022_create_lead_source_candidates.py").read_text(encoding="utf-8")

    assert 'revision = "20260602_0020"' in migration_0020
    assert 'down_revision = "20260529_0019"' in migration_0020
    assert 'revision = "20260602_0021"' in migration_0021
    assert 'down_revision = "20260602_0020"' in migration_0021
    assert 'revision = "20260602_0022"' in migration_0022
    assert 'down_revision = "20260602_0021"' in migration_0022


def test_phase2_migrations_reuse_existing_platform_and_risk_enums() -> None:
    migration_0022 = (MIGRATION_DIR / "20260602_0022_create_lead_source_candidates.py").read_text(encoding="utf-8")

    assert 'name="sourceplatform",' in migration_0022
    assert 'name="channelrisklevel", create_type=False' in migration_0022
    assert "CREATE TYPE sourceplatform" not in migration_0022
    assert "CREATE TYPE channelrisklevel" not in migration_0022


def test_phase2_core_tables_can_compile_minimal_insert_and_select_sql() -> None:
    prompt_insert = insert(LLMPromptTemplate).values(
        name="source_discovery_default",
        task_type=LLMPromptTaskType.SOURCE_DISCOVERY,
        provider="deepseek",
        model="deepseek-chat",
        system_prompt="只发现来源，不触达。",
        user_prompt_template="国家: {country}",
        output_schema_json={"type": "object"},
        version="v1.0",
        status=LLMPromptTemplateStatus.ACTIVE,
        is_default=True,
        created_by="contract-test",
    )
    task_insert = insert(AgentTaskRun).values(
        task_type=AgentTaskType.SOURCE_DISCOVERY,
        status=AgentTaskRunStatus.PENDING,
        trigger_source="manual",
        input_json={"country": "Russia"},
        retry_count=0,
    )
    defaults = LeadSourceCandidateRules.resolve_defaults(ChannelRiskLevel.LOW)
    candidate_insert = insert(LeadSourceCandidate).values(
        source_url="https://example.com/dealers",
        normalized_domain="example.com",
        platform=SourcePlatform.OFFICIAL_WEBSITE,
        channel_name="dealer_directory",
        country="Russia",
        city="Moscow",
        risk_level=ChannelRiskLevel.LOW,
        review_status=defaults.review_status,
        approved_for_extraction=defaults.approved_for_extraction,
        discovery_method="keyword_search",
        discovery_query="автосалон Москва",
        discovery_reason="公开目录页",
        evidence_note="公开页面包含 dealer 和 contact 信息",
        evidence_links=["https://example.com/dealers"],
        extraction_status=LeadSourceCandidateExtractionStatus.PENDING,
        retry_count=0,
        dedupe_key=LeadSourceCandidateRules.build_dedupe_key(
            source_url="https://example.com/dealers",
            normalized_domain="example.com",
            platform=SourcePlatform.OFFICIAL_WEBSITE,
        ),
        is_duplicate=False,
    )

    for statement in (
        prompt_insert,
        task_insert,
        candidate_insert,
        select(LLMPromptTemplate).where(LLMPromptTemplate.task_type == LLMPromptTaskType.SOURCE_DISCOVERY),
        select(AgentTaskRun).where(AgentTaskRun.status == AgentTaskRunStatus.PENDING),
        select(LeadSourceCandidate).where(
            LeadSourceCandidate.review_status == LeadSourceCandidateReviewStatus.AUTO_APPROVED
        ),
    ):
        compiled = str(statement.compile(dialect=postgresql.dialect()))
        assert compiled


def test_phase2_contract_limits_lead_source_candidate_api_write_actions() -> None:
    api_file = API_ROOT / "app" / "api" / "lead_source_candidates.py"
    assert api_file.exists()
    api_text = api_file.read_text(encoding="utf-8")
    assert '@router.get("",' in api_text
    assert '@router.get("/{candidate_id}",' in api_text
    assert '@router.post("/{candidate_id}/review-actions",' in api_text
    assert "@router.patch" not in api_text
    assert "@router.delete" not in api_text
    assert '"/outreach' not in api_text
