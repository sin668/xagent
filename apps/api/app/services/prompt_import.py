from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.prompt_file_parser import ParsedPromptFile, PromptFileParserService


@dataclass(frozen=True)
class PromptImportItemResult:
    source_file_path: str
    source_file_hash: str
    version: str
    task_type: str
    validation_status: str
    action: str
    template_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class PromptImportResult:
    dry_run: bool
    migration_batch_id: str
    scanned_count: int
    planned_count: int
    created_count: int
    skipped_count: int
    items: list[PromptImportItemResult]


class PromptImportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def import_prompt_directory(
        self,
        prompt_dir: Path,
        *,
        repo_root: Path,
        provider: str,
        model: str,
        migration_batch_id: str,
        dry_run: bool,
    ) -> PromptImportResult:
        parsed_files = PromptFileParserService.scan_prompt_directory(prompt_dir, repo_root=repo_root)
        item_results = [
            self._import_parsed_prompt(
                parsed,
                provider=provider,
                model=model,
                migration_batch_id=migration_batch_id,
                dry_run=dry_run,
            )
            for parsed in parsed_files
        ]

        return PromptImportResult(
            dry_run=dry_run,
            migration_batch_id=migration_batch_id,
            scanned_count=len(parsed_files),
            planned_count=sum(1 for item in item_results if item.action.startswith("planned")),
            created_count=sum(1 for item in item_results if item.action.startswith("created")),
            skipped_count=sum(1 for item in item_results if item.action == "skipped_existing"),
            items=item_results,
        )

    def _import_parsed_prompt(
        self,
        parsed: ParsedPromptFile,
        *,
        provider: str,
        model: str,
        migration_batch_id: str,
        dry_run: bool,
    ) -> PromptImportItemResult:
        existing_same_file = self._find_same_file_hash_version(parsed)
        if existing_same_file is not None:
            return self._build_item_result(
                parsed,
                action="skipped_existing",
                template=existing_same_file,
                reason="source_file_path + source_file_hash + version 已存在，跳过幂等写入。",
            )

        active_default = self._find_active_default(parsed, provider=provider, model=model)
        status = LLMPromptTemplateStatus.DRAFT
        is_default = False
        parent_template_id = None
        action = "created_draft"
        if active_default is None and parsed.validation_status == "validation_passed":
            status = LLMPromptTemplateStatus.ACTIVE
            is_default = True
            action = "created_active_default"
        elif active_default is not None:
            parent_template_id = active_default.id

        if dry_run:
            return self._build_item_result(
                parsed,
                action=f"planned_{action}",
                reason="dry_run=true，仅输出迁移计划，不写入数据库。",
            )

        template = LLMPromptTemplate(
            name=parsed.name,
            task_type=parsed.task_type,
            provider=provider,
            model=model,
            system_prompt=parsed.system_prompt,
            user_prompt_template=parsed.user_prompt_template,
            output_schema_json=parsed.output_schema_json,
            version=parsed.version,
            status=status,
            is_default=is_default,
            created_by="prompt_import_script",
            source_file_path=parsed.source_file_path,
            source_file_hash=parsed.source_file_hash,
            migration_batch_id=migration_batch_id,
            parent_template_id=parent_template_id,
            change_summary="从 prompts/*.md 文件导入基线 Prompt。",
            validation_status=parsed.validation_status,
            validation_errors_json=parsed.validation_errors_json,
        )
        self.session.add(template)
        self.session.flush()
        return self._build_item_result(parsed, action=action, template=template)

    def _find_same_file_hash_version(self, parsed: ParsedPromptFile) -> LLMPromptTemplate | None:
        return self.session.scalar(
            select(LLMPromptTemplate)
            .where(LLMPromptTemplate.source_file_path == parsed.source_file_path)
            .where(LLMPromptTemplate.source_file_hash == parsed.source_file_hash)
            .where(LLMPromptTemplate.version == parsed.version)
            .order_by(LLMPromptTemplate.created_at.desc(), LLMPromptTemplate.id.desc())
        )

    def _find_active_default(self, parsed: ParsedPromptFile, *, provider: str, model: str) -> LLMPromptTemplate | None:
        return self.session.scalar(
            select(LLMPromptTemplate)
            .where(LLMPromptTemplate.task_type == parsed.task_type)
            .where(LLMPromptTemplate.provider == provider)
            .where(LLMPromptTemplate.model == model)
            .where(LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE)
            .where(LLMPromptTemplate.is_default.is_(True))
            .order_by(LLMPromptTemplate.created_at.desc(), LLMPromptTemplate.id.desc())
        )

    @staticmethod
    def _build_item_result(
        parsed: ParsedPromptFile,
        *,
        action: str,
        template: LLMPromptTemplate | None = None,
        reason: str | None = None,
    ) -> PromptImportItemResult:
        return PromptImportItemResult(
            source_file_path=parsed.source_file_path,
            source_file_hash=parsed.source_file_hash,
            version=parsed.version,
            task_type=parsed.task_type.value,
            validation_status=parsed.validation_status,
            action=action,
            template_id=str(template.id) if template is not None else None,
            reason=reason,
        )
