from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InventoryItem


CONFIRMED_QUOTE_STATUS = "confirmed"


class InventoryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_item(
        self,
        *,
        external_id: str | None,
        brand: str,
        model: str,
        year: int | None,
        mileage_km: int | None,
        vehicle_type: str | None,
        condition_summary: str | None,
        configuration: str | None,
        quoted_price,
        currency: str,
        quote_status: str,
        export_ready: bool,
        media_urls: list[str],
        valid_until: datetime | None,
        source_ref: str | None,
    ) -> InventoryItem:
        item = InventoryItem(
            external_id=external_id,
            brand=brand,
            model=model,
            year=year,
            mileage_km=mileage_km,
            vehicle_type=vehicle_type,
            condition_summary=condition_summary,
            configuration=configuration,
            quoted_price=quoted_price,
            currency=currency,
            quote_status=quote_status,
            export_ready=export_ready,
            media_urls=media_urls,
            valid_until=valid_until,
            source_ref=source_ref,
        )
        self.session.add(item)
        return item

    def list_items(self) -> list[InventoryItem]:
        return list(self.session.scalars(select(InventoryItem).order_by(InventoryItem.created_at.asc(), InventoryItem.id.asc())).all())

    def get_item_by_external_id(self, external_id: str) -> InventoryItem:
        item = self.session.scalar(select(InventoryItem).where(InventoryItem.external_id == external_id))
        if item is None:
            raise ValueError(f"车源不存在: {external_id}")
        return item

    def is_expired(self, item: InventoryItem, now: datetime | None = None) -> bool:
        if item.valid_until is None:
            return False
        current = now or datetime.now(UTC)
        valid_until = item.valid_until
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=UTC)
        return valid_until < current

    def quote_blocking_reasons(self, item: InventoryItem, now: datetime | None = None) -> list[str]:
        reasons = []
        if item.quote_status != CONFIRMED_QUOTE_STATUS:
            reasons.append("价格未确认")
        if self.is_expired(item, now):
            reasons.append("车源已过期")
        if not item.export_ready:
            reasons.append("不可出口")
        if item.quoted_price is None:
            reasons.append("缺少价格")
        return reasons

    def can_ai_quote(self, item: InventoryItem, now: datetime | None = None) -> bool:
        return not self.quote_blocking_reasons(item, now)

    def risk_flags(self, item: InventoryItem, now: datetime | None = None) -> list[str]:
        flags = []
        if self.is_expired(item, now):
            flags.append("过期")
        if item.quote_status != CONFIRMED_QUOTE_STATUS:
            flags.append("价格未确认")
        if not item.export_ready:
            flags.append("不可出口")
        return flags
