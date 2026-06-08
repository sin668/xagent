import pytest

from app.models import ComplianceReview, Customer
from app.models.enums import ComplianceReviewStatus, CustomerGrade, CustomerStatus, CustomerType
from app.models.enums import LeadCleanupSuggestionType
from app.services.compliance import ComplianceService
from app.services.customer_dnc import CustomerDncService
from app.services.permissions import Phase3Action, Phase3PermissionService


class FakeCustomerSession:
    def __init__(self, customer: Customer, review: ComplianceReview | None = None):
        self.customer = customer
        self.review = review
        self.added = []
        self.flushed = False

    def scalar(self, statement):
        text = str(statement)
        if "compliance_reviews" in text:
            return self.review
        if "customers" in text:
            return self.customer
        return None

    def add(self, item):
        self.added.append(item)
        if isinstance(item, ComplianceReview):
            self.review = item

    def flush(self):
        self.flushed = True


def build_customer(*, grade: CustomerGrade = CustomerGrade.B, status: CustomerStatus = CustomerStatus.READY_FOR_SALES) -> Customer:
    return Customer(
        name="Phase3 Dealer",
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        grade=grade,
        status=status,
        do_not_contact=status == CustomerStatus.DO_NOT_CONTACT,
    )


def test_phase3_permission_service_allows_restore_invalid_only_for_compliance_or_admin() -> None:
    Phase3PermissionService.ensure_allowed(
        Phase3Action.RESTORE_INVALID_OR_WATCH,
        actor_role="compliance",
    )
    Phase3PermissionService.ensure_allowed(
        Phase3Action.RESTORE_INVALID_OR_WATCH,
        actor_role="admin",
    )

    with pytest.raises(PermissionError, match="恢复 Invalid/Watch 仅允许合规或管理员"):
        Phase3PermissionService.ensure_allowed(
            Phase3Action.RESTORE_INVALID_OR_WATCH,
            actor_role="operations",
        )


def test_phase3_permission_service_allows_cancel_dnc_only_for_compliance_or_admin() -> None:
    Phase3PermissionService.ensure_allowed(
        Phase3Action.CANCEL_DO_NOT_CONTACT,
        actor_role="admin",
    )

    with pytest.raises(PermissionError, match="取消勿扰仅允许合规或管理员"):
        Phase3PermissionService.ensure_allowed(
            Phase3Action.CANCEL_DO_NOT_CONTACT,
            actor_role="customer_service",
        )


def test_phase3_permission_service_requires_admin_for_duplicate_and_customer_level_merge() -> None:
    for suggestion_type in (
        LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        LeadCleanupSuggestionType.MERGE_CONTACT_METHOD,
        LeadCleanupSuggestionType.MERGE_SOURCE_EVIDENCE,
    ):
        Phase3PermissionService.ensure_cleanup_review_allowed(suggestion_type, actor_role="admin")
        with pytest.raises(PermissionError, match="疑似重复和客户级归并仅允许管理员"):
            Phase3PermissionService.ensure_cleanup_review_allowed(suggestion_type, actor_role="operations")


def test_phase3_permission_service_requires_admin_to_execute_duplicate_and_customer_level_merge() -> None:
    for suggestion_type in (
        LeadCleanupSuggestionType.STRONG_DUPLICATE,
        LeadCleanupSuggestionType.POSSIBLE_DUPLICATE,
        LeadCleanupSuggestionType.MERGE_CONTACT_METHOD,
        LeadCleanupSuggestionType.MERGE_SOURCE_EVIDENCE,
    ):
        Phase3PermissionService.ensure_cleanup_execution_allowed(suggestion_type, actor_role="admin")
        with pytest.raises(PermissionError, match="重复线索和客户级归并执行仅允许管理员"):
            Phase3PermissionService.ensure_cleanup_execution_allowed(suggestion_type, actor_role="operations")


def test_phase3_permission_service_blocks_sales_or_cs_from_c_grade_quote_without_compliance_approval() -> None:
    for actor_role in ("sales", "customer_service"):
        with pytest.raises(PermissionError, match="客服/销售不能绕过 C 级合规复核"):
            Phase3PermissionService.ensure_c_grade_compliance_ready(
                actor_role=actor_role,
                compliance_approved=False,
            )

    Phase3PermissionService.ensure_c_grade_compliance_ready(
        actor_role="sales",
        compliance_approved=True,
    )


def test_customer_dnc_service_uses_permission_guard_for_cancel_do_not_contact() -> None:
    customer = build_customer(status=CustomerStatus.DO_NOT_CONTACT)
    service = CustomerDncService(FakeCustomerSession(customer))

    with pytest.raises(PermissionError, match="取消勿扰仅允许合规或管理员"):
        service.unmark_do_not_contact(
            customer_id=customer.id,
            unmarked_by="cs-a",
            actor_role="customer_service",
            reason="客服尝试取消勿扰",
        )

    updated = service.unmark_do_not_contact(
        customer_id=customer.id,
        unmarked_by="compliance-a",
        actor_role="compliance",
        reason="客户重新同意沟通",
    )

    assert updated.do_not_contact is False
    assert updated.status == CustomerStatus.PENDING_REVIEW
    assert updated.do_not_contact_reason == "取消勿扰：客户重新同意沟通"


def test_compliance_service_uses_permission_guard_for_c_grade_quote_before_review() -> None:
    customer = build_customer(grade=CustomerGrade.C)
    service = ComplianceService(FakeCustomerSession(customer))

    with pytest.raises(PermissionError, match="客服/销售不能绕过 C 级合规复核"):
        service.mark_quoted(customer_id=customer.id, actor="sales-a", actor_role="sales")

    review = ComplianceReview(
        customer_id=customer.id,
        status=ComplianceReviewStatus.APPROVED,
        reason="合规已批准",
        reviewer="compliance-a",
    )
    service = ComplianceService(FakeCustomerSession(customer, review))
    quoted = service.mark_quoted(customer_id=customer.id, actor="sales-a", actor_role="sales")

    assert quoted.status == CustomerStatus.QUOTED
    assert quoted.owner == "sales-a"
