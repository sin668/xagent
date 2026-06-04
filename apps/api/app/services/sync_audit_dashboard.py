from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIAuditLog, SyncLog
from app.models.enums import AITaskType


class SyncAuditDashboardService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def dashboard(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
        source_name: str | None = None,
        model_name: str | None = None,
    ) -> dict[str, object]:
        sync_logs = self._sync_logs(source_name=source_name)
        ai_logs = self._ai_logs(task_type=task_type, status=status, model_name=model_name)

        latest_sync_at = None
        if sync_logs:
            latest = max((item.finished_at or item.started_at for item in sync_logs), default=None)
            latest_sync_at = latest.isoformat() if latest else None

        return {
            "summary": {
                "latest_sync_at": latest_sync_at,
                "sync_success_count": sum(item.success_count for item in sync_logs),
                "sync_failure_count": sum(item.failure_count for item in sync_logs),
                "ai_task_count": len(ai_logs),
                "ai_blocked_count": sum(1 for item in ai_logs if item.risk_blocked),
            },
            "sync_logs": [self._serialize_sync_log(item) for item in sync_logs],
            "ai_audit_logs": [self._serialize_ai_log(item) for item in ai_logs],
        }

    def _sync_logs(self, *, source_name: str | None) -> list[SyncLog]:
        query = select(SyncLog).order_by(SyncLog.started_at.desc(), SyncLog.id.desc()).limit(30)
        if source_name:
            query = query.where(SyncLog.source_name == source_name)
        return list(self.session.scalars(query).all())

    def _ai_logs(
        self,
        *,
        task_type: str | None,
        status: str | None,
        model_name: str | None,
    ) -> list[AIAuditLog]:
        query = select(AIAuditLog).order_by(AIAuditLog.executed_at.desc(), AIAuditLog.id.desc()).limit(50)
        if task_type:
            query = query.where(AIAuditLog.task_type == AITaskType(task_type))
        if model_name:
            query = query.where(AIAuditLog.model_name == model_name)
        if status == "blocked":
            query = query.where(AIAuditLog.risk_blocked.is_(True))
        elif status == "succeeded":
            query = query.where(AIAuditLog.risk_blocked.is_(False))
        return list(self.session.scalars(query).all())

    @staticmethod
    def _serialize_sync_log(log: SyncLog) -> dict[str, object]:
        return {
            "id": str(log.id),
            "source_name": log.source_name,
            "object_name": log.object_name,
            "status": log.status.value,
            "success_count": log.success_count,
            "failure_count": log.failure_count,
            "error_summary": log.error_summary,
            "started_at": log.started_at.isoformat(),
            "finished_at": log.finished_at.isoformat() if log.finished_at else None,
        }

    @staticmethod
    def _serialize_ai_log(log: AIAuditLog) -> dict[str, object]:
        status = "blocked" if log.risk_blocked else "succeeded"
        return {
            "id": str(log.id),
            "customer_id": str(log.customer_id) if log.customer_id else None,
            "task_type": log.task_type.value,
            "model_name": log.model_name,
            "prompt_version": log.prompt_version,
            "channel_name": log.channel_name,
            "source_url": log.source_url,
            "status": status,
            "risk": "blocked" if log.risk_blocked else "normal",
            "risk_blocked": log.risk_blocked,
            "risk_block_reason": log.risk_block_reason,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "total_tokens": log.total_tokens,
            "cost_amount": float(log.cost_amount) if log.cost_amount is not None else None,
            "cost_currency": log.cost_currency,
            "executed_at": log.executed_at.isoformat(),
        }
