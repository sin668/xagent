from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


class SourceDiscoveryValidationError(ValueError):
    def __init__(self, message: str, *, error_type: str = "schema_validation_error") -> None:
        super().__init__(message)
        self.error_type = error_type


@dataclass(frozen=True)
class SourceDiscoveryValidationResult:
    valid: bool
    normalized_output: dict[str, Any]
    candidates: list[dict[str, Any]]
    blocked_candidates: list[dict[str, Any]]
    error: dict[str, str] | None = None


class SourceDiscoverySchemaService:
    TOP_LEVEL_REQUIRED = ("task_type", "country", "city", "channel_strategy", "candidates", "blocked_candidates")
    CANDIDATE_REQUIRED = ("source_url", "platform", "risk_level", "discovery_reason", "evidence_note")
    ALLOWED_RISK_LEVELS = {"Low", "Medium", "High", "Forbidden"}
    AUTO_EXTRACTABLE_RISK_LEVELS = {"Low", "Medium"}

    @classmethod
    def validate_output(cls, output: dict[str, Any]) -> SourceDiscoveryValidationResult:
        if not isinstance(output, dict):
            raise SourceDiscoveryValidationError("Source Discovery 输出必须是 JSON object。")

        normalized = copy.deepcopy(output)
        cls._validate_top_level(normalized)

        candidates = cls._validate_candidates(normalized["candidates"])
        blocked_candidates = cls._validate_blocked_candidates(normalized["blocked_candidates"])
        normalized["candidates"] = candidates
        normalized["blocked_candidates"] = [
            {key: value for key, value in item.items() if key != "approved_for_extraction"}
            for item in blocked_candidates
        ]

        return SourceDiscoveryValidationResult(
            valid=True,
            normalized_output=normalized,
            candidates=candidates,
            blocked_candidates=blocked_candidates,
        )

    @classmethod
    def _validate_top_level(cls, output: dict[str, Any]) -> None:
        for field_name in cls.TOP_LEVEL_REQUIRED:
            if field_name not in output:
                raise SourceDiscoveryValidationError(f"Source Discovery 输出缺少必填字段：{field_name}")

        if output["task_type"] != "SOURCE_DISCOVERY":
            raise SourceDiscoveryValidationError("Source Discovery 输出 task_type 必须为 SOURCE_DISCOVERY。")
        if not isinstance(output["country"], str) or not output["country"].strip():
            raise SourceDiscoveryValidationError("Source Discovery 输出 country 必须是非空字符串。")
        if output["city"] is not None and not isinstance(output["city"], str):
            raise SourceDiscoveryValidationError("Source Discovery 输出 city 必须是字符串、null 或 Unknown。")
        if not isinstance(output["channel_strategy"], str) or not output["channel_strategy"].strip():
            raise SourceDiscoveryValidationError("Source Discovery 输出 channel_strategy 必须是非空字符串。")
        if not isinstance(output["candidates"], list):
            raise SourceDiscoveryValidationError("Source Discovery 输出 candidates 必须是数组。")
        if not isinstance(output["blocked_candidates"], list):
            raise SourceDiscoveryValidationError("Source Discovery 输出 blocked_candidates 必须是数组。")

    @classmethod
    def _validate_candidates(cls, candidates: list[Any]) -> list[dict[str, Any]]:
        normalized_candidates: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise SourceDiscoveryValidationError(f"candidates[{index}] 必须是 object。")
            for field_name in cls.CANDIDATE_REQUIRED:
                if field_name not in candidate:
                    raise SourceDiscoveryValidationError(f"candidates[{index}] 缺少必填字段：{field_name}")

            risk_level = candidate["risk_level"]
            if risk_level not in cls.ALLOWED_RISK_LEVELS:
                raise SourceDiscoveryValidationError(f"candidates[{index}].risk_level 非法：{risk_level}")
            if risk_level == "Forbidden":
                raise SourceDiscoveryValidationError("Forbidden 来源不得进入 candidates，必须进入 blocked_candidates。")

            cls._validate_required_text(candidate, index=index, field_name="source_url")
            cls._validate_required_text(candidate, index=index, field_name="platform")
            cls._validate_required_text(candidate, index=index, field_name="discovery_reason")
            cls._validate_required_text(candidate, index=index, field_name="evidence_note")

            if risk_level == "High" and candidate.get("approved_for_extraction") is True:
                raise SourceDiscoveryValidationError("High 风险来源不得自动抽取，approved_for_extraction 必须为 false。")

            normalized_candidates.append(candidate)
        return normalized_candidates

    @classmethod
    def _validate_blocked_candidates(cls, blocked_candidates: list[Any]) -> list[dict[str, Any]]:
        normalized_blocked: list[dict[str, Any]] = []
        for index, blocked in enumerate(blocked_candidates):
            if not isinstance(blocked, dict):
                raise SourceDiscoveryValidationError(f"blocked_candidates[{index}] 必须是 object。")
            for field_name in ("source_url", "risk_level", "blocked_reason"):
                if field_name not in blocked:
                    raise SourceDiscoveryValidationError(f"blocked_candidates[{index}] 缺少必填字段：{field_name}")
            cls._validate_required_text(blocked, index=index, field_name="source_url", prefix="blocked_candidates")
            cls._validate_required_text(blocked, index=index, field_name="blocked_reason", prefix="blocked_candidates")
            if blocked["risk_level"] not in {"Forbidden", "High"}:
                raise SourceDiscoveryValidationError(
                    f"blocked_candidates[{index}].risk_level 必须为 Forbidden 或 High。"
                )

            normalized = dict(blocked)
            normalized["approved_for_extraction"] = False
            normalized_blocked.append(normalized)
        return normalized_blocked

    @staticmethod
    def _validate_required_text(
        record: dict[str, Any],
        *,
        index: int,
        field_name: str,
        prefix: str = "candidates",
    ) -> None:
        value = record.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise SourceDiscoveryValidationError(f"{prefix}[{index}].{field_name} 必须是非空字符串。")
