from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.staging_leads import StagingLeadResponse


class LLMLeadExtractionRunRequest(BaseModel):
    candidate_url_id: UUID
    llm_output_json: dict = Field(description="符合 lead_extraction_output 的 LLM JSON 输出。")


class LLMLeadExtractionRunResponse(BaseModel):
    staging_lead: StagingLeadResponse

