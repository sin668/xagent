from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FailedCase
from app.models.enums import ChannelRiskLevel, FailedCaseType


class FailedCaseService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def classify_failure_reason(reason: str | None) -> FailedCaseType:
        text = (reason or "").lower()
        if any(term in text for term in ("fetch", "读取失败", "timeout", "timed out", "connection")):
            return FailedCaseType.FETCH_FAILED
        if any(term in text for term in ("缺少来源证据", "missing evidence", "evidence_refs 不得为空")):
            return FailedCaseType.MISSING_EVIDENCE
        if any(term in text for term in ("不在公开文本中", "fabrication", "suspected fabrication", "疑似编造")):
            return FailedCaseType.LLM_SUSPECTED_FABRICATION
        if any(term in text for term in ("high/forbidden", "风险阻断", "risk_blocked", "不得写入 staging")):
            return FailedCaseType.RISK_BLOCKED
        if any(term in text for term in ("duplicate", "重复", "强重复")):
            return FailedCaseType.DUPLICATE
        return FailedCaseType.SCHEMA_INVALID

    @staticmethod
    def build_failed_case_payload(
        *,
        case_type: str | FailedCaseType,
        source_url: str | None,
        risk_level: str | ChannelRiskLevel | None,
        related_task_type: str | None,
        related_object_type: str | None,
        related_object_id: str | None,
        failure_reason: str,
        evidence_note: str | None = None,
        raw_input_ref: str | None = None,
        raw_output_json: dict | None = None,
        model_name: str | None = None,
        prompt_version: str | None = None,
        usable_for_rag: bool = True,
    ) -> dict:
        return {
            "case_type": FailedCaseType(case_type),
            "source_url": source_url,
            "risk_level": ChannelRiskLevel(risk_level) if risk_level is not None else None,
            "related_task_type": related_task_type,
            "related_object_type": related_object_type,
            "related_object_id": related_object_id,
            "failure_reason": failure_reason,
            "evidence_note": evidence_note,
            "raw_input_ref": raw_input_ref,
            "raw_output_json": raw_output_json,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "usable_for_rag": usable_for_rag,
            "touch_queue_allowed": False,
        }

    def record_failed_case(self, **payload) -> FailedCase:
        record = FailedCase(
            **self.build_failed_case_payload(**payload),
            created_at=datetime.utcnow(),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_failed_cases(
        self,
        *,
        case_type: str | FailedCaseType | None = None,
        usable_for_rag: bool | None = None,
        limit: int = 100,
    ) -> list[FailedCase]:
        statement = select(FailedCase).order_by(FailedCase.created_at.desc()).limit(limit)
        if case_type is not None:
            statement = statement.where(FailedCase.case_type == FailedCaseType(case_type))
        if usable_for_rag is not None:
            statement = statement.where(FailedCase.usable_for_rag.is_(usable_for_rag))
        return list(self.session.scalars(statement).all())
