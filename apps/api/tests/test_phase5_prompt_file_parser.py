from pathlib import Path

from app.models.enums import LLMPromptTaskType
from app.services.prompt_file_parser import PromptFileParserService


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_phase5_prompt_file_parser_scans_all_prompt_markdown_files() -> None:
    parsed_files = PromptFileParserService.scan_prompt_directory(REPO_ROOT / "prompts")

    source_paths = {item.source_file_path for item in parsed_files}
    assert source_paths == {"prompts/lead-extraction.md", "prompts/lead-grading.md"}

    task_types = {item.source_file_path: item.task_type for item in parsed_files}
    assert task_types["prompts/lead-extraction.md"] == LLMPromptTaskType.LEAD_EXTRACTION
    assert task_types["prompts/lead-grading.md"] == LLMPromptTaskType.LEAD_GRADING


def test_phase5_prompt_file_parser_hash_is_stable_for_same_content() -> None:
    prompt_path = REPO_ROOT / "prompts" / "lead-extraction.md"

    first = PromptFileParserService.parse_prompt_file(prompt_path, repo_root=REPO_ROOT)
    second = PromptFileParserService.parse_prompt_file(prompt_path, repo_root=REPO_ROOT)

    assert first.source_file_hash == second.source_file_hash
    assert len(first.source_file_hash) == 64


def test_phase5_prompt_file_parser_extracts_system_and_user_prompt_sections() -> None:
    parsed = PromptFileParserService.parse_prompt_file(REPO_ROOT / "prompts" / "lead-grading.md", repo_root=REPO_ROOT)

    assert parsed.name == "PoC AI 线索分级建议 Prompt"
    assert parsed.version == "lead-grading-v1"
    assert "你是海外车辆采购 AI 获客系统的线索分级助手" in parsed.system_prompt
    assert "{{lead_extraction_output_json}}" in parsed.user_prompt_template
    assert parsed.output_schema_json == {}
    assert parsed.validation_status == "validation_failed"
    assert parsed.validation_errors_json == {
        "output_schema_json": "Prompt 文件未内嵌可解析 JSON schema，不得编造 schema。"
    }


def test_phase5_prompt_file_parser_can_parse_embedded_json_schema() -> None:
    content = """# Email Reply Draft Prompt

## System Prompt

```text
system body
```

## User Prompt Template

```text
user body
```

## Output JSON Schema

```json
{"type": "object", "required": ["reply"]}
```
"""

    parsed = PromptFileParserService.parse_markdown_content(
        content,
        source_file_path="prompts/email-reply-draft.md",
    )

    assert parsed.task_type == LLMPromptTaskType.EMAIL_REPLY_DRAFT
    assert parsed.output_schema_json == {"type": "object", "required": ["reply"]}
    assert parsed.validation_status == "validation_passed"
    assert parsed.validation_errors_json is None
