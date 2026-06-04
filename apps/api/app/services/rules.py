from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    FORBIDDEN = "Forbidden"


class Grade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    INVALID = "Invalid"
    WATCH = "Watch"


@dataclass(frozen=True)
class CustomerPolicyState:
    customer_id: str
    grade: str
    do_not_contact: bool = False
    compliance_review_status: str | None = None


def is_channel_allowed_for_automation(risk_level: str) -> bool:
    return risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}


def channel_block_reason(risk_level: str) -> str | None:
    if risk_level == RiskLevel.HIGH:
        return "High 风险渠道只允许政策研究和人工小样本，不进入自动任务。"
    if risk_level == RiskLevel.FORBIDDEN:
        return "Forbidden 渠道或行为禁止执行。"
    return None


def is_customer_allowed_in_outreach_queue(customer: CustomerPolicyState) -> bool:
    if customer.do_not_contact:
        return False
    if customer.grade in {Grade.INVALID, Grade.WATCH}:
        return False
    return customer.grade in {Grade.B, Grade.C}


def can_generate_outreach_draft(customer: CustomerPolicyState, risk_level: str) -> bool:
    return is_channel_allowed_for_automation(risk_level) and is_customer_allowed_in_outreach_queue(customer)


def can_quote_or_contract(customer: CustomerPolicyState) -> bool:
    if customer.grade != Grade.C:
        return True
    return customer.compliance_review_status == "approved"

