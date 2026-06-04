from uuid import UUID

from pydantic import BaseModel, Field


class ChannelPlanCreate(BaseModel):
    country: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=120)
    channel_name: str = Field(min_length=1, max_length=120)
    channel_type: str = Field(min_length=1, max_length=80)
    risk_level: str = Field(pattern="^(Low|Medium|High|Forbidden)$")
    keywords: list[str] = Field(default_factory=list)
    daily_url_limit: int = Field(gt=0)
    daily_lead_limit: int | None = Field(default=None, gt=0)
    status: str = Field(default="draft", pattern="^(draft|enabled|paused|archived)$")
    owner: str | None = Field(default=None, max_length=120)
    source_usage_type: str | None = Field(
        default=None,
        pattern="^(automatic_collection|public_discovery_only|manual_sample|policy_research)$",
    )


class ChannelPlanUpdate(BaseModel):
    country: str | None = Field(default=None, min_length=1, max_length=80)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    channel_name: str | None = Field(default=None, min_length=1, max_length=120)
    channel_type: str | None = Field(default=None, min_length=1, max_length=80)
    risk_level: str | None = Field(default=None, pattern="^(Low|Medium|High|Forbidden)$")
    keywords: list[str] | None = None
    daily_url_limit: int | None = Field(default=None, gt=0)
    daily_lead_limit: int | None = Field(default=None, gt=0)
    status: str | None = Field(default=None, pattern="^(draft|enabled|paused|archived)$")
    owner: str | None = Field(default=None, max_length=120)
    resolution_note: str | None = None
    resolved_by: str | None = Field(default=None, max_length=120)
    source_usage_type: str | None = Field(
        default=None,
        pattern="^(automatic_collection|public_discovery_only|manual_sample|policy_research)$",
    )


class ChannelPlanResponse(BaseModel):
    id: UUID
    country: str
    city: str
    channel_name: str
    channel_type: str
    risk_level: str
    source_usage_type: str
    keywords: list[str]
    daily_url_limit: int
    daily_lead_limit: int | None
    status: str
    owner: str | None
    created_at: str
    updated_at: str


class ChannelPlanListResponse(BaseModel):
    items: list[ChannelPlanResponse]
