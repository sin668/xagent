import re
from datetime import UTC, datetime

from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from app.models.review_log import ReviewLog
from sqlalchemy import select
from sqlalchemy.orm import Session


class LLMPromptTemplateService:
    DRAFT_EDITOR_ROLES = {"admin", "tech_admin"}
    SCHEMA_EDITOR_ROLES = {"tech_admin"}
    EMAIL_REPLY_RISK_BOUNDARIES = ("不自动发送", "不编造")

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def list_templates(
        self,
        *,
        task_type: LLMPromptTaskType | None = None,
        status: LLMPromptTemplateStatus | None = None,
        is_default: bool | None = None,
    ) -> list[LLMPromptTemplate]:
        if self.session is None:
            raise ValueError("查询 prompt template 需要传入数据库 session")

        query = select(LLMPromptTemplate).order_by(LLMPromptTemplate.task_type, LLMPromptTemplate.name)
        if task_type is not None:
            query = query.where(LLMPromptTemplate.task_type == task_type)
        if status is not None:
            query = query.where(LLMPromptTemplate.status == status)
        if is_default is not None:
            query = query.where(LLMPromptTemplate.is_default.is_(is_default))
        return list(self.session.scalars(query).all())

    def get_template(self, template_id) -> LLMPromptTemplate | None:
        if self.session is None:
            raise ValueError("查询 prompt template 需要传入数据库 session")
        return self.session.get(LLMPromptTemplate, template_id)

    def list_audit_logs(self, template_id) -> list[ReviewLog]:
        if self.session is None:
            raise ValueError("查询 prompt 审计日志需要传入数据库 session")
        return list(
            self.session.scalars(
                select(ReviewLog)
                .where(ReviewLog.task_id == str(template_id))
                .where(ReviewLog.agent_name == "llm_prompt_governance")
                .order_by(ReviewLog.created_at.desc(), ReviewLog.id.desc())
            ).all()
        )

    def create_draft(self, *, actor: str, actor_role: str, payload: dict) -> LLMPromptTemplate:
        if self.session is None:
            raise ValueError("创建 prompt 草稿需要传入数据库 session")
        self.ensure_draft_editor(actor_role)
        template = LLMPromptTemplate(
            **payload,
            status=LLMPromptTemplateStatus.DRAFT,
            is_default=False,
            created_by=actor,
        )
        self.session.add(template)
        self.session.flush()
        return template

    def update_draft(self, template_id, *, actor_role: str, payload: dict) -> LLMPromptTemplate:
        if self.session is None:
            raise ValueError("编辑 prompt 草稿需要传入数据库 session")
        self.ensure_draft_editor(actor_role)
        template = self.get_template(template_id)
        if template is None:
            raise ValueError("Prompt template 不存在")
        if template.status != LLMPromptTemplateStatus.DRAFT:
            raise PermissionError("只能编辑 draft 状态的 Prompt template")
        if "output_schema_json" in payload and payload.get("output_schema_json") is not None:
            self.ensure_schema_editor(actor_role)

        for field_name, value in payload.items():
            if field_name in {"actor", "actor_role"}:
                continue
            if value is not None:
                setattr(template, field_name, value)
        self.session.flush()
        return template

    def validate_draft_preview(self, template_id, *, actor_role: str, sample_variables: dict) -> dict:
        if self.session is None:
            raise ValueError("校验 prompt 草稿需要传入数据库 session")
        self.ensure_draft_editor(actor_role)
        template = self.get_template(template_id)
        if template is None:
            raise ValueError("Prompt template 不存在")
        if template.status != LLMPromptTemplateStatus.DRAFT:
            raise PermissionError("只能校验 draft 状态的 Prompt template")

        required_variables = self.extract_template_variables(template.user_prompt_template)
        missing_variables = [name for name in required_variables if name not in sample_variables]
        errors: dict[str, object] = {}
        warnings: list[str] = []

        if missing_variables:
            errors["missing_variables"] = missing_variables
        if not isinstance(template.output_schema_json, dict) or not template.output_schema_json.get("type"):
            errors["output_schema_json"] = "output_schema_json 必须是包含 type 的 JSON Schema object。"
        if template.task_type not in set(LLMPromptTaskType):
            errors["task_type"] = "任务类型不合法。"
        if str(template.task_type.value).startswith("EMAIL_REPLY"):
            missing_boundaries = [
                boundary
                for boundary in self.EMAIL_REPLY_RISK_BOUNDARIES
                if boundary not in f"{template.system_prompt}\n{template.user_prompt_template}"
            ]
            if missing_boundaries:
                errors["risk_boundaries"] = missing_boundaries

        rendered_user_prompt = self.render_template_variables(template.user_prompt_template, sample_variables)
        passed = not errors
        template.validation_status = "validation_passed" if passed else "validation_failed"
        template.validation_errors_json = None if passed else errors
        self.session.flush()

        return {
            "template_id": template.id,
            "passed": passed,
            "validation_status": template.validation_status,
            "errors": errors,
            "warnings": warnings,
            "required_variables": required_variables,
            "missing_variables": missing_variables,
            "rendered_user_prompt": rendered_user_prompt,
            "would_publish": False,
        }

    def publish_draft(self, template_id, *, actor: str, actor_role: str, change_summary: str | None) -> LLMPromptTemplate:
        if self.session is None:
            raise ValueError("发布 prompt 草稿需要传入数据库 session")
        self.ensure_draft_editor(actor_role)
        template = self.get_template(template_id)
        if template is None:
            raise ValueError("Prompt template 不存在")
        if template.status != LLMPromptTemplateStatus.DRAFT:
            raise PermissionError("只能发布 draft 状态的 Prompt template")
        if template.validation_status != "validation_passed":
            raise PermissionError("Prompt template 校验未通过，不能发布")

        self._clear_default_active_for_same_scope(template)
        template.status = LLMPromptTemplateStatus.ACTIVE
        template.is_default = True
        template.published_by = actor
        template.published_at = datetime.now(UTC)
        template.change_summary = change_summary
        self._write_audit_log(
            template=template,
            action="prompt_publish",
            reviewer=actor,
            result="success",
            input_ref=change_summary,
            output_ref=f"status={template.status.value};is_default={template.is_default}",
        )
        self.session.flush()
        return template

    def set_default(self, template_id, *, actor: str, actor_role: str, change_summary: str | None) -> LLMPromptTemplate:
        if self.session is None:
            raise ValueError("切换默认 prompt 需要传入数据库 session")
        self.ensure_draft_editor(actor_role)
        template = self.get_template(template_id)
        if template is None:
            raise ValueError("Prompt template 不存在")
        if template.status not in {LLMPromptTemplateStatus.ACTIVE, LLMPromptTemplateStatus.PAUSED}:
            raise PermissionError("只有 active 或 paused 版本可以切换为默认版本")

        self._clear_default_active_for_same_scope(template)
        template.status = LLMPromptTemplateStatus.ACTIVE
        template.is_default = True
        template.published_by = actor
        template.published_at = datetime.now(UTC)
        template.change_summary = change_summary
        self._write_audit_log(
            template=template,
            action="prompt_set_default",
            reviewer=actor,
            result="success",
            input_ref=change_summary,
            output_ref=f"status={template.status.value};is_default={template.is_default}",
        )
        self.session.flush()
        return template

    def rollback_to_template(
        self,
        template_id,
        *,
        rollback_to_template_id,
        actor: str,
        actor_role: str,
        change_summary: str | None,
    ) -> LLMPromptTemplate:
        if self.session is None:
            raise ValueError("回滚 prompt 需要传入数据库 session")
        self.ensure_draft_editor(actor_role)
        current = self.get_template(template_id)
        target = self.get_template(rollback_to_template_id)
        if current is None or target is None:
            raise ValueError("Prompt template 不存在")
        if current.task_type != target.task_type or current.provider != target.provider or current.model != target.model:
            raise PermissionError("只能回滚到相同 task_type/provider/model 的历史版本")

        rollback_draft = LLMPromptTemplate(
            name=f"{target.name}_rollback",
            task_type=target.task_type,
            provider=target.provider,
            model=target.model,
            system_prompt=target.system_prompt,
            user_prompt_template=target.user_prompt_template,
            output_schema_json=target.output_schema_json,
            version=f"{target.version}-rollback",
            status=LLMPromptTemplateStatus.DRAFT,
            is_default=False,
            created_by=actor,
            source_file_path=target.source_file_path,
            source_file_hash=target.source_file_hash,
            migration_batch_id=target.migration_batch_id,
            parent_template_id=target.id,
            change_summary=change_summary,
            rollback_from_template_id=current.id,
            validation_status=target.validation_status,
            validation_errors_json=target.validation_errors_json,
        )
        self.session.add(rollback_draft)
        self.session.flush()
        self._write_audit_log(
            template=current,
            action="prompt_rollback",
            reviewer=actor,
            result="success",
            input_ref=change_summary,
            output_ref=f"rollback_draft_id={rollback_draft.id};rollback_to_template_id={target.id}",
        )
        self.session.flush()
        return rollback_draft

    def _clear_default_active_for_same_scope(self, template: LLMPromptTemplate) -> None:
        existing_defaults = self.session.scalars(
            select(LLMPromptTemplate)
            .where(LLMPromptTemplate.task_type == template.task_type)
            .where(LLMPromptTemplate.provider == template.provider)
            .where(LLMPromptTemplate.model == template.model)
            .where(LLMPromptTemplate.status == LLMPromptTemplateStatus.ACTIVE)
            .where(LLMPromptTemplate.is_default.is_(True))
            .where(LLMPromptTemplate.id != template.id)
        ).all()
        for existing in existing_defaults:
            existing.is_default = False
            existing.status = LLMPromptTemplateStatus.PAUSED
        if existing_defaults:
            self.session.flush()

    @classmethod
    def ensure_draft_editor(cls, actor_role: str | None) -> None:
        role = str(actor_role or "").strip().lower()
        if role not in cls.DRAFT_EDITOR_ROLES:
            raise PermissionError("只有 admin 或 tech_admin 可以创建和编辑 Prompt 草稿")

    @classmethod
    def ensure_schema_editor(cls, actor_role: str | None) -> None:
        role = str(actor_role or "").strip().lower()
        if role not in cls.SCHEMA_EDITOR_ROLES:
            raise PermissionError("只有 tech_admin 可以编辑 Prompt output_schema_json")

    def _write_audit_log(
        self,
        *,
        template: LLMPromptTemplate,
        action: str,
        reviewer: str,
        result: str,
        input_ref: str | None,
        output_ref: str | None,
    ) -> None:
        if self.session is None:
            raise ValueError("写入 prompt 审计日志需要传入数据库 session")
        self.session.add(
            ReviewLog(
                task_id=str(template.id),
                agent_name="llm_prompt_governance",
                action=action,
                reviewer=reviewer,
                input_ref=input_ref,
                output_ref=output_ref,
                result=result,
            )
        )

    @staticmethod
    def extract_template_variables(template: str) -> list[str]:
        return sorted(set(re.findall(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}", template)))

    @staticmethod
    def render_template_variables(template: str, variables: dict) -> str:
        rendered = template
        for name, value in variables.items():
            rendered = re.sub(r"{{\s*" + re.escape(str(name)) + r"\s*}}", str(value), rendered)
        return rendered

    @staticmethod
    def validate_default_template_uniqueness(
        *,
        existing_templates: list[dict],
        task_type: LLMPromptTaskType,
        provider: str | None = None,
        model: str | None = None,
        status: LLMPromptTemplateStatus,
        is_default: bool,
    ) -> None:
        if status != LLMPromptTemplateStatus.ACTIVE or not is_default:
            return

        for template in existing_templates:
            if (
                template.get("task_type") == task_type
                and (provider is None or template.get("provider") == provider)
                and (model is None or template.get("model") == model)
                and template.get("status") == LLMPromptTemplateStatus.ACTIVE
                and template.get("is_default") is True
            ):
                raise ValueError("同一 task_type/provider/model 只能有一个 active 默认模板")
