from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.models.enums import LLMPromptTaskType


@dataclass(frozen=True)
class ParsedPromptFile:
    name: str
    task_type: LLMPromptTaskType
    source_file_path: str
    source_file_hash: str
    system_prompt: str
    user_prompt_template: str
    output_schema_json: dict
    version: str
    validation_status: str
    validation_errors_json: dict | None


class PromptFileParserService:
    _FENCED_BLOCK_PATTERN = re.compile(
        r"^##\s+(?P<section>[^\n]+)\s*\n+```(?P<lang>[a-zA-Z0-9_-]*)\n(?P<body>.*?)\n```",
        re.MULTILINE | re.DOTALL,
    )

    @classmethod
    def scan_prompt_directory(cls, prompt_dir: Path, *, repo_root: Path | None = None) -> list[ParsedPromptFile]:
        root = repo_root or prompt_dir.parent
        return [
            cls.parse_prompt_file(path, repo_root=root)
            for path in sorted(prompt_dir.glob("*.md"))
            if path.is_file()
        ]

    @classmethod
    def parse_prompt_file(cls, prompt_path: Path, *, repo_root: Path | None = None) -> ParsedPromptFile:
        content = prompt_path.read_text(encoding="utf-8")
        root = repo_root or prompt_path.parent.parent
        try:
            source_file_path = prompt_path.relative_to(root).as_posix()
        except ValueError:
            source_file_path = prompt_path.as_posix()
        return cls.parse_markdown_content(content, source_file_path=source_file_path)

    @classmethod
    def parse_markdown_content(cls, content: str, *, source_file_path: str) -> ParsedPromptFile:
        title = cls._extract_title(content)
        sections = cls._extract_fenced_sections(content)
        system_prompt = sections.get("system prompt", "")
        user_prompt_template = sections.get("user prompt template", "")
        output_schema_json, schema_error = cls._extract_output_schema(sections)

        validation_errors: dict[str, str] = {}
        if not system_prompt:
            validation_errors["system_prompt"] = "Prompt 文件缺少 System Prompt 代码块。"
        if not user_prompt_template:
            validation_errors["user_prompt_template"] = "Prompt 文件缺少 User Prompt Template 代码块。"
        if schema_error:
            validation_errors["output_schema_json"] = schema_error

        return ParsedPromptFile(
            name=title,
            task_type=cls.infer_task_type(source_file_path, title),
            source_file_path=source_file_path,
            source_file_hash=cls.compute_content_hash(content),
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            output_schema_json=output_schema_json,
            version=cls.infer_version(source_file_path),
            validation_status="validation_failed" if validation_errors else "validation_passed",
            validation_errors_json=validation_errors or None,
        )

    @staticmethod
    def compute_content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def infer_task_type(source_file_path: str, title: str = "") -> LLMPromptTaskType:
        normalized = f"{source_file_path} {title}".lower()
        if "lead-extraction" in normalized or "公开网页信息抽取" in normalized:
            return LLMPromptTaskType.LEAD_EXTRACTION
        if "lead-grading" in normalized or "线索分级" in normalized:
            return LLMPromptTaskType.LEAD_GRADING
        if "auto-send" in normalized:
            return LLMPromptTaskType.EMAIL_REPLY_AUTO_SEND_CHECK
        if "knowledge-retrieval" in normalized:
            return LLMPromptTaskType.EMAIL_REPLY_KNOWLEDGE_RETRIEVAL
        if "email-reply-send" in normalized:
            return LLMPromptTaskType.EMAIL_REPLY_SEND
        if "email-reply" in normalized:
            return LLMPromptTaskType.EMAIL_REPLY_DRAFT
        if "source-discovery" in normalized:
            return LLMPromptTaskType.SOURCE_DISCOVERY
        return LLMPromptTaskType.EMAIL_REPLY_DRAFT

    @staticmethod
    def infer_version(source_file_path: str) -> str:
        stem = Path(source_file_path).stem
        return f"{stem}-v1"

    @staticmethod
    def _extract_title(content: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return "Unknown Prompt"

    @classmethod
    def _extract_fenced_sections(cls, content: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        for match in cls._FENCED_BLOCK_PATTERN.finditer(content):
            section = cls._normalize_section_name(match.group("section"))
            sections[section] = match.group("body").strip()
        return sections

    @staticmethod
    def _normalize_section_name(section: str) -> str:
        normalized = section.strip().lower()
        return re.sub(r"^\d+(?:\.\d+)*\.\s*", "", normalized)

    @staticmethod
    def _extract_output_schema(sections: dict[str, str]) -> tuple[dict, str | None]:
        raw_schema = None
        for section_name in ("output json schema", "output schema", "输出 json schema", "输出 schema"):
            if section_name in sections:
                raw_schema = sections[section_name]
                break
        if raw_schema is None:
            return {}, "Prompt 文件未内嵌可解析 JSON schema，不得编造 schema。"
        try:
            parsed = json.loads(raw_schema)
        except json.JSONDecodeError:
            return {}, "Prompt 文件内嵌 JSON schema 解析失败，不得编造 schema。"
        if not isinstance(parsed, dict):
            return {}, "Prompt 文件内嵌 JSON schema 不是 object，不得编造 schema。"
        return parsed, None
