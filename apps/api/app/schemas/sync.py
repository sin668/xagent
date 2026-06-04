from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    object_names: list[str] | None = Field(
        default=None,
        description="Optional subset of Feishu table object names to sync.",
    )
    dry_run: bool = Field(default=True, description="When true, only validate and plan records without database writes.")


class SyncObjectResult(BaseModel):
    object_name: str
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    errors: list[str] = Field(default_factory=list)


class SyncResponse(BaseModel):
    status: str
    dry_run: bool
    results: list[SyncObjectResult]


class SyncAuditSummary(BaseModel):
    latest_sync_at: str | None = None
    sync_success_count: int
    sync_failure_count: int
    ai_task_count: int
    ai_blocked_count: int


class SyncAuditSyncLogItem(BaseModel):
    id: str
    source_name: str
    object_name: str
    status: str
    success_count: int
    failure_count: int
    error_summary: str | None = None
    started_at: str
    finished_at: str | None = None


class SyncAuditAiLogItem(BaseModel):
    id: str
    customer_id: str | None = None
    task_type: str
    model_name: str
    prompt_version: str
    channel_name: str | None = None
    source_url: str | None = None
    status: str
    risk: str
    risk_blocked: bool
    risk_block_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_amount: float | None = None
    cost_currency: str | None = None
    executed_at: str


class SyncAuditDashboardResponse(BaseModel):
    summary: SyncAuditSummary
    sync_logs: list[SyncAuditSyncLogItem]
    ai_audit_logs: list[SyncAuditAiLogItem]
