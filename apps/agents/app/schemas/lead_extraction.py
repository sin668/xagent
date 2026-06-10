from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


LeadExtractionFieldName = Literal[
    "company_name",
    "email",
    "phone",
    "country",
    "city",
    "vehicle_interest",
    "export_intent",
    "website",
]


class FieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: Literal["source_content", "source_url"]
    quote: str = Field(min_length=1)


class ExtractedLeadField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: LeadExtractionFieldName
    value: str | None = None
    evidence: FieldEvidence | None = None
    missing_reason: str | None = None

    @model_validator(mode="after")
    def require_evidence_or_missing_reason(self) -> "ExtractedLeadField":
        if self.value and self.evidence is None:
            raise ValueError(f"字段 {self.field_name} 必须包含证据引用或缺失原因。")
        if self.value is None and not self.missing_reason:
            raise ValueError(f"字段 {self.field_name} 必须包含证据引用或缺失原因。")
        return self


LeadContactType = Literal[
    "email",
    "phone",
    "whatsapp",
    "telegram",
    "vk",
    "vkontakte",
    "ok",
    "odnoklassniki",
    "tiktok",
    "max",
    "website",
    "other",
]


class ExtractedContact(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    contact_type: LeadContactType = Field(validation_alias=AliasChoices("contact_type", "type"))
    value: str = Field(min_length=1)
    usage: str | None = "source_public_contact"
    evidence: FieldEvidence | None = None


class LeadExtractionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str = Field(min_length=1)
    company_name: ExtractedLeadField
    email: ExtractedLeadField
    phone: ExtractedLeadField
    country: ExtractedLeadField
    city: ExtractedLeadField
    vehicle_interest: ExtractedLeadField
    export_intent: ExtractedLeadField
    website: ExtractedLeadField
    contacts: list[ExtractedContact] = Field(default_factory=list)
    audit_status: Literal["shadow_only"] = "shadow_only"


class LeadExtractionAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase4.agent.lead_extraction.v1"]
    extraction_run_id: UUID | str
    agent_mode: Literal["active", "shadow"] = "shadow"
    candidates: list[LeadExtractionCandidate] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    audit: dict = Field(default_factory=dict)
