from __future__ import annotations

from typing import Any

from app.models.llm_prompt_template import LLMPromptTemplate
from app.services.llm_prompt_repository import LoadedLLMPromptTemplate


class StaticPromptRepository:
    def __init__(self, output_schema_json: dict[str, Any] | None = None) -> None:
        self.output_schema_json = output_schema_json or {"type": "object"}
        self.requests: list[dict[str, str]] = []

    def load_active_default(self, *, task_type: str, provider: str, model: str) -> LoadedLLMPromptTemplate:
        self.requests.append({"task_type": task_type, "provider": provider, "model": model})
        return LoadedLLMPromptTemplate(
            template_id="11111111-1111-1111-1111-111111111111",
            name=f"{task_type.lower()}_test_default",
            task_type=task_type,
            provider=provider,
            model=model,
            system_prompt=f"DB SYSTEM {task_type}",
            user_prompt_template="DB USER {{market}} {{source_url}} {{source_content}} {{recommended_grade}} {{lead}} {{leads}} {{lead_snapshot}} {{page_snapshots}} {{context}}",
            output_schema_json=self.output_schema_json,
            version="test-v1",
        )


def seed_prompt_templates(session, task_types: list[str] | tuple[str, ...]) -> None:
    for task_type in task_types:
        session.add(
            LLMPromptTemplate(
                name=f"{task_type.lower()}_test_default",
                task_type=task_type,
                provider="deepseek",
                model="deepseek-chat",
                system_prompt=f"DB SYSTEM {task_type}",
                user_prompt_template=(
                    "DB USER {{market}} {{source_url}} {{source_content}} {{recommended_grade}} "
                    "{{lead}} {{leads}} {{lead_snapshot}} {{page_snapshots}} {{context}}"
                ),
                output_schema_json={"type": "object"},
                version="test-v1",
                status="active",
                is_default=True,
            )
        )
    session.commit()
