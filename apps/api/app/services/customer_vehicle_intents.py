from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, CustomerVehicleIntent
from app.models.enums import CustomerGrade, CustomerStatus, CustomerVehicleIntentStatus
from app.schemas.customer_vehicle_intent import CustomerVehicleIntentCreate, CustomerVehicleIntentUpdate


class CustomerVehicleIntentService:
    SALES_CANDIDATE_STATUSES = {CustomerVehicleIntentStatus.ACTIVE, CustomerVehicleIntentStatus.PENDING_CONFIRMATION}

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

    def get_intent(self, intent_id: UUID) -> CustomerVehicleIntent:
        intent = self.session.scalar(select(CustomerVehicleIntent).where(CustomerVehicleIntent.id == intent_id))
        if intent is None:
            raise ValueError(f"客户意向车型不存在: {intent_id}")
        return intent

    def list_for_customer(self, customer_id: UUID) -> list[CustomerVehicleIntent]:
        self.get_customer(customer_id)
        return list(
            self.session.scalars(
                select(CustomerVehicleIntent)
                .where(CustomerVehicleIntent.customer_id == customer_id)
                .order_by(CustomerVehicleIntent.created_at.desc(), CustomerVehicleIntent.id.desc())
            ).all()
        )

    @staticmethod
    def ensure_customer_can_edit_intents(customer: Customer) -> None:
        if bool(customer.do_not_contact) or CustomerStatus(customer.status) == CustomerStatus.DO_NOT_CONTACT:
            raise ValueError("勿扰客户不得新增或修改意向车型。")
        if CustomerStatus(customer.status) in {CustomerStatus.WATCH, CustomerStatus.INVALID}:
            raise ValueError("Watch/Invalid 客户不得维护意向车型。")

    @classmethod
    def is_sales_candidate_customer(cls, customer: Customer, intents: list[CustomerVehicleIntent]) -> bool:
        if CustomerGrade(customer.grade) != CustomerGrade.C:
            return False
        if CustomerStatus(customer.status) not in {CustomerStatus.READY_FOR_SALES, CustomerStatus.SALES_FOLLOWING}:
            return False
        return any(CustomerVehicleIntentStatus(intent.status) in cls.SALES_CANDIDATE_STATUSES for intent in intents)

    def create_for_customer(
        self,
        customer_id: UUID,
        *,
        request: CustomerVehicleIntentCreate,
        now: datetime | None = None,
    ) -> CustomerVehicleIntent:
        if request.customer_id != customer_id:
            raise ValueError("路径 customer_id 与请求 customer_id 不一致。")
        customer = self.get_customer(customer_id)
        self.ensure_customer_can_edit_intents(customer)
        timestamp = now or self._now()
        intent = CustomerVehicleIntent(
            customer_id=customer_id,
            brand=request.brand,
            model=request.model,
            year_range=request.year_range,
            vehicle_age=request.vehicle_age,
            quantity=request.quantity,
            budget_range=request.budget_range,
            purchase_frequency=request.purchase_frequency,
            delivery_country=request.delivery_country,
            delivery_city=request.delivery_city,
            concerns=request.concerns,
            source_type=request.source_type,
            source_note=request.source_note,
            status=request.status,
            created_by=request.created_by,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.session.add(intent)
        self.session.flush()
        return intent

    def update_intent(
        self,
        intent_id: UUID,
        *,
        request: CustomerVehicleIntentUpdate,
        now: datetime | None = None,
    ) -> CustomerVehicleIntent:
        intent = self.get_intent(intent_id)
        customer = self.get_customer(intent.customer_id)
        self.ensure_customer_can_edit_intents(customer)
        updates = request.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            setattr(intent, field_name, value)
        intent.updated_at = now or self._now()
        self.session.flush()
        return intent
