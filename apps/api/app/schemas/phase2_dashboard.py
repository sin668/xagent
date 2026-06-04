from pydantic import BaseModel, Field


class Phase2DashboardSummary(BaseModel):
    source_candidate_count: int
    review_backlog_count: int
    auto_extraction_count: int
    agent_task_count: int
    failed_task_count: int
    llm_cost_total: float
    risk_event_count: int
    high_forbidden_risk_event_count: int


class Phase2FailureReasonItem(BaseModel):
    reason: str
    count: int
    agent_task_run_ids: list[str] = Field(default_factory=list)


class Phase2LLMCostItem(BaseModel):
    agent_task_run_id: str
    task_type: str
    status: str
    model: str | None = None
    prompt_version: str | None = None
    cost_amount: float
    cost_currency: str
    total_tokens: int


class Phase2LLMCosts(BaseModel):
    total_cost: float
    currency: str
    items: list[Phase2LLMCostItem]


class Phase2RiskEventItem(BaseModel):
    id: str
    task_id: str | None = None
    channel: str
    risk_level: str
    severity: str
    resolution_status: str
    event_type: str
    block_reason: str | None = None
    pause_suggested: bool
    created_at: str


class Phase2DashboardResponse(BaseModel):
    summary: Phase2DashboardSummary
    risk_distribution: dict[str, int]
    review_backlog: dict[str, int]
    extraction_status_distribution: dict[str, int]
    failure_reasons: list[Phase2FailureReasonItem]
    llm_costs: Phase2LLMCosts
    high_forbidden_risk_events: list[Phase2RiskEventItem]
    guardrail: str
