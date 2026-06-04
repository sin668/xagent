from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.staging_leads import StagingLeadResponse


class LLMLeadGradingRunRequest(BaseModel):
    staging_lead_id: UUID
    llm_output_json: dict = Field(description="符合 lead_grading_output 的 LLM JSON 输出。")
    do_not_contact: bool = False


class LLMLeadGradingRunResponse(BaseModel):
    staging_lead: StagingLeadResponse
    rule_validation_result: dict

