from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.llm_prompt_repository import LLMPromptRepository, LLMPromptTemplateNotFound


def test_prompt_repository_loads_active_default_prompt_for_provider_model() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        template = LLMPromptTemplate(
            name="lead_extraction_default",
            task_type="LEAD_EXTRACTION",
            provider="deepseek",
            model="deepseek-chat",
            system_prompt="DB system prompt",
            user_prompt_template="DB user prompt {{source_url}}",
            output_schema_json={"type": "object", "required": ["fields"]},
            version="v1.0",
            status="active",
            is_default=True,
        )
        session.add(template)
        session.commit()

        loaded = LLMPromptRepository(session).load_active_default(
            task_type="LEAD_EXTRACTION",
            provider="deepseek",
            model="deepseek-chat",
        )

        assert loaded.template_id == template.id
        assert loaded.system_prompt == "DB system prompt"
        assert loaded.render_user_prompt({"source_url": "https://dealer.example"}) == "DB user prompt https://dealer.example"
        assert loaded.output_schema_json == {"type": "object", "required": ["fields"]}
        assert loaded.audit == {
            "prompt_template_id": str(template.id),
            "prompt_version": "v1.0",
            "prompt_name": "lead_extraction_default",
            "prompt_task_type": "LEAD_EXTRACTION",
        }
    finally:
        session.close()
        engine.dispose()


def test_prompt_repository_fails_when_default_prompt_is_missing() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        try:
            LLMPromptRepository(session).load_active_default(
                task_type="LEAD_CLEANUP",
                provider="deepseek",
                model="deepseek-chat",
            )
        except LLMPromptTemplateNotFound as exc:
            assert exc.error_type == "configuration_error"
            assert "LEAD_CLEANUP" in str(exc)
        else:
            raise AssertionError("missing prompt must raise LLMPromptTemplateNotFound")
    finally:
        session.close()
        engine.dispose()


def test_prompt_repository_uses_text_cast_for_postgresql_enum_columns() -> None:
    statement = LLMPromptRepository.build_active_default_statement(
        task_type="LEAD_EXTRACTION",
        provider="deepseek",
        model="deepseek-chat",
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "CAST(llm_prompt_templates.task_type AS VARCHAR)" in compiled
    assert "CAST(llm_prompt_templates.status AS VARCHAR)" in compiled
