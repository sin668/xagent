from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


DEFAULT_MAX_RETRIES = 2

RETRYABLE_ERROR_TYPES = {
    "timeout_error",
    "provider_rate_limited",
    "transient_network_error",
}

NON_RETRYABLE_ERROR_TYPES = {
    "schema_validation_error",
    "evidence_validation_error",
    "risk_blocked",
    "contract_mismatch",
}


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    next_retry_at: datetime | None
    terminal_status: str | None = None


class RetryPolicy:
    def __init__(self, *, max_retries: int = DEFAULT_MAX_RETRIES, base_delay_seconds: int = 60) -> None:
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds

    def decide(self, *, error_type: str, retry_count: int, now: datetime | None = None) -> RetryDecision:
        current_time = now or datetime.now(UTC)
        if not is_retryable_error(error_type) or retry_count >= self.max_retries:
            return RetryDecision(should_retry=False, next_retry_at=None, terminal_status="failed")

        next_retry_count = retry_count + 1
        delay = timedelta(seconds=self.base_delay_seconds * next_retry_count)
        return RetryDecision(should_retry=True, next_retry_at=current_time + delay)


def is_retryable_error(error_type: str) -> bool:
    return error_type in RETRYABLE_ERROR_TYPES
