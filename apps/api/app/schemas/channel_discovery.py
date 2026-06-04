from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.raw_collection import CandidateUrlResponse, CollectionTaskResponse


class ChannelDiscoveryRunRequest(BaseModel):
    plan_id: UUID
    max_candidates: int | None = Field(default=None, gt=0, le=500)


class ChannelDiscoveryRunResponse(BaseModel):
    task: CollectionTaskResponse
    candidates: list[CandidateUrlResponse]
    created_count: int
    updated_count: int

