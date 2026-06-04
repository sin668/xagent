from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, InventoryItem, LeadInventoryMatch
from app.models.enums import CustomerGrade
from app.services.inventory import InventoryService


QUOTE_DISCLAIMER = "推荐车源仅用于人工报价前评估，不等同于正式报价。"


class InventoryMatchService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.inventory_service = InventoryService(session)

    def get_customer(self, customer_id: UUID) -> Customer:
        customer = self.session.scalar(select(Customer).where(Customer.id == customer_id))
        if customer is None:
            raise ValueError(f"客户不存在: {customer_id}")
        return customer

    def recommend(
        self,
        *,
        customer_id: UUID,
        vehicle_type: str | None,
        min_year: int | None,
        max_price: float | None,
        requires_compliance_review: bool,
    ) -> list[LeadInventoryMatch]:
        customer = self.get_customer(customer_id)
        matches = []
        for item in self.inventory_service.list_items():
            if vehicle_type and (item.vehicle_type or "").lower() != vehicle_type.lower():
                continue
            if min_year and (item.year is None or item.year < min_year):
                continue
            if max_price and (item.quoted_price is None or float(item.quoted_price) > max_price):
                continue
            if not self.inventory_service.can_ai_quote(item):
                continue

            reason = self._build_reason(item, min_year)
            risk_tips = self._build_risk_tips(customer, requires_compliance_review)
            match = LeadInventoryMatch(
                customer_id=customer.id,
                inventory_item_id=item.id,
                score=90,
                recommendation_reason=reason,
                risk_tips=risk_tips,
            )
            self.session.add(match)
            self.session.flush()
            match.inventory_item = item
            matches.append(match)
        return matches

    def decide(self, *, match_id: UUID, decision: str, owner: str, note: str | None) -> LeadInventoryMatch:
        match = self.session.scalar(select(LeadInventoryMatch).where(LeadInventoryMatch.id == match_id))
        if match is None:
            raise ValueError(f"匹配记录不存在: {match_id}")
        match.decision = decision
        match.decision_owner = owner
        match.decision_note = note
        match.decided_at = datetime.now(UTC)
        return match

    def next_gate(self, match: LeadInventoryMatch) -> str:
        if match.decision == "advance_quote":
            return "C级线索报价前必须完成合规复核"
        return "暂不匹配，记录原因后继续观察"

    def _build_reason(self, item: InventoryItem, min_year: int | None) -> str:
        valid_until = item.valid_until.isoformat()[:10] if item.valid_until else "Unknown"
        parts = [
            f"车型匹配 {item.vehicle_type or 'Unknown'}",
            f"年份满足 {min_year}+" if min_year else f"年份 {item.year or 'Unknown'}",
            f"车况: {(item.condition_summary or 'Unknown').split('，')[0]}",
            f"价格有效期至 {valid_until}",
            "可出口" if item.export_ready else "不可出口",
        ]
        return "；".join(parts)

    def _build_risk_tips(self, customer: Customer, requires_compliance_review: bool) -> list[str]:
        tips = [QUOTE_DISCLAIMER]
        if customer.grade == CustomerGrade.C or requires_compliance_review:
            tips.append("C级线索报价前必须合规复核")
        return tips
