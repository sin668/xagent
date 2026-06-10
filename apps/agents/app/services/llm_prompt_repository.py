from __future__ import annotations

from dataclasses import dataclass
from string import Template
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.llm_prompt_template import LLMPromptTemplate


class LLMPromptTemplateNotFound(RuntimeError):
    error_type = "configuration_error"


@dataclass(frozen=True)
class LoadedLLMPromptTemplate:
    template_id: UUID | str
    name: str
    task_type: str
    provider: str
    model: str
    system_prompt: str
    user_prompt_template: str
    output_schema_json: dict[str, Any]
    version: str

    def render_user_prompt(self, variables: dict[str, Any]) -> str:
        rendered = self.user_prompt_template
        for key, value in variables.items():
            text = self._stringify(value)
            rendered = rendered.replace("{{" + key + "}}", text)
            rendered = rendered.replace("{" + key + "}", text)
        try:
            rendered = Template(rendered).safe_substitute({key: self._stringify(value) for key, value in variables.items()})
        except ValueError:
            pass
        return rendered

    @property
    def audit(self) -> dict[str, str]:
        return {
            "prompt_template_id": str(self.template_id),
            "prompt_version": self.version,
            "prompt_name": self.name,
            "prompt_task_type": self.task_type,
        }

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return "null"
        return str(value)


class LLMPromptRepository:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def load_active_default(self, *, task_type: str, provider: str, model: str) -> LoadedLLMPromptTemplate:
        if self.session is not None:
            return self._load(self.session, task_type=task_type, provider=provider, model=model)
        with SessionLocal() as session:
            return self._load(session, task_type=task_type, provider=provider, model=model)

    def _load(self, session: Session, *, task_type: str, provider: str, model: str) -> LoadedLLMPromptTemplate:
        normalized_task_type = task_type.upper()
        template = session.scalar(
            self.build_active_default_statement(task_type=normalized_task_type, provider=provider, model=model)
        )
        if template is None:
            raise LLMPromptTemplateNotFound(
                f"缺少 active default LLM prompt template：task_type={normalized_task_type}, "
                f"provider={provider}, model={model}"
            )
        return LoadedLLMPromptTemplate(
            template_id=template.id,
            name=template.name,
            task_type=str(template.task_type),
            provider=template.provider,
            model=template.model,
            system_prompt=template.system_prompt,
            user_prompt_template=template.user_prompt_template,
            output_schema_json=dict(template.output_schema_json or {}),
            version=template.version,
        )

    @staticmethod
    def build_active_default_statement(*, task_type: str, provider: str, model: str):
        return (
            select(LLMPromptTemplate)
            .where(cast(LLMPromptTemplate.task_type, String) == task_type.upper())
            .where(LLMPromptTemplate.provider == provider)
            .where(LLMPromptTemplate.model == model)
            .where(cast(LLMPromptTemplate.status, String) == "active")
            .where(LLMPromptTemplate.is_default.is_(True))
            .order_by(LLMPromptTemplate.updated_at.desc(), LLMPromptTemplate.id.desc())
        )
