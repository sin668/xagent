from pydantic import BaseModel
from pydantic import Field


class ChannelLeadDashboardSummary(BaseModel):
    candidate_count: int
    b_grade_count: int
    c_grade_count: int
    bc_grade_count: int
    invalid_count: int
    invalid_rate: float


class ChannelLeadDashboardItem(BaseModel):
    channel_name: str
    display_name: str
    risk_level: str
    risk_status: str
    investment_recommendation: str
    candidate_count: int
    b_grade_count: int
    c_grade_count: int
    bc_grade_count: int
    invalid_count: int
    invalid_rate: float


class ChannelLeadDashboardResponse(BaseModel):
    summary: ChannelLeadDashboardSummary
    channels: list[ChannelLeadDashboardItem]


class PhaseOneFunnelSummary(BaseModel):
    candidate_url_count: int
    staging_lead_count: int
    core_customer_count: int
    core_valid_lead_count: int
    touchable_effective_lead_count: int
    high_readonly_excluded_count: int
    do_not_contact_excluded_count: int
    daily_candidate_target: int
    candidate_target_completion_rate: float
    candidate_target_met: bool


class PhaseOneFunnelDailyItem(PhaseOneFunnelSummary):
    date: str


class PhaseOneFunnelChannelItem(BaseModel):
    channel_name: str
    display_name: str
    risk_level: str
    candidate_url_count: int
    staging_lead_count: int
    core_customer_count: int
    core_valid_lead_count: int
    touchable_effective_lead_count: int
    high_readonly_excluded_count: int
    do_not_contact_excluded_count: int


class PhaseOneFunnelFilters(BaseModel):
    date_from: str | None = None
    date_to: str | None = None
    channel: str | None = None
    risk_level: str | None = None


class PhaseOneFunnelDashboardResponse(BaseModel):
    summary: PhaseOneFunnelSummary
    daily: list[PhaseOneFunnelDailyItem]
    channels: list[PhaseOneFunnelChannelItem]
    filters: PhaseOneFunnelFilters
    guardrail: str


class ChannelQualitySummary(BaseModel):
    candidate_url_count: int
    staging_lead_count: int
    core_customer_count: int
    bc_grade_count: int
    invalid_watch_count: int
    duplicate_count: int
    risk_event_count: int
    bc_rate: float
    duplicate_rate: float


class ChannelQualityItem(BaseModel):
    channel_name: str
    display_name: str
    risk_category: str
    candidate_url_count: int
    staging_lead_count: int
    core_customer_count: int
    a_grade_count: int
    b_grade_count: int
    c_grade_count: int
    bc_grade_count: int
    invalid_count: int
    watch_count: int
    invalid_watch_count: int
    bc_rate: float
    contact_completeness_rate: float
    evidence_completeness_rate: float
    duplicate_count: int
    duplicate_rate: float
    high_secondary_review_required_count: int
    high_secondary_review_passed_count: int
    high_secondary_review_pass_rate: float
    risk_event_count: int
    pause_suggested_count: int
    quality_conclusion: str


class ChannelQualityDashboardResponse(BaseModel):
    summary: ChannelQualitySummary
    channels: list[ChannelQualityItem]
    filters: PhaseOneFunnelFilters
    guardrail: str


class RiskEventDashboardSummary(BaseModel):
    risk_event_count: int
    open_risk_event_count: int
    investigating_risk_event_count: int
    resolved_risk_event_count: int
    dismissed_risk_event_count: int
    critical_risk_event_count: int
    high_risk_event_count: int
    pause_suggested_count: int
    paused_channel_plan_count: int


class RiskEventDashboardEventItem(BaseModel):
    id: str
    channel_plan_id: str | None = None
    channel_name: str
    risk_level: str
    severity: str
    resolution_status: str
    event_type: str
    block_reason: str | None = None
    pause_suggested: bool
    task_id: str | None = None
    agent_name: str | None = None
    action: str | None = None
    result: str
    resolution_note: str | None = None
    resolved_by: str | None = None
    created_at: str
    resolved_at: str | None = None


class RiskEventDashboardPausedChannelPlanItem(BaseModel):
    id: str
    country: str
    city: str
    channel_name: str
    channel_type: str
    risk_level: str
    status: str
    owner: str | None = None
    daily_url_limit: int
    daily_lead_limit: int | None = None
    latest_block_reason: str | None = None
    latest_event_status: str | None = None
    latest_event_severity: str | None = None
    latest_event_created_at: str | None = None
    resume_requires_resolution_note: bool
    keywords: list[str] = Field(default_factory=list)


class RiskEventDashboardFilters(BaseModel):
    date_from: str | None = None
    date_to: str | None = None
    channel: str | None = None
    risk_level: str | None = None
    severity: str | None = None
    resolution_status: str | None = None


class RiskEventDashboardResponse(BaseModel):
    summary: RiskEventDashboardSummary
    events: list[RiskEventDashboardEventItem]
    paused_channel_plans: list[RiskEventDashboardPausedChannelPlanItem]
    filters: RiskEventDashboardFilters
    guardrail: str


class OutreachSlaDashboardSummary(BaseModel):
    sent_count: int
    replied_count: int
    response_rate: float
    pending_count: int
    overdue_count: int
    compliance_waiting_count: int
    sla_risk_count: int


class OutreachSlaQueueItem(BaseModel):
    customer_id: str
    customer_name: str
    grade: str
    owner: str | None = None
    status: str
    sla_hours: int
    waiting_hours: float
    risk_status: str
    compliance_status: str | None = None
    next_action: str


class OutreachSlaDashboardResponse(BaseModel):
    summary: OutreachSlaDashboardSummary
    queue: list[OutreachSlaQueueItem]


class RoiCostCreateRequest(BaseModel):
    external_id: str | None = None
    cost_type: str = Field(pattern="^(labor|ai_api|tool)$")
    amount: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    labor_hours: float | None = Field(default=None, ge=0)
    hourly_rate: float | None = Field(default=None, ge=0)
    channel_name: str | None = None
    notes: str | None = None


class RoiCostResponse(BaseModel):
    id: str
    external_id: str | None = None
    cost_type: str
    amount: float
    currency: str
    labor_hours: float | None = None
    hourly_rate: float | None = None
    channel_name: str | None = None
    notes: str | None = None


class RoiMetricsSummary(BaseModel):
    total_cost: float
    labor_cost: float
    ai_api_cost: float
    tool_cost: float
    effective_lead_count: int
    reply_count: int
    sales_opportunity_count: int
    cost_per_effective_lead: float | None = None
    cost_per_reply: float | None = None
    cost_per_sales_opportunity: float | None = None
    llm_call_count: int
    llm_failure_count: int
    llm_failure_rate: float
    llm_token_count: int
    llm_cost_total: float
    review_completed_count: int
    avg_review_duration_hours: float | None = None
    ai_cost_per_effective_lead: float | None = None


class RoiMetricsResponse(BaseModel):
    summary: RoiMetricsSummary
    compliance_guardrail: str


class AdminOverviewSummary(BaseModel):
    candidate_count: int
    b_grade_count: int
    c_grade_count: int
    bc_grade_count: int
    response_rate: float
    sla_risk_count: int


class AdminOverviewQueueItem(BaseModel):
    customer_id: str
    customer_name: str
    grade: str
    status: str
    owner: str | None = None
    updated_at: str


class AdminOverviewQueue(BaseModel):
    count: int
    items: list[AdminOverviewQueueItem]


class AdminOverviewTeamQueues(BaseModel):
    operations: AdminOverviewQueue
    customer_service: AdminOverviewQueue
    sales: AdminOverviewQueue


class AdminOverviewRiskEvent(BaseModel):
    id: str
    customer_id: str | None = None
    task_type: str
    model_name: str
    prompt_version: str
    source_url: str | None = None
    risk_blocked: bool
    risk_block_reason: str | None = None
    executed_at: str


class AdminOverviewResponse(BaseModel):
    summary: AdminOverviewSummary
    channel_outputs: list[ChannelLeadDashboardItem]
    team_queues: AdminOverviewTeamQueues
    risk_events: list[AdminOverviewRiskEvent]
    blocked_tasks: list[AdminOverviewRiskEvent]
