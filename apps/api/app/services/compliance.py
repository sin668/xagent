from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ComplianceReview, Customer
from app.models.enums import ComplianceReviewStatus, CustomerGrade, CustomerStatus
from app.services.permissions import Phase3PermissionService


AI_RISK_TIP = "AI仅提示风险，不能替代合规复核结论或法律意见。"


class ComplianceService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_customer(self, customer_id: UUID) -> Customer:
        customer = self.session.scalar(select(Customer).where(Customer.id == customer_id))
        if customer is None:
            raise ValueError(f"客户不存在: {customer_id}")
        return customer

    def latest_review(self, customer_id: UUID) -> ComplianceReview | None:
        return self.session.scalar(
            select(ComplianceReview)
            .where(ComplianceReview.customer_id == customer_id)
            .order_by(ComplianceReview.created_at.desc(), ComplianceReview.id.desc())
        )

    def ensure_pending_review(self, customer: Customer) -> ComplianceReview:
        review = self.latest_review(customer.id)
        if review is not None:
            return review
        review = ComplianceReview(
            customer_id=customer.id,
            status=ComplianceReviewStatus.PENDING,
            reason="C级线索报价/合同前自动进入合规复核",
            risk_note="待复核贸易、支付、物流、清关风险",
        )
        self.session.add(review)
        self.session.flush()
        return review

    def list_pending_reviews(self) -> list[tuple[Customer, ComplianceReview]]:
        customers = self.session.scalars(
            select(Customer)
            .where(Customer.grade == CustomerGrade.C)
            .where(Customer.do_not_contact.is_(False))
            .order_by(Customer.updated_at.desc(), Customer.name)
        ).all()
        pending = []
        for customer in customers:
            review = self.ensure_pending_review(customer)
            if review.status == ComplianceReviewStatus.PENDING:
                pending.append((customer, review))
        return pending

    def status_for_customer(self, customer_id: UUID) -> tuple[Customer, ComplianceReview]:
        customer = self.get_customer(customer_id)
        review = self.ensure_pending_review(customer) if customer.grade == CustomerGrade.C else self.latest_review(customer.id)
        if review is None:
            review = ComplianceReview(
                customer_id=customer.id,
                status=ComplianceReviewStatus.NOT_REQUIRED,
                reason="非C级线索默认不需要报价前合规复核",
            )
            self.session.add(review)
            self.session.flush()
        return customer, review

    def submit_review(
        self,
        *,
        customer_id: UUID,
        actor: str,
        actor_role: str,
        status: str,
        reason: str,
        risk_note: str | None,
    ) -> ComplianceReview:
        if actor_role != "compliance":
            raise PermissionError("复核记录不可被普通用户覆盖。")
        customer = self.get_customer(customer_id)
        review = self.ensure_pending_review(customer)
        review.status = ComplianceReviewStatus(status)
        review.reason = reason
        review.risk_note = risk_note
        review.reviewer = actor
        review.reviewed_at = datetime.utcnow()
        return review

    def mark_quoted(self, *, customer_id: UUID, actor: str, actor_role: str = "sales") -> Customer:
        customer, review = self.status_for_customer(customer_id)
        if customer.grade == CustomerGrade.C and review.status != ComplianceReviewStatus.APPROVED:
            Phase3PermissionService.ensure_c_grade_compliance_ready(
                actor_role=actor_role,
                compliance_approved=False,
            )
            raise ValueError("C级线索报价前必须完成合规复核。")
        customer.status = CustomerStatus.QUOTED
        customer.owner = actor
        return customer

    def quote_contract_blocked(self, customer: Customer, review: ComplianceReview) -> bool:
        return customer.grade == CustomerGrade.C and review.status != ComplianceReviewStatus.APPROVED
