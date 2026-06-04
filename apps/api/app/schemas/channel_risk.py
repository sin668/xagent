from pydantic import BaseModel, Field, HttpUrl


class ChannelRiskRuleUpsert(BaseModel):
    channel_type: str = Field(min_length=1)
    risk_level: str = Field(pattern="^(Low|Medium|High|Forbidden)$")
    allowed_actions: str = Field(min_length=1)
    forbidden_actions: str = Field(min_length=1)
    policy_source_url: HttpUrl | None = None
    notes: str | None = None
    external_id: str | None = None
    collection_allowed: bool | None = None
    updated_by: str | None = Field(default=None, max_length=120)


class ChannelRiskRuleResponse(BaseModel):
    channel_name: str
    channel_type: str
    risk_level: str
    collection_allowed: bool
    ai_processing_allowed: bool
    allowed_actions: str
    forbidden_actions: str
    policy_source_url: str | None = None
    notes: str | None = None
    updated_by: str | None = None
    updated_at: str


class ChannelRiskRuleListResponse(BaseModel):
    items: list[ChannelRiskRuleResponse]


class ChannelRiskEvaluateRequest(BaseModel):
    channel_name: str = Field(min_length=1)
    task_type: str = Field(pattern="^(lead_extraction|lead_grading|outreach_draft|inventory_matching|risk_block)$")
    requested_action: str = Field(min_length=1)
    source_usage_type: str | None = Field(
        default=None,
        pattern="^(automatic_collection|public_discovery_only|manual_sample|policy_research)$",
    )
    source_url: str | None = None
    model_name: str = Field(default="unknown")
    prompt_version: str = Field(default="unknown")


class ChannelRiskDecisionResponse(BaseModel):
    allowed: bool
    channel_name: str
    risk_level: str
    block_reason: str | None = None
    audit_logged: bool
