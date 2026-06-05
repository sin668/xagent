from pydantic import BaseModel, Field

from app.models.enums import CustomerStatus


class CustomerAssignRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=120)
    team: str = Field(min_length=1, max_length=80)
    actor: str = Field(min_length=1, max_length=120)
    reason: str | None = None


class CustomerStatusTransitionRequest(BaseModel):
    to_status: CustomerStatus
    actor: str = Field(min_length=1, max_length=120)
    actor_role: str = Field(default="operations", min_length=1, max_length=80)
    reason: str | None = None
