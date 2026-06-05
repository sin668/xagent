from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JsonType
from app.models.enums import CustomerVehicleIntentSourceType, CustomerVehicleIntentStatus, enum_values


class CustomerVehicleIntent(Base):
    __tablename__ = "customer_vehicle_intents"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    year_range: Mapped[str | None] = mapped_column(String(80), nullable=True)
    vehicle_age: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_range: Mapped[str | None] = mapped_column(String(120), nullable=True)
    purchase_frequency: Mapped[str | None] = mapped_column(String(120), nullable=True)
    delivery_country: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    delivery_city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    concerns: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    source_type: Mapped[CustomerVehicleIntentSourceType] = mapped_column(
        Enum(CustomerVehicleIntentSourceType, values_callable=enum_values),
        nullable=False,
        index=True,
    )
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CustomerVehicleIntentStatus] = mapped_column(
        Enum(CustomerVehicleIntentStatus, values_callable=enum_values),
        nullable=False,
        default=CustomerVehicleIntentStatus.ACTIVE,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    customer = relationship("Customer", back_populates="vehicle_intents")
