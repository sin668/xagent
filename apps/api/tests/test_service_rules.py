from app.services.rules import (
    CustomerPolicyState,
    can_generate_outreach_draft,
    can_quote_or_contract,
    channel_block_reason,
    is_channel_allowed_for_automation,
    is_customer_allowed_in_outreach_queue,
)


def test_high_and_forbidden_channels_are_blocked() -> None:
    assert is_channel_allowed_for_automation("Low") is True
    assert is_channel_allowed_for_automation("Medium") is True
    assert is_channel_allowed_for_automation("High") is False
    assert is_channel_allowed_for_automation("Forbidden") is False
    assert "High 风险渠道" in channel_block_reason("High")
    assert "禁止执行" in channel_block_reason("Forbidden")


def test_do_not_contact_customer_is_excluded_from_outreach_queue() -> None:
    customer = CustomerPolicyState(customer_id="c-1", grade="B", do_not_contact=True)
    assert is_customer_allowed_in_outreach_queue(customer) is False
    assert can_generate_outreach_draft(customer, "Low") is False


def test_invalid_and_watch_are_excluded_from_outreach_queue() -> None:
    assert is_customer_allowed_in_outreach_queue(CustomerPolicyState(customer_id="c-1", grade="Invalid")) is False
    assert is_customer_allowed_in_outreach_queue(CustomerPolicyState(customer_id="c-2", grade="Watch")) is False


def test_c_grade_requires_compliance_approval_before_quote_or_contract() -> None:
    pending = CustomerPolicyState(customer_id="c-1", grade="C", compliance_review_status="pending")
    approved = CustomerPolicyState(customer_id="c-1", grade="C", compliance_review_status="approved")
    assert can_quote_or_contract(pending) is False
    assert can_quote_or_contract(approved) is True

