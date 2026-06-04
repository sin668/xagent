from uuid import UUID

from pydantic import BaseModel, Field


class CollectionTaskCreate(BaseModel):
    plan_id: UUID | None = None
    task_type: str = Field(min_length=1, max_length=80)
    channel_name: str = Field(min_length=1, max_length=120)
    risk_level: str = Field(pattern="^(Low|Medium|High|Forbidden)$")
    source_usage_type: str | None = Field(default=None)
    max_sample_size: int | None = Field(default=None, gt=0)
    allowed_actions: str = Field(min_length=1)
    forbidden_actions: str = Field(min_length=1)


class CollectionTaskResponse(BaseModel):
    id: UUID
    plan_id: UUID | None
    task_type: str
    channel_name: str
    risk_level: str
    source_usage_type: str
    max_sample_size: int | None
    allowed_actions: str
    forbidden_actions: str
    status: str
    started_at: str | None
    finished_at: str | None
    error_message: str | None
    created_at: str


class CollectionTaskListResponse(BaseModel):
    items: list[CollectionTaskResponse]


class CandidateUrlUpsert(BaseModel):
    task_id: UUID
    url: str = Field(min_length=1)
    source_platform: str = Field(min_length=1)
    source_risk_level: str = Field(pattern="^(Low|Medium|High|Forbidden)$")
    source_usage_type: str | None = None
    discovery_reason: str = Field(min_length=1)


class CandidateUrlResponse(BaseModel):
    id: UUID
    task_id: UUID
    url: str
    url_hash: str
    source_platform: str
    source_risk_level: str
    source_usage_type: str
    requires_secondary_verification: bool
    queue_eligible: bool
    discovery_reason: str
    status: str
    created: bool | None = None
    created_at: str
    updated_at: str


class CandidateUrlListResponse(BaseModel):
    items: list[CandidateUrlResponse]


class PageSnapshotCreate(BaseModel):
    candidate_url_id: UUID
    page_title: str | None = Field(default=None, max_length=255)
    text_excerpt: str | None = None
    evidence_note: str | None = None
    read_status: str = Field(pattern="^(success|blocked|failed|needs_manual_review|captcha|login_wall|access_error|policy_wall)$")
    robots_or_policy_note: str | None = None


class PageSnapshotResponse(BaseModel):
    id: UUID
    candidate_url_id: UUID
    page_title: str | None
    text_excerpt: str | None
    evidence_note: str
    read_status: str
    captured_at: str
    robots_or_policy_note: str | None
    created_at: str
    latest_for_candidate_id: UUID | None = None


class PageSnapshotListResponse(BaseModel):
    items: list[PageSnapshotResponse]
