from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from sqlalchemy import select
from sqlalchemy.orm import Session


class LLMPromptTemplateService:
    DRAFT_EDITOR_ROLES = {"admin", "tech_admin"}

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

        for field_name, value in payload.items():
            if field_name in {"actor", "actor_role"}:
                continue
            if value is not None:
                setattr(template, field_name, value)
        self.session.flush()
        return template

    @classmethod
    def ensure_draft_editor(cls, actor_role: str | None) -> None:
        role = str(actor_role or "").strip().lower()
        if role not in cls.DRAFT_EDITOR_ROLES:
            raise PermissionError("只有 admin 或 tech_admin 可以创建和编辑 Prompt 草稿")

    @staticmethod
    def validate_default_template_uniqueness(
        *,
        existing_templates: list[dict],
        task_type: LLMPromptTaskType,
        status: LLMPromptTemplateStatus,
        is_default: bool,
    ) -> None:
        if status != LLMPromptTemplateStatus.ACTIVE or not is_default:
            return

        for template in existing_templates:
            if (
                template.get("task_type") == task_type
                and template.get("status") == LLMPromptTemplateStatus.ACTIVE
                and template.get("is_default") is True
            ):
                raise ValueError("同一 task_type 只能有一个 active 默认模板")
