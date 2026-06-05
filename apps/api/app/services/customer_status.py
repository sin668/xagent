from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ComplianceReview, Customer, ReviewLog
from app.models.enums import ComplianceReviewStatus, CustomerGrade, CustomerStatus
from app.services.compliance_guards import Phase3ComplianceGuardService
from app.services.permissions import Phase3PermissionService


class CustomerAssignmentStatusService:
    WORKBENCH_BLOCKED_GRADES = {CustomerGrade.WATCH, CustomerGrade.INVALID}
    WORKBENCH_BLOCKED_STATUSES = {CustomerStatus.WATCH, CustomerStatus.INVALID, CustomerStatus.DO_NOT_CONTACT}
    VALID_TEAMS = {"customer_service", "sales", "export", "compliance", "operations"}
    QUOTE_CONTRACT_STATUSES = {CustomerStatus.QUOTED}
    ALLOWED_TRANSITIONS = {
        CustomerStatus.NEW: {CustomerStatus.NEEDS_ENRICHMENT, CustomerStatus.PENDING_REVIEW, CustomerStatus.INVALID, CustomerStatus.WATCH},
        CustomerStatus.NEEDS_ENRICHMENT: {CustomerStatus.PENDING_REVIEW, CustomerStatus.INVALID, CustomerStatus.WATCH},
        CustomerStatus.PENDING_REVIEW: {
            CustomerStatus.READY_FOR_CUSTOMER_SERVICE,
            CustomerStatus.READY_FOR_SALES,
            CustomerStatus.INVALID,
            CustomerStatus.WATCH,
            CustomerStatus.DO_NOT_CONTACT,
        },
        CustomerStatus.READY_FOR_CUSTOMER_SERVICE: {
            CustomerStatus.CUSTOMER_SERVICE_FOLLOWING,
            CustomerStatus.READY_FOR_SALES,
            CustomerStatus.INVALID,
            CustomerStatus.WATCH,
            CustomerStatus.DO_NOT_CONTACT,
        },
        CustomerStatus.CUSTOMER_SERVICE_FOLLOWING: {
            CustomerStatus.READY_FOR_SALES,
            CustomerStatus.SALES_FOLLOWING,
            CustomerStatus.INVALID,
            CustomerStatus.WATCH,
            CustomerStatus.DO_NOT_CONTACT,
        },
        CustomerStatus.READY_FOR_SALES: {
            CustomerStatus.SALES_FOLLOWING,
            CustomerStatus.QUOTED,
            CustomerStatus.INVALID,
            CustomerStatus.WATCH,
            CustomerStatus.DO_NOT_CONTACT,
        },
        CustomerStatus.SALES_FOLLOWING: {
            CustomerStatus.QUOTED,
            CustomerStatus.INVALID,
            CustomerStatus.WATCH,
            CustomerStatus.DO_NOT_CONTACT,
        },
        CustomerStatus.QUOTED: {
            CustomerStatus.SALES_FOLLOWING,
            CustomerStatus.INVALID,
            CustomerStatus.WATCH,
            CustomerStatus.DO_NOT_CONTACT,
        },
        CustomerStatus.INVALID: set(),
        CustomerStatus.WATCH: set(),
        CustomerStatus.DO_NOT_CONTACT: set(),
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    @classmethod
    def is_workbench_eligible(cls, customer: Customer) -> bool:
        return (
            not bool(customer.do_not_contact)
            and CustomerGrade(customer.grade) not in cls.WORKBENCH_BLOCKED_GRADES
            and CustomerStatus(customer.status) not in cls.WORKBENCH_BLOCKED_STATUSES
        )

    @classmethod
    def filter_workbench_customers(cls, customers: Iterable[Customer]) -> list[Customer]:
        return [customer for customer in customers if cls.is_workbench_eligible(customer)]

    @classmethod
    def workbench_query(cls, *, limit: int = 100):
        return (
            select(Customer)
            .where(Customer.do_not_contact.is_(False))
            .where(Customer.grade.notin_([CustomerGrade.WATCH, CustomerGrade.INVALID]))
            .where(Customer.status.notin_([CustomerStatus.WATCH, CustomerStatus.INVALID, CustomerStatus.DO_NOT_CONTACT]))
            .order_by(Customer.updated_at.desc(), Customer.name)
            .limit(limit)
        )

    @staticmethod
    def next_status_after_assignment(customer: Customer, team: str) -> CustomerStatus:
        if CustomerStatus(customer.status) not in {CustomerStatus.NEW, CustomerStatus.NEEDS_ENRICHMENT, CustomerStatus.PENDING_REVIEW}:
            return CustomerStatus(customer.status)
        if CustomerGrade(customer.grade) == CustomerGrade.C or team == "sales":
            return CustomerStatus.READY_FOR_SALES
        return CustomerStatus.READY_FOR_CUSTOMER_SERVICE

    @staticmethod
    def _coerce_status(value: CustomerStatus | str) -> CustomerStatus:
        return value if isinstance(value, CustomerStatus) else CustomerStatus(value)

    def get_customer(self, customer_id: UUID) -> Customer:
        customer = self.session.scalar(select(Customer).where(Customer.id == customer_id))
        if customer is None:
            raise ValueError(f"客户不存在: {customer_id}")
        return customer

    def latest_compliance_review(self, customer: Customer) -> ComplianceReview | None:
        return self.session.scalar(
            select(ComplianceReview)
            .where(ComplianceReview.customer_id == customer.id)
            .order_by(ComplianceReview.created_at.desc(), ComplianceReview.id.desc())
        )

    def ensure_pending_compliance_review(self, customer: Customer) -> ComplianceReview:
        review = self.latest_compliance_review(customer)
        if review is not None:
            return review
        review = ComplianceReview(
            customer_id=customer.id,
            status=ComplianceReviewStatus.PENDING,
            reason="C级客户报价/合同前必须完成合规复核。",
            risk_note="待复核报价、合同、付款、物流、清关、交付周期风险。",
        )
        self.session.add(review)
        self.session.flush()
        return review

    def audit(self, *, customer: Customer, action: str, actor: str, input_ref: str, result: str, reason: str | None) -> ReviewLog:
        log = ReviewLog(
            task_id=str(customer.id),
            agent_name="manual-customer-status",
            action=action,
            reviewer=actor,
            input_ref=input_ref,
            output_ref=f"customer:{customer.id}",
            result=result,
            error_message=reason,
        )
        self.session.add(log)
        return log

    def assign_owner(self, customer: Customer, *, owner: str, team: str, actor: str, reason: str | None) -> Customer:
        owner = owner.strip()
        team = team.strip()
        actor = actor.strip()
        if not owner:
            raise ValueError("客户分配必须指定负责人。")
        if team not in self.VALID_TEAMS:
            raise ValueError("客户分配团队不在允许范围内。")
        if not actor:
            raise ValueError("客户分配必须记录操作人。")
        if not self.is_workbench_eligible(customer):
            raise ValueError("Watch/Invalid/勿扰客户不得进入客户工作台或分配队列。")

        old_owner = customer.owner
        old_team = getattr(customer, "owner_team", None)
        old_status = CustomerStatus(customer.status)
        customer.owner = owner
        customer.owner_team = team
        customer.status = self.next_status_after_assignment(customer, team)
        self.audit(
            customer=customer,
            action="customer_assigned",
            actor=actor,
            input_ref=(
                f"old_owner={old_owner};old_team={old_team};owner={owner};team={team};"
                f"from_status={old_status.value};to_status={customer.status.value}"
            ),
            result="approved",
            reason=reason,
        )
        self.session.flush()
        return customer

    def assign_owner_by_id(
        self,
        customer_id: UUID,
        *,
        owner: str,
        team: str,
        actor: str,
        reason: str | None,
    ) -> Customer:
        customer = self.get_customer(customer_id)
        return self.assign_owner(customer, owner=owner, team=team, actor=actor, reason=reason)

    def transition_status(
        self,
        customer: Customer,
        *,
        to_status: CustomerStatus | str,
        actor: str,
        actor_role: str = "operations",
        reason: str | None,
        latest_compliance_review: ComplianceReview | None = None,
    ) -> Customer:
        target = self._coerce_status(to_status)
        current = CustomerStatus(customer.status)
        if current in self.WORKBENCH_BLOCKED_STATUSES or customer.do_not_contact:
            raise ValueError("Watch/Invalid/勿扰客户不得进入客户工作台或分配队列。")
        if target not in self.ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(f"不允许的客户状态流转: {current.value} -> {target.value}")
        if target in self.QUOTE_CONTRACT_STATUSES and CustomerGrade(customer.grade) == CustomerGrade.C:
            review = latest_compliance_review or self.ensure_pending_compliance_review(customer)
            if ComplianceReviewStatus(review.status) != ComplianceReviewStatus.APPROVED:
                self.audit(
                    customer=customer,
                    action="customer_compliance_review_requested",
                    actor=actor,
                    input_ref=f"from={current.value};to={target.value};review_status={review.status.value}",
                    result="blocked",
                    reason=reason,
                )
                Phase3ComplianceGuardService.audit_block(
                    session=self.session,
                    actor=actor,
                    target_ref=f"customer:{customer.id}",
                    block_type="c_grade_compliance_review_required",
                    reason="C 级客户报价/合同/付款/物流/清关/交付周期动作前必须完成合规复核。",
                    input_ref=f"trade_action={target.value};compliance_approved=False",
                )
                Phase3PermissionService.ensure_c_grade_compliance_ready(
                    actor_role=actor_role,
                    compliance_approved=False,
                )
                self.session.flush()
                raise ValueError("C级客户报价/合同前必须完成合规复核。")

        customer.status = target
        self.audit(
            customer=customer,
            action="customer_status_changed",
            actor=actor,
            input_ref=f"from={current.value};to={target.value}",
            result="approved",
            reason=reason,
        )
        self.session.flush()
        return customer

    def transition_status_by_id(
        self,
        customer_id: UUID,
        *,
        to_status: CustomerStatus | str,
        actor: str,
        actor_role: str = "operations",
        reason: str | None,
    ) -> Customer:
        customer = self.get_customer(customer_id)
        return self.transition_status(customer, to_status=to_status, actor=actor, actor_role=actor_role, reason=reason)
