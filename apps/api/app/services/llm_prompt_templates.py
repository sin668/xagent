from app.models.enums import LLMPromptTaskType, LLMPromptTemplateStatus
from app.models.llm_prompt_template import LLMPromptTemplate
from sqlalchemy import select
from sqlalchemy.orm import Session


class LLMPromptTemplateService:
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
