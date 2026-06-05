from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, CustomerFollowup
from app.models.enums import CustomerStatus
from app.schemas.customer_followup import CustomerFollowupCreate


class CustomerFollowupService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def get_customer(self, customer_id: UUID) -> Customer:
        customer = self.session.scalar(select(Customer).where(Customer.id == customer_id))
        if customer is None:
            raise ValueError(f"客户不存在: {customer_id}")
        return customer

    def list_for_customer(self, customer_id: UUID) -> list[CustomerFollowup]:
        self.get_customer(customer_id)
        return list(
            self.session.scalars(
                select(CustomerFollowup)
                .where(CustomerFollowup.customer_id == customer_id)
                .order_by(CustomerFollowup.created_at.desc(), CustomerFollowup.id.desc())
            ).all()
        )

    def create_for_customer(
        self,
        customer_id: UUID,
        *,
        request: CustomerFollowupCreate,
        now: datetime | None = None,
    ) -> CustomerFollowup:
        if request.customer_id != customer_id:
            raise ValueError("路径 customer_id 与请求 customer_id 不一致。")
        customer = self.get_customer(customer_id)
        if bool(customer.do_not_contact) or CustomerStatus(customer.status) == CustomerStatus.DO_NOT_CONTACT:
            raise ValueError("勿扰客户不得继续新增主动跟进。")
        timestamp = now or self._now()
        followup = CustomerFollowup(
            customer_id=customer_id,
            owner_id=request.owner_id,
            team=request.team,
            followup_type=request.followup_type,
            content=request.content,
            customer_feedback=request.customer_feedback,
            next_action=request.next_action,
            next_followup_at=request.next_followup_at,
            triggered_dnc=request.triggered_dnc,
            triggered_compliance_review=request.triggered_compliance_review,
            created_by=request.created_by,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.session.add(followup)
        if request.triggered_dnc:
            customer.do_not_contact = True
            customer.do_not_contact_reason = request.customer_feedback
            customer.do_not_contact_marked_by = request.created_by
            customer.do_not_contact_marked_at = timestamp
            customer.status = CustomerStatus.DO_NOT_CONTACT
        self.session.flush()
        return followup
