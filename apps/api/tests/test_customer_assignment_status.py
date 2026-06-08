from uuid import uuid4

from sqlalchemy import insert, select
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.models import ComplianceReview, Customer, ReviewLog
from app.models.enums import ComplianceReviewStatus, CustomerGrade, CustomerStatus, CustomerType
from app.services.customer_status import CustomerAssignmentStatusService


class FakeSession:
    def __init__(self, scalar_results=None):
        self.added = []
        self.flushed = False
        self.scalar_results = list(scalar_results or [])

    def add(self, item):
        self.added.append(item)

    def flush(self):
        self.flushed = True

    def scalar(self, statement):
        return self.scalar_results.pop(0) if self.scalar_results else None


def build_customer(**overrides) -> Customer:
    payload = {
        "id": uuid4(),
        "external_id": "TEST-P3-E3-S4-CUSTOMER",
        "name": "Ru Auto City",
        "normalized_name": "ru auto city",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "grade": CustomerGrade.B,
        "status": CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
        "owner": None,
        "owner_team": None,
        "do_not_contact": False,
    }
    payload.update(overrides)
    return Customer(**payload)


def test_customer_model_has_owner_team_for_assignment_persistence() -> None:
    columns = set(Base.metadata.tables["customers"].columns.keys())

    assert "owner" in columns
    assert "owner_team" in columns


def test_customer_owner_team_column_compiles_for_postgresql_insert() -> None:
    statement = insert(Customer).values(
        name="Ru Auto City",
        country="Russia",
        city="Moscow",
        customer_type=CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        grade=CustomerGrade.B,
        status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
        owner="cs-a",
        owner_team="customer_service",
        do_not_contact=False,
    )

    compiled = str(statement.compile(dialect=postgresql.dialect()))
    assert "owner_team" in compiled


def test_assign_owner_team_records_customer_assigned_audit_event() -> None:
    session = FakeSession()
    service = CustomerAssignmentStatusService(session)
    customer = build_customer(status=CustomerStatus.PENDING_REVIEW)

    updated = service.assign_owner(
        customer,
        owner="cs-a",
        team="customer_service",
        actor="ops-a",
        reason="A/B级客户交付客服首次触达",
    )

    assert updated.owner == "cs-a"
    assert updated.owner_team == "customer_service"
    assert updated.status == CustomerStatus.READY_FOR_CUSTOMER_SERVICE
    assert session.flushed is True
    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "customer_assigned"
    assert audit.reviewer == "ops-a"
    assert audit.task_id == str(customer.id)
    assert "owner=cs-a" in audit.input_ref
    assert "team=customer_service" in audit.input_ref
    assert audit.error_message == "A/B级客户交付客服首次触达"


def test_assign_owner_blocks_watch_invalid_and_do_not_contact_customers() -> None:
    service = CustomerAssignmentStatusService(FakeSession())

    for customer in (
        build_customer(grade=CustomerGrade.WATCH, status=CustomerStatus.WATCH),
        build_customer(grade=CustomerGrade.INVALID, status=CustomerStatus.INVALID),
        build_customer(do_not_contact=True, status=CustomerStatus.DO_NOT_CONTACT),
    ):
        try:
            service.assign_owner(customer, owner="cs-a", team="customer_service", actor="ops-a", reason="test")
        except ValueError as exc:
            assert "不得进入客户工作台或分配队列" in str(exc)
        else:
            raise AssertionError("Watch/Invalid/勿扰客户不得被分配")


def test_status_transition_allows_expected_customer_service_flow_and_audits() -> None:
    session = FakeSession()
    service = CustomerAssignmentStatusService(session)
    customer = build_customer(status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE, owner="cs-a", owner_team="customer_service")

    updated = service.transition_status(
        customer,
        to_status=CustomerStatus.CUSTOMER_SERVICE_FOLLOWING,
        actor="cs-a",
        reason="人工已完成首次触达",
    )

    assert updated.status == CustomerStatus.CUSTOMER_SERVICE_FOLLOWING
    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "customer_status_changed"
    assert "from=ready_for_customer_service" in audit.input_ref
    assert "to=customer_service_following" in audit.input_ref


def test_status_transition_rejects_invalid_jump() -> None:
    service = CustomerAssignmentStatusService(FakeSession())
    customer = build_customer(status=CustomerStatus.PENDING_REVIEW)

    try:
        service.transition_status(customer, to_status=CustomerStatus.QUOTED, actor="sales-a", reason="跳过承接流程")
    except ValueError as exc:
        assert "不允许的客户状态流转" in str(exc)
    else:
        raise AssertionError("不应允许从待复核直接进入报价")


def test_workbench_filter_excludes_watch_invalid_and_do_not_contact() -> None:
    customers = [
        build_customer(grade=CustomerGrade.A, status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE, do_not_contact=False),
        build_customer(grade=CustomerGrade.WATCH, status=CustomerStatus.WATCH, do_not_contact=False),
        build_customer(grade=CustomerGrade.INVALID, status=CustomerStatus.INVALID, do_not_contact=False),
        build_customer(grade=CustomerGrade.B, status=CustomerStatus.DO_NOT_CONTACT, do_not_contact=True),
    ]

    visible = CustomerAssignmentStatusService.filter_workbench_customers(customers)

    assert len(visible) == 1
    assert visible[0].grade == CustomerGrade.A


def test_c_grade_quote_status_requires_or_creates_pending_compliance_review() -> None:
    session = FakeSession()
    service = CustomerAssignmentStatusService(session)
    customer = build_customer(
        grade=CustomerGrade.C,
        status=CustomerStatus.READY_FOR_SALES,
        owner="sales-a",
        owner_team="sales",
    )

    try:
        service.transition_status(
            customer,
            to_status=CustomerStatus.QUOTED,
            actor="sales-a",
            reason="客户要求报价",
        )
    except ValueError as exc:
        assert "C级客户报价/合同前必须完成合规复核" in str(exc)
    else:
        raise AssertionError("C级客户合规复核通过前不得进入报价状态")

    review = next(item for item in session.added if isinstance(item, ComplianceReview))
    assert review.customer_id == customer.id
    assert review.status == ComplianceReviewStatus.PENDING
    assert "报价/合同前" in review.reason
    assert customer.status == CustomerStatus.READY_FOR_SALES
    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "customer_compliance_review_requested"
    assert audit.reviewer == "sales-a"
    assert audit.result == "blocked"
    assert "to=quoted" in audit.input_ref


def test_c_grade_quote_status_allows_when_compliance_review_is_approved() -> None:
    session = FakeSession()
    service = CustomerAssignmentStatusService(session)
    customer = build_customer(
        grade=CustomerGrade.C,
        status=CustomerStatus.READY_FOR_SALES,
        owner="sales-a",
        owner_team="sales",
    )
    review = ComplianceReview(
        customer_id=customer.id,
        status=ComplianceReviewStatus.APPROVED,
        reason="合规已批准报价",
        reviewer="compliance-a",
    )

    updated = service.transition_status(
        customer,
        to_status=CustomerStatus.QUOTED,
        actor="sales-a",
        reason="合规通过后报价",
        latest_compliance_review=review,
    )

    assert updated.status == CustomerStatus.QUOTED
    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "customer_status_changed"
    assert "to=quoted" in audit.input_ref


def test_workbench_query_contract_excludes_watch_invalid_and_dnc() -> None:
    statement = CustomerAssignmentStatusService.workbench_query(limit=50)
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))

    assert "customers.do_not_contact IS false" in compiled
    assert "watch" in compiled
    assert "invalid" in compiled
    assert "do_not_contact" in compiled
    assert "LIMIT 50" in compiled
