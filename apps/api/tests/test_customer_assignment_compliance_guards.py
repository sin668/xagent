from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import ComplianceReview, Customer, ReviewLog
from app.models.enums import ComplianceReviewStatus, CustomerGrade, CustomerStatus, CustomerType
from app.schemas.customer_assignment import CustomerAssignRequest, CustomerStatusTransitionRequest
from app.services.customer_status import CustomerAssignmentStatusService


client = TestClient(app)


class FakeSession:
    def __init__(self, *, scalar_results=None):
        self.scalar_results = list(scalar_results or [])
        self.added = []
        self.flushed = False
        self.committed = False

    def scalar(self, statement):
        return self.scalar_results.pop(0) if self.scalar_results else None

    def add(self, item):
        self.added.append(item)

    def flush(self):
        self.flushed = True

    def commit(self):
        self.committed = True


def build_customer(**overrides) -> Customer:
    payload = {
        "id": uuid4(),
        "external_id": "customer:assignment",
        "name": "Ru Auto City",
        "normalized_name": "ru auto city",
        "country": "Russia",
        "city": "Moscow",
        "customer_type": CustomerType.LOCAL_DEALER_SECONDARY_DEALER,
        "grade": CustomerGrade.B,
        "status": CustomerStatus.PENDING_REVIEW,
        "owner": None,
        "owner_team": None,
        "do_not_contact": False,
    }
    payload.update(overrides)
    return Customer(**payload)


def test_customer_assignment_and_status_routes_are_registered_without_outreach_send() -> None:
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]

    assert "/customers/{customer_id}/assign" in paths
    assert "patch" in paths["/customers/{customer_id}/assign"]
    assert "/customers/{customer_id}/status" in paths
    assert "patch" in paths["/customers/{customer_id}/status"]
    api_text = (Path(__file__).resolve().parents[1] / "app" / "api" / "customers.py").read_text(encoding="utf-8")
    assert "auto_send" not in api_text
    assert "send_message" not in api_text


def test_assignment_request_requires_owner_team_actor_and_reason() -> None:
    request = CustomerAssignRequest(
        owner="cs-a",
        team="customer_service",
        actor="ops-a",
        reason="分配给客服首次触达。",
    )

    assert request.owner == "cs-a"
    assert request.team == "customer_service"
    assert request.actor == "ops-a"
    assert request.reason == "分配给客服首次触达。"


def test_assign_customer_by_id_records_owner_team_and_audit() -> None:
    customer = build_customer(status=CustomerStatus.PENDING_REVIEW)
    session = FakeSession(scalar_results=[customer])
    service = CustomerAssignmentStatusService(session)

    updated = service.assign_owner_by_id(
        customer.id,
        owner="cs-a",
        team="customer_service",
        actor="ops-a",
        reason="分配给客服首次触达。",
    )

    assert updated.owner == "cs-a"
    assert updated.owner_team == "customer_service"
    assert updated.status == CustomerStatus.READY_FOR_CUSTOMER_SERVICE
    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "customer_assigned"
    assert audit.reviewer == "ops-a"
    assert session.flushed is True


def test_transition_customer_status_by_id_allows_customer_service_flow() -> None:
    customer = build_customer(
        status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
        owner="cs-a",
        owner_team="customer_service",
    )
    session = FakeSession(scalar_results=[customer])
    service = CustomerAssignmentStatusService(session)

    updated = service.transition_status_by_id(
        customer.id,
        to_status=CustomerStatus.CUSTOMER_SERVICE_FOLLOWING,
        actor="cs-a",
        reason="人工已完成首次触达。",
    )

    assert updated.status == CustomerStatus.CUSTOMER_SERVICE_FOLLOWING
    audit = next(item for item in session.added if isinstance(item, ReviewLog))
    assert audit.action == "customer_status_changed"
    assert "to=customer_service_following" in audit.input_ref


def test_c_grade_quote_contract_boundary_creates_pending_compliance_and_blocks_status() -> None:
    customer = build_customer(
        grade=CustomerGrade.C,
        status=CustomerStatus.READY_FOR_SALES,
        owner="sales-a",
        owner_team="sales",
    )
    session = FakeSession(scalar_results=[customer, None])
    service = CustomerAssignmentStatusService(session)

    try:
        service.transition_status_by_id(
            customer.id,
            to_status=CustomerStatus.QUOTED,
            actor="sales-a",
            actor_role="sales",
            reason="报价前状态流转。",
        )
    except PermissionError as exc:
        assert "客服/销售不能绕过 C 级合规复核" in str(exc)
    else:
        raise AssertionError("C 级客户合规复核通过前不得进入报价状态")

    review = next(item for item in session.added if isinstance(item, ComplianceReview))
    assert review.customer_id == customer.id
    assert review.status == ComplianceReviewStatus.PENDING
    assert customer.status == CustomerStatus.READY_FOR_SALES


def test_do_not_contact_customer_cannot_be_assigned_or_transitioned_to_outreach_queue() -> None:
    customer = build_customer(do_not_contact=True, status=CustomerStatus.DO_NOT_CONTACT)
    service = CustomerAssignmentStatusService(FakeSession(scalar_results=[customer]))

    try:
        service.assign_owner_by_id(
            customer.id,
            owner="cs-a",
            team="customer_service",
            actor="ops-a",
            reason="尝试分配勿扰客户。",
        )
    except ValueError as exc:
        assert "不得进入客户工作台或分配队列" in str(exc)
    else:
        raise AssertionError("勿扰客户不得被分配")

    service = CustomerAssignmentStatusService(FakeSession(scalar_results=[customer]))
    try:
        service.transition_status_by_id(
            customer.id,
            to_status=CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
            actor="ops-a",
            reason="尝试恢复触达队列。",
        )
    except ValueError as exc:
        assert "不得进入客户工作台或分配队列" in str(exc)
    else:
        raise AssertionError("勿扰客户不得进入触达队列")


def test_status_transition_request_supports_quoted_boundary_status() -> None:
    request = CustomerStatusTransitionRequest(
        to_status=CustomerStatus.QUOTED,
        actor="sales-a",
        actor_role="sales",
        reason="客户请求报价，先触发合规门禁。",
    )

    assert request.to_status == CustomerStatus.QUOTED
    assert request.actor == "sales-a"
    assert request.actor_role == "sales"
