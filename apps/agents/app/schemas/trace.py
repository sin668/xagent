from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SENSITIVE_TRACE_KEYS = {
    "api_key",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
}


def redact_trace_summary(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_TRACE_KEYS:
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = redact_trace_summary(item)
        return redacted
    if isinstance(value, list):
        return [redact_trace_summary(item) for item in value]
    return value


class AgentNodeTraceError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool


class AgentNodeTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node: str = Field(min_length=1, max_length=120)
    status: Literal["succeeded", "failed", "blocked", "skipped"]
    duration_ms: int = Field(ge=0)
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    error: AgentNodeTraceError | None = None

    @field_validator("input_summary", "output_summary", mode="before")
    @classmethod
    def redact_sensitive_summary(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("trace summary must be a dict")
        return redact_trace_summary(value)


class AgentRunTraceAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    writes_core_tables: bool = False
    executed_nodes: list[AgentNodeTrace] = Field(default_factory=list)
    failed_node: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_core_table_writes(self) -> "AgentRunTraceAudit":
        if self.writes_core_tables:
            raise ValueError("Agent trace audit must not allow core table writes.")
        return self
