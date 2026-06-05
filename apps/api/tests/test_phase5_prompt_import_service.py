from pathlib import Path
from textwrap import dedent

import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.prompt_import import PromptImportService


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "poc" / "import_prompts.py"


def write_prompt_file(prompt_dir: Path, filename: str, title: str, schema_required: str = "reply") -> Path:
    prompt_dir.mkdir(parents=True, exist_ok=True)
    path = prompt_dir / filename
    path.write_text(
        dedent(
            f"""\
            # {title}

            ## System Prompt

            ```text
            system body for {title}
            ```

            ## User Prompt Template

            ```text
            user body for {title}
            ```

            ## Output JSON Schema

            ```json
            {{"type": "object", "required": ["{schema_required}"]}}
            ```
            """
        ),
        encoding="utf-8",
    )
    return path


def cleanup_prompt_import_batch(sync_session, batch_id: str) -> None:
    sync_session.query(LLMPromptTemplate).filter(
        LLMPromptTemplate.migration_batch_id == batch_id,
    ).delete(synchronize_session=False)


@pytest.mark.asyncio
async def test_phase5_prompt_import_service_is_idempotent_for_same_file_hash_and_version(tmp_path: Path) -> None:
    batch_id = "phase5-test-idempotent"
    prompt_dir = tmp_path / "prompts"
    write_prompt_file(prompt_dir, "email-reply-idempotent-one.md", "Email Reply Idempotent One Prompt")
    write_prompt_file(prompt_dir, "email-reply-idempotent-two.md", "Email Reply Idempotent Two Prompt", schema_required="subject")
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            cleanup_prompt_import_batch(sync_session, batch_id)
            sync_session.commit()

            try:
                first = PromptImportService(sync_session).import_prompt_directory(
                    prompt_dir,
                    repo_root=tmp_path,
                    provider="file-baseline",
                    model="prompt-md",
                    migration_batch_id=batch_id,
                    dry_run=False,
                )
                second = PromptImportService(sync_session).import_prompt_directory(
                    prompt_dir,
                    repo_root=tmp_path,
                    provider="file-baseline",
                    model="prompt-md",
                    migration_batch_id=batch_id,
                    dry_run=False,
                )
                persisted = sync_session.scalar(
                    select(LLMPromptTemplate)
                    .where(LLMPromptTemplate.source_file_path == "prompts/email-reply-idempotent-one.md")
                    .where(LLMPromptTemplate.migration_batch_id == batch_id)
                )
                return first, second, persisted
            finally:
                cleanup_prompt_import_batch(sync_session, batch_id)
                sync_session.commit()

        first, second, persisted = await async_session.run_sync(run)

    assert first.created_count == 2
    assert second.created_count == 0
    assert second.skipped_count == 2
    assert persisted


@pytest.mark.asyncio
async def test_phase5_prompt_import_creates_draft_when_hash_changes_and_active_default_exists(tmp_path: Path) -> None:
    batch_id = "phase5-test-hash-change"
    prompt_dir = tmp_path / "prompts"
    write_prompt_file(prompt_dir, "email-reply-hash-change.md", "Email Reply Hash Change Prompt")
    source_file_path = "prompts/email-reply-hash-change.md"
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            cleanup_prompt_import_batch(sync_session, batch_id)
            sync_session.commit()

            try:
                existing = LLMPromptTemplate(
                    name="Existing Active Lead Extraction",
                    task_type=LLMPromptTaskType.EMAIL_REPLY_DRAFT,
                    provider="file-baseline",
                    model="prompt-md",
                    system_prompt="active system",
                    user_prompt_template="active user",
                    output_schema_json={},
                    version="email-reply-hash-change-v1",
                    status=LLMPromptTemplateStatus.ACTIVE,
                    is_default=True,
                    source_file_path=source_file_path,
                    source_file_hash="old-hash",
                    migration_batch_id=batch_id,
                )
                sync_session.add(existing)
                sync_session.commit()

                result = PromptImportService(sync_session).import_prompt_directory(
                    prompt_dir,
                    repo_root=tmp_path,
                    provider="file-baseline",
                    model="prompt-md",
                    migration_batch_id=batch_id,
                    dry_run=False,
                )

                records = list(
                    sync_session.scalars(
                        select(LLMPromptTemplate)
                        .where(LLMPromptTemplate.source_file_path == source_file_path)
                        .where(LLMPromptTemplate.migration_batch_id == batch_id)
                        .order_by(LLMPromptTemplate.created_at)
                    )
                )
                return result, records
            finally:
                cleanup_prompt_import_batch(sync_session, batch_id)
                sync_session.commit()

        result, records = await async_session.run_sync(run)

    created = [
        item
        for item in result.items
        if item.source_file_path == source_file_path and item.action == "created_draft"
    ]
    assert created
    assert len(records) == 2
    assert records[0].status == LLMPromptTemplateStatus.ACTIVE
    assert records[0].is_default is True
    assert records[1].status == LLMPromptTemplateStatus.DRAFT
    assert records[1].is_default is False
    assert records[1].parent_template_id == records[0].id


@pytest.mark.asyncio
async def test_phase5_prompt_import_dry_run_reports_without_writing(tmp_path: Path) -> None:
    batch_id = "phase5-test-dry-run"
    prompt_dir = tmp_path / "prompts"
    write_prompt_file(prompt_dir, "email-reply-dry-run-one.md", "Email Reply Dry Run One Prompt")
    write_prompt_file(prompt_dir, "email-reply-dry-run-two.md", "Email Reply Dry Run Two Prompt", schema_required="subject")
    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            cleanup_prompt_import_batch(sync_session, batch_id)
            sync_session.commit()

            try:
                result = PromptImportService(sync_session).import_prompt_directory(
                    prompt_dir,
                    repo_root=tmp_path,
                    provider="file-baseline",
                    model="prompt-md",
                    migration_batch_id=batch_id,
                    dry_run=True,
                )
                count = (
                    sync_session.query(LLMPromptTemplate)
                    .filter(LLMPromptTemplate.migration_batch_id == batch_id)
                    .count()
                )
                return result, count
            finally:
                cleanup_prompt_import_batch(sync_session, batch_id)
                sync_session.commit()

        result, count = await async_session.run_sync(run)

    assert result.dry_run is True
    assert result.planned_count == 2
    assert result.created_count == 0
    assert count == 0


def test_phase5_prompt_import_script_exists_for_macos_local_execution() -> None:
    assert SCRIPT_PATH.exists()
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "#!/usr/bin/env python3" in script
    assert "PromptImportService" in script
    assert "--dry-run" in script
    assert "迁移报告" in script
